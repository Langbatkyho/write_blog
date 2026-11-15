"""Build bundle.json cho Claude Artifact từ nguồn chân lý trong repo (ART-1, O-04).

Bundle gom flow, skill của mọi style hệ thống, bảng model Claude, hằng số và
JSON Schema của Voice Lab. Mọi kiểm tra dùng lại resolver/validator Python của
engine; bundle sai contract thì build dừng (fail-closed).

Skill được kèm sẵn chuỗi YAML do `yaml.safe_dump(..., allow_unicode=True,
sort_keys=False)` sinh ra — đúng cách `engine.workflow_context.build_step_prompt`
và `engine.learning.build_learning_prompt` dựng prompt — để JS ghép prompt khớp
từng byte mà không cần port PyYAML.

Không gọi API, không ghi vào runs/.

    python artifact/build_bundle.py [--config engine/config.example.yaml] [--out artifact/dist/bundle.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

from artifact.claude_config import EFFORTS, VERIFIED_MODELS, validate_claude_config  # noqa: E402
from engine.learning import _compact_skills, _compact_workflow  # noqa: E402
from engine.style_contracts import validate_style_metadata  # noqa: E402
from engine.style_manager import validate_style_contract  # noqa: E402
from engine.utils import load_yaml, resolve_path  # noqa: E402
from engine.voice_lab.calibration import (  # noqa: E402
    CALIBRATION_MAX_WORDS,
    CALIBRATION_MIN_WORDS,
    DEFAULT_CONTENT_BRIEF,
    DIRECT_USER_CONFIRMATION_CONFIDENCE,
)
from engine.voice_lab.compiler import (  # noqa: E402
    AGENT_FILENAME_MAP,
    DIMENSION_AGENTS,
    REQUIRED_AGENTS,
    SKILL_LEVEL_INVARIANTS,
    stable_skill_hash,
)
from engine.voice_lab.models import SCHEMA_VERSION, VOICE_DIMENSIONS, StyleProfile  # noqa: E402
from engine.voice_lab.prompts import (  # noqa: E402
    analysis_schema,
    calibration_schema,
    interview_patch_schema,
    synthesis_schema,
)
from engine.workflow_contracts import (  # noqa: E402
    WorkflowDefinition,
    validate_step_skill_contract,
    validate_workflow_artifact_set,
)
from engine.workflow_resolution import (  # noqa: E402
    load_workflow_skills,
    resolve_step_skill_path,
    resolve_workflow_file,
)

BUNDLE_FORMAT = 1
MODES = ("deep", "moment")
DEFAULT_CONFIG = ROOT / "engine" / "config.example.yaml"
DEFAULT_OUT = ROOT / "artifact" / "dist" / "bundle.json"

SCHEMA_EXPORTS: Dict[str, Callable[[], Any]] = {
    "analysis_payload": analysis_schema,
    "synthesis_payload": synthesis_schema,
    "interview_patch_payload": interview_patch_schema,
    "calibration_payload": calibration_schema,
    "style_profile": StyleProfile.model_json_schema,
}


class BundleBuildError(ValueError):
    pass


def dump_yaml(data: Any) -> str:
    """Đúng tham số mà engine dùng khi nhúng YAML vào prompt."""
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False)


def _load_workflow(config: Dict[str, Any], mode: str) -> Tuple[Path, Dict[str, Any], WorkflowDefinition]:
    workflow_file = resolve_workflow_file(config, mode)
    workflow = load_yaml(workflow_file)
    try:
        definition = WorkflowDefinition.from_dict(workflow, expected_mode=mode)
    except ValueError as exc:
        raise BundleBuildError(f"Flow '{workflow_file.name}' (mode {mode}) không hợp lệ: {exc}") from exc
    return workflow_file, workflow, definition


def _discover_styles(mode: str) -> List[str]:
    mode_dir = resolve_path(f"skills/{mode}")
    if not mode_dir.is_dir():
        raise BundleBuildError(f"Không có thư mục skills/{mode}.")
    return sorted(
        entry.name
        for entry in mode_dir.iterdir()
        if entry.is_dir() and entry.name != "__pycache__" and not entry.name.startswith(".")
    )


def _style_metadata(mode: str, slug: str) -> Dict[str, Any]:
    meta_path = resolve_path(f"skills/{mode}/{slug}/style_meta.yaml")
    if not meta_path.exists():
        return validate_style_metadata({"name": slug, "slug": slug, "mode": mode})
    return validate_style_metadata(load_yaml(meta_path), expected_slug=slug, expected_mode=mode)


def _build_style(
    mode: str,
    slug: str,
    workflow_file: Path,
    workflow: Dict[str, Any],
    definition: WorkflowDefinition,
) -> Dict[str, Any]:
    try:
        resolved = validate_style_contract(mode, slug, workflow_file)
        if resolved != slug:
            raise ValueError(f"thư mục '{slug}' được resolve thành '{resolved}'")
        meta = _style_metadata(mode, slug)
        files: Dict[str, Dict[str, Any]] = {}
        skills_by_stage: Dict[str, Dict[str, Any]] = {}
        for step, step_definition in zip(workflow["steps"], definition.steps):
            skill_path = resolve_step_skill_path(step, slug, mode)
            skill = load_yaml(skill_path)
            validate_step_skill_contract(step_definition, skill)
            skills_by_stage[step_definition.id] = skill
            files[skill_path.name] = {
                "data": skill,
                "yaml": dump_yaml(skill),
                # Hash do Python tính: JSON làm mất dạng số thực (3.0 -> 3) nên JS không tự tính lại được.
                "base_hash": stable_skill_hash(skill),
            }
        validate_workflow_artifact_set(definition, skills_by_stage)
        learning_skills = load_workflow_skills(workflow, slug, mode)
    except BundleBuildError:
        raise
    except Exception as exc:
        raise BundleBuildError(f"Style '{slug}' (mode {mode}) không hợp lệ: {exc}") from exc
    return {
        "system": True,
        "meta": meta,
        "files": files,
        "learning_compact_skills_yaml": dump_yaml(_compact_skills(learning_skills)),
    }


def _check_base_styles(styles: Dict[str, Dict[str, Any]]) -> None:
    for mode, by_slug in styles.items():
        for slug, style in by_slug.items():
            base = style["meta"].get("base_style_slug")
            if base is not None and base not in by_slug:
                raise BundleBuildError(
                    f"Style '{slug}' (mode {mode}) khai báo base_style_slug '{base}' không tồn tại."
                )


def _check_filename_map(workflows: Dict[str, Dict[str, Any]]) -> None:
    """AGENT_FILENAME_MAP của Voice Lab phải khớp đúng các file skill của flow (Bài học 14)."""
    for mode, workflow in workflows.items():
        mapped = {AGENT_FILENAME_MAP[mode][agent] for agent in REQUIRED_AGENTS[mode]}
        flow_files = set(workflow["stage_files"].values())
        if mapped != flow_files:
            raise BundleBuildError(
                f"AGENT_FILENAME_MAP (mode {mode}) lệch với flow: "
                f"chỉ có trong map {sorted(mapped - flow_files)}, chỉ có trong flow {sorted(flow_files - mapped)}."
            )


def _export_schemas() -> Dict[str, Any]:
    schemas: Dict[str, Any] = {}
    for name, export in SCHEMA_EXPORTS.items():
        try:
            schema = export()
        except Exception as exc:
            raise BundleBuildError(f"Không xuất được JSON Schema '{name}': {exc}") from exc
        if not isinstance(schema, dict) or schema.get("type") != "object" or "properties" not in schema:
            raise BundleBuildError(f"JSON Schema '{name}' không phải schema object hợp lệ.")
        schemas[name] = schema
    return schemas


def build_bundle_content(config_path: Path = DEFAULT_CONFIG) -> Dict[str, Any]:
    config = load_yaml(config_path)
    workflows: Dict[str, Dict[str, Any]] = {}
    styles: Dict[str, Dict[str, Any]] = {}
    learning_workflow_yaml: Dict[str, str] = {}
    for mode in MODES:
        workflow_file, workflow, definition = _load_workflow(config, mode)
        workflows[mode] = {
            "file": workflow_file.relative_to(resolve_path(".")).as_posix(),
            "definition": workflow,
            "stage_ids": list(definition.stage_ids),
            "stage_files": {step.id: Path(step.skill).name for step in definition.steps},
        }
        learning_workflow_yaml[mode] = dump_yaml(_compact_workflow(workflow))
        styles[mode] = {
            slug: _build_style(mode, slug, workflow_file, workflow, definition)
            for slug in _discover_styles(mode)
        }
        if not styles[mode]:
            raise BundleBuildError(f"Mode {mode} không có style nào.")
    _check_base_styles(styles)
    _check_filename_map(workflows)

    all_stage_ids = [stage for mode in MODES for stage in workflows[mode]["stage_ids"]]
    if len(all_stage_ids) != len(set(all_stage_ids)):
        raise BundleBuildError("Stage id trùng giữa hai flow; bảng model theo stage sẽ mơ hồ.")
    models = validate_claude_config(config.get("claude"), workflow_stage_ids=all_stage_ids)

    learning_skill = load_yaml(resolve_path("skills/editorial_learning.yaml"))
    return {
        "bundle_format": BUNDLE_FORMAT,
        "workflows": workflows,
        "styles": styles,
        "models": models,
        # Lựa chọn hợp lệ cho bảng chỉnh model trên trang (ART-6.1): đúng những gì build chấp nhận.
        "model_catalog": {"models": dict(VERIFIED_MODELS), "efforts": list(EFFORTS)},
        "learning": {
            "skill_yaml": dump_yaml(learning_skill),
            "compact_workflow_yaml": learning_workflow_yaml,
        },
        "voice_lab": {
            "schema_version": SCHEMA_VERSION,
            "dimensions": list(VOICE_DIMENSIONS),
            "dimension_agents": DIMENSION_AGENTS,
            "agent_filename_map": AGENT_FILENAME_MAP,
            "required_agents": REQUIRED_AGENTS,
            "skill_level_invariants": list(SKILL_LEVEL_INVARIANTS),
            "calibration": {
                "min_words": CALIBRATION_MIN_WORDS,
                "max_words": CALIBRATION_MAX_WORDS,
                "direct_user_confirmation_confidence": DIRECT_USER_CONFIRMATION_CONFIDENCE,
                "default_content_brief": DEFAULT_CONTENT_BRIEF,
            },
            "schemas": _export_schemas(),
        },
    }


def serialize(content: Dict[str, Any]) -> Tuple[str, str]:
    """Trả (content_hash, chuỗi JSON của bundle). Thứ tự key giữ nguyên thứ tự nguồn."""
    canonical = json.dumps(content, ensure_ascii=False, separators=(",", ":"))
    content_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    bundle = {"content_hash": content_hash, **content}
    return content_hash, json.dumps(bundle, ensure_ascii=False, separators=(",", ":")) + "\n"


def build_bundle(config_path: Path = DEFAULT_CONFIG, out_path: Path = DEFAULT_OUT) -> Tuple[str, Path]:
    content_hash, text = serialize(build_bundle_content(config_path))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8", newline="\n")
    return content_hash, out_path


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    try:
        content_hash, out_path = build_bundle(args.config, args.out)
    except BundleBuildError as exc:
        print(f"Build thất bại: {exc}", file=sys.stderr)
        return 1
    size = out_path.stat().st_size
    print(json.dumps({"content_hash": content_hash, "out": str(out_path), "bytes": size}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
