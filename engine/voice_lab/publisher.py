from __future__ import annotations

import copy
import datetime as dt
import os
import shutil
import uuid
from pathlib import Path
from typing import Optional

import yaml

from engine.style_manager import validate_slug, validate_style_yaml
from engine.utils import resolve_path, write_text
from engine.voice_lab.compiler import (
    REQUIRED_AGENTS,
    AGENT_FILENAME_MAP,
    SKILL_LEVEL_INVARIANTS,
    stable_skill_hash,
    validate_base_snapshot,
)
from engine.voice_lab.models import CompileResult, PublishResult, StyleProfile


def _root_path(workspace_root: Optional[Path]) -> Path:
    return workspace_root.resolve() if workspace_root else resolve_path(".").resolve()


def _validate_publish_input(
    profile: StyleProfile,
    compiled: CompileResult,
    slug: str,
    mode: str,
) -> None:
    if not validate_slug(slug):
        raise ValueError("Slug không hợp lệ.")
    if mode not in REQUIRED_AGENTS:
        raise ValueError(f"Mode không hợp lệ: {mode}")
    if profile.mode != mode:
        raise ValueError(
            f"Profile mode '{profile.mode}' không khớp publish mode '{mode}'."
        )
    if profile.analysis_status != "complete":
        raise ValueError("Profile chưa phân tích hoàn tất.")
    if profile.status != "confirmed" or profile.is_draft:
        raise ValueError("Profile chưa được người dùng xác nhận.")
    required_files = {
        AGENT_FILENAME_MAP[mode][agent] for agent in REQUIRED_AGENTS[mode]
    }
    actual_files = set(compiled.artifacts)
    missing = sorted(required_files - actual_files)
    if missing:
        raise ValueError(f"Compile result thiếu skill bắt buộc: {missing}")
    unexpected = sorted(actual_files - required_files)
    if unexpected:
        raise ValueError(f"Compile result có skill ngoài Flow contract: {unexpected}")
    for artifact in compiled.artifacts.values():
        validate_base_snapshot(
            artifact,
            mode=mode,
            base_style_slug=profile.base_style_slug,
        )


def _write_and_validate_staging(
    staging_dir: Path,
    profile: StyleProfile,
    compiled: CompileResult,
    *,
    name: str,
    slug: str,
    mode: str,
    workspace_root: Path,
) -> list[str]:
    warnings: list[str] = []
    staging_dir.mkdir(parents=True, exist_ok=False)
    for filename, artifact in compiled.artifacts.items():
        if artifact.filename != filename:
            raise ValueError(
                f"{filename}: Canonical IR filename không khớp key artifact."
            )
        effective = artifact.effective_skill
        content = yaml.safe_dump(effective, allow_unicode=True, sort_keys=False)
        valid, error, warning = validate_style_yaml(content, filename, mode)
        if not valid:
            raise ValueError(f"{filename}: {error}")
        if warning:
            warnings.append(f"{filename}: {warning}")
        write_text(staging_dir / filename, content)

        for key in SKILL_LEVEL_INVARIANTS:
            if key not in artifact.invariants:
                continue
            if key not in effective:
                raise ValueError(f"{filename}: thiếu invariant bắt buộc '{key}'.")
            expected = artifact.invariants[key]
            if effective[key] != expected:
                raise ValueError(
                    f"{filename}: invariant '{key}' thay đổi trong effective skill."
                )
        synthetic = {
            "filename": artifact.filename,
            "workflow_order": artifact.workflow_order,
            "agent_id": artifact.agent_id,
        }
        for key, actual in synthetic.items():
            if key not in artifact.invariants:
                raise ValueError(f"{filename}: snapshot thiếu invariant '{key}'.")
            if artifact.invariants[key] != actual:
                raise ValueError(
                    f"{filename}: invariant '{key}' không khớp Canonical IR."
                )
        base_candidate = copy.deepcopy(effective)
        base_candidate.pop("voice_lab_style", None)
        if stable_skill_hash(base_candidate) != artifact.base_hash:
            raise ValueError(f"{filename}: base_hash không khớp effective skill.")

    now = dt.datetime.now(dt.timezone.utc).isoformat()
    meta = {
        "name": name,
        "slug": slug,
        "mode": mode,
        "base_style_slug": profile.base_style_slug,
        "schema_version": profile.schema_version,
        "profile_revision": profile.revision,
        "is_protected": False,
        "updated_at": now,
    }
    write_text(
        staging_dir / "style_meta.yaml",
        yaml.safe_dump(meta, allow_unicode=True, sort_keys=False),
    )
    write_text(
        staging_dir / "profile_dna.json",
        profile.model_dump_json(indent=2),
    )

    flow_name = "write_moment_blog.yaml" if mode == "moment" else "write_blog.yaml"
    workflow_path = workspace_root / "flow" / flow_name
    if not workflow_path.exists():
        raise ValueError(f"Không tìm thấy workflow: {workflow_path}")
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8-sig"))
    flow_files = {Path(step["skill"]).name for step in workflow.get("steps", [])}
    expected_files = {
        AGENT_FILENAME_MAP[mode][agent] for agent in REQUIRED_AGENTS[mode]
    }
    if flow_files != expected_files:
        raise ValueError(
            "Flow filename contract không khớp AGENT_FILENAME_MAP: "
            f"flow={sorted(flow_files)}, map={sorted(expected_files)}"
        )
    staging_files = {path.name for path in staging_dir.glob("*.yaml")}
    generated_skill_files = staging_files - {"style_meta.yaml"}
    if generated_skill_files != flow_files:
        raise ValueError(
            "Staging skill set không khớp Flow: "
            f"staging={sorted(generated_skill_files)}, flow={sorted(flow_files)}"
        )
    return warnings


def publish_style(
    profile: StyleProfile,
    compiled: CompileResult,
    *,
    name: str,
    slug: str,
    mode: Optional[str] = None,
    workspace_root: Optional[Path] = None,
) -> PublishResult:
    """Publish a complete style using staging, validation, backup and rollback."""
    effective_mode = mode or profile.mode
    _validate_publish_input(profile, compiled, slug, effective_mode)
    root = _root_path(workspace_root)
    mode_dir = root / "skills" / effective_mode
    mode_dir.mkdir(parents=True, exist_ok=True)
    transaction_id = uuid.uuid4().hex
    staging_dir = mode_dir / f"{slug}.staging-{transaction_id}"
    runtime_dir = mode_dir / slug
    tombstone = mode_dir / f"{slug}.old-{transaction_id}"
    backup_path: Optional[Path] = None
    runtime_moved = False
    if runtime_dir.exists():
        meta_path = runtime_dir / "style_meta.yaml"
        if meta_path.exists():
            meta = yaml.safe_load(meta_path.read_text(encoding="utf-8-sig")) or {}
            if meta.get("is_protected", False):
                raise ValueError(f"Không thể ghi đè System Style được bảo vệ: {slug}")

    try:
        warnings = _write_and_validate_staging(
            staging_dir,
            profile,
            compiled,
            name=name,
            slug=slug,
            mode=effective_mode,
            workspace_root=root,
        )
        if runtime_dir.exists():
            backup_dir = root / "profile_history"
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup_base = backup_dir / (
                f"{slug}_{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S')}"
                f"_{transaction_id[:8]}"
            )
            backup_path = Path(
                shutil.make_archive(str(backup_base), "zip", str(runtime_dir))
            )
            os.replace(runtime_dir, tombstone)
            runtime_moved = True
        os.replace(staging_dir, runtime_dir)
    except Exception:
        if runtime_dir.exists() and runtime_moved:
            shutil.rmtree(runtime_dir, ignore_errors=True)
        if runtime_moved and tombstone.exists():
            os.replace(tombstone, runtime_dir)
        if staging_dir.exists():
            shutil.rmtree(staging_dir, ignore_errors=True)
        raise

    if tombstone.exists():
        try:
            shutil.rmtree(tombstone)
        except OSError as exc:
            warnings.append(f"Không thể xóa tombstone sau publish: {exc}")
    return PublishResult(
        runtime_dir=str(runtime_dir),
        backup_path=str(backup_path) if backup_path else None,
        warnings=warnings,
    )
