import datetime as dt
import shutil
from pathlib import Path
from typing import Any, Tuple, List, Dict, Optional
import yaml

from engine.utils import resolve_path, write_text, load_yaml, read_text
from engine.supabase_client import upsert_style_file, delete_style_files
from engine.workflow_contracts import (
    WorkflowDefinition,
    validate_step_skill_contract,
    validate_workflow_artifact_set,
)
from engine.style_repository import (
    clone_to_staging,
    commit_staged_directory,
    commit_staged_rename,
    move_to_trash,
)
from engine.style_contracts import is_valid_style_slug, validate_style_metadata

def _sync_style_to_supabase(mode: str, slug: str, style_dir: Path) -> None:
    """Helper to sync all yaml files in a style directory to Supabase."""
    for f in style_dir.glob("*.yaml"):
        content = read_text(f)
        upsert_style_file(mode, slug, f.name, content)

DEEP_GROUP_A_FILES = {
    "story_architect.yaml",
    "reflection_engine.yaml",
    "coach_agent.yaml",
    "future_self.yaml",
}

DEEP_GROUP_B_FILES = {
    "writing_agent.yaml",
    "reader_experience.yaml",
    "editor_agent.yaml",
}

def validate_slug(slug: str) -> bool:
    return is_valid_style_slug(slug)

def validate_style_yaml(content: str, filename: str, mode: str) -> Tuple[bool, str, str]:
    try:
        data = yaml.safe_load(content)
        if not isinstance(data, dict):
            return False, "Nội dung YAML không phải là một mapping (dictionary) hợp lệ.", ""
    except Exception as e:
        return False, f"Lỗi cú pháp YAML: {str(e)}", ""

    # Universal Hard Check
    if "name" not in data:
        return False, "Thiếu khóa gốc bắt buộc: 'name'.", ""
    if "output" not in data:
        return False, "Thiếu khóa gốc bắt buộc: 'output'.", ""

    # Specific Hard Check by Group
    if mode == "moment" or filename in DEEP_GROUP_A_FILES:
        if "tasks" not in data:
            return False, f"Agent '{filename}' (Nhóm A / Moment) bắt buộc phải có khóa gốc 'tasks'.", ""
    elif filename in DEEP_GROUP_B_FILES:
        if "supreme_rule" not in data:
            return False, f"Agent '{filename}' (Nhóm B) bắt buộc phải có khóa 'supreme_rule'.", ""

    # Soft Warning Check
    warning_msg = ""
    anti_hallucination_keys = {"do_not", "rules", "style_rules", "supreme_rule"}
    if not any(k in data for k in anti_hallucination_keys):
        warning_msg = "Cảnh báo: File thiếu các từ khóa bảo vệ văn phong chống hallucination (rules, do_not, style_rules)."

    return True, "", warning_msg

def resolve_style_by_slug_or_alias(mode: str, slug: str) -> Optional[str]:
    # 1. Direct path check
    style_dir = resolve_path(f"skills/{mode}/{slug}")
    if style_dir.is_dir():
        return slug

    # 2. Check alias in style_meta.yaml (previous_slugs)
    mode_dir = resolve_path(f"skills/{mode}")
    if mode_dir.is_dir():
        for d in mode_dir.iterdir():
            if d.is_dir():
                meta_path = d / "style_meta.yaml"
                if meta_path.exists():
                    try:
                        meta = load_yaml(meta_path)
                        if slug in meta.get("previous_slugs", []):
                            return d.name
                    except Exception:
                        pass

    # 3. Legacy Deep fallback during transition
    if mode == "deep":
        legacy_dir = resolve_path(f"skills/{slug}")
        if legacy_dir.is_dir():
            return slug

    return None


def _validate_alias_namespace(
    mode_dir: Path,
    *,
    candidate_slug: str,
    candidate_aliases: list[str],
    exclude_slug: str | None = None,
) -> None:
    claims: dict[str, str] = {}

    def claim(value: str, owner: str) -> None:
        previous = claims.get(value)
        if previous is not None:
            raise ValueError(
                f"Slug/alias '{value}' bị trùng giữa '{previous}' và '{owner}'."
            )
        claims[value] = owner

    if mode_dir.is_dir():
        for directory in mode_dir.iterdir():
            if (
                not directory.is_dir()
                or directory.name.startswith(".")
                or directory.name == exclude_slug
            ):
                continue
            claim(directory.name, f"slug:{directory.name}")
            meta_path = directory / "style_meta.yaml"
            if not meta_path.exists():
                continue
            metadata = validate_style_metadata(
                load_yaml(meta_path),
                expected_slug=directory.name,
            )
            for alias in metadata.get("previous_slugs", []):
                claim(alias, f"alias:{directory.name}")

    candidate_values = [candidate_slug, *candidate_aliases]
    if len(candidate_values) != len(set(candidate_values)):
        raise ValueError("Slug hiện tại và previous_slugs không được trùng nhau.")
    for value in candidate_values:
        claim(value, f"candidate:{candidate_slug}")


def validate_style_directory(
    mode: str,
    slug: str,
    style_dir: Path,
    workflow_path: Optional[Path] = None,
    *,
    namespace_exclude_slug: str | None = None,
) -> None:
    meta_path = style_dir / "style_meta.yaml"
    metadata: dict[str, Any] = {
        "slug": slug,
        "mode": mode,
        "previous_slugs": [],
    }
    if meta_path.exists():
        metadata = validate_style_metadata(
            load_yaml(meta_path), expected_slug=slug, expected_mode=mode
        )
    _validate_alias_namespace(
        style_dir.parent,
        candidate_slug=slug,
        candidate_aliases=list(metadata.get("previous_slugs", [])),
        exclude_slug=namespace_exclude_slug or slug,
    )

    if workflow_path is None:
        flow_name = (
            "write_moment_blog.yaml" if mode == "moment" else "write_blog.yaml"
        )
        workflow_path = resolve_path(f"flow/{flow_name}")
    workflow = load_yaml(workflow_path)
    definition = WorkflowDefinition.from_dict(workflow, expected_mode=mode)
    skills: dict[str, dict[str, Any]] = {}
    missing_files: list[str] = []
    for step in definition.steps:
        filename = Path(step.skill).name
        skill_path = style_dir / filename
        if not skill_path.is_file():
            missing_files.append(filename)
            continue
        content = read_text(skill_path)
        valid, error, _ = validate_style_yaml(content, filename, mode)
        if not valid:
            raise ValueError(f"Skill '{filename}' không hợp lệ: {error}")
        skill = yaml.safe_load(content)
        validate_step_skill_contract(step, skill)
        skills[step.id] = skill
    if missing_files:
        raise ValueError(
            f"Style '{slug}' (mode: {mode}) vi phạm hợp đồng Flow. "
            f"Thiếu các file skill bắt buộc: {missing_files}"
        )
    validate_workflow_artifact_set(definition, skills)


def validate_style_contract(mode: str, style: str, workflow_path: Optional[Path] = None) -> str:
    resolved = resolve_style_by_slug_or_alias(mode, style)
    if not resolved:
        mode_dir = resolve_path(f"skills/{mode}")
        available = [d.name for d in mode_dir.iterdir() if d.is_dir()] if mode_dir.exists() else []
        raise ValueError(f"Style '{style}' not found in mode '{mode}'. Available styles: {available}")
    
    style = resolved
    style_dir = resolve_path(f"skills/{mode}/{style}")
    if not style_dir.is_dir() and mode == "deep":
        style_dir = resolve_path(f"skills/{style}")
    try:
        validate_style_directory(mode, style, style_dir, workflow_path)
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(
            f"Không thể validate Flow/style contract tại {workflow_path}: {exc}"
        ) from exc

    return style

def list_styles(mode: str) -> List[Dict[str, Any]]:
    mode_dir = resolve_path(f"skills/{mode}")
    if not mode_dir.is_dir():
        return []

    styles = []
    for d in mode_dir.iterdir():
        if not d.is_dir() or d.name == "__pycache__":
            continue
        meta_path = d / "style_meta.yaml"
        if meta_path.exists():
            try:
                meta = validate_style_metadata(
                    load_yaml(meta_path),
                    expected_slug=d.name,
                    expected_mode=mode,
                )
                meta.setdefault("slug", d.name)
                meta.setdefault("name", d.name)
                meta.setdefault("mode", mode)
                meta.setdefault("is_protected", False)
                meta.setdefault("updated_at", dt.datetime.fromtimestamp(d.stat().st_mtime).isoformat())
                styles.append(meta)
            except Exception as exc:
                styles.append(
                    {
                        "name": d.name,
                        "slug": d.name,
                        "mode": mode,
                        "description": "Style metadata không hợp lệ",
                        "is_protected": True,
                        "is_valid": False,
                        "validation_error": str(exc),
                        "updated_at": dt.datetime.fromtimestamp(
                            d.stat().st_mtime
                        ).isoformat(),
                    }
                )
        else:
            styles.append({
                "name": d.name,
                "slug": d.name,
                "mode": mode,
                "description": "Custom style",
                "is_protected": False,
                "updated_at": dt.datetime.fromtimestamp(d.stat().st_mtime).isoformat(),
            })

    styles.sort(key=lambda x: str(x.get("updated_at", "")), reverse=True)
    return styles

def get_style_detail(mode: str, slug: str) -> Dict[str, Any]:
    resolved = resolve_style_by_slug_or_alias(mode, slug)
    if not resolved:
        raise ValueError(f"Style '{slug}' not found in mode '{mode}'.")
    slug = resolved
    style_dir = resolve_path(f"skills/{mode}/{slug}")
    if not style_dir.is_dir() and mode == "deep":
        style_dir = resolve_path(f"skills/{slug}")

    meta_path = style_dir / "style_meta.yaml"
    meta = {}
    if meta_path.exists():
        meta = validate_style_metadata(
            load_yaml(meta_path), expected_slug=slug, expected_mode=mode
        )
    meta.setdefault("name", slug)
    meta.setdefault("slug", slug)
    meta.setdefault("mode", mode)
    meta.setdefault("is_protected", False)

    files = []
    for f in sorted(style_dir.iterdir()):
        if f.is_file() and f.name.endswith(".yaml") and f.name != "style_meta.yaml":
            files.append(f.name)

    return {
        "metadata": meta,
        "files": files,
        "directory": str(style_dir),
    }

def save_style_file(mode: str, slug: str, filename: str, content: str) -> Tuple[bool, str, str]:
    if Path(filename).name != filename or filename in {"", ".", ".."}:
        return False, "Tên file không hợp lệ hoặc chứa path traversal.", ""
    resolved = resolve_style_by_slug_or_alias(mode, slug)
    if not resolved:
        return False, f"Style '{slug}' không tồn tại.", ""
    slug = resolved

    if filename.endswith(".yaml") and filename != "style_meta.yaml":
        is_valid, err, warn = validate_style_yaml(content, filename, mode)
        if not is_valid:
            return False, err, warn
    else:
        warn = ""

    style_dir = resolve_path(f"skills/{mode}/{slug}")
    if not style_dir.is_dir() and mode == "deep":
        style_dir = resolve_path(f"skills/{slug}")

    staging_dir: Path | None = None
    try:
        staging_dir = clone_to_staging(style_dir, style_dir.parent, slug)
        write_text(staging_dir / filename, content)
        meta_path = staging_dir / "style_meta.yaml"
        if meta_path.exists():
            meta = load_yaml(meta_path)
            if filename == "style_meta.yaml":
                meta = validate_style_metadata(
                    meta, expected_slug=slug, expected_mode=mode
                )
            meta["updated_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
            write_text(
                meta_path,
                yaml.safe_dump(meta, allow_unicode=True, sort_keys=False),
            )
        validate_style_directory(mode, slug, staging_dir)
        commit_staged_directory(staging_dir, style_dir)
        
        # Sync file đã sửa lên Supabase
        if not upsert_style_file(mode, slug, filename, content):
            warn += " ⚠️ Lưu local OK nhưng sync Supabase thất bại."
            
        committed_meta = style_dir / "style_meta.yaml"
        if committed_meta.exists():
            if not upsert_style_file(mode, slug, "style_meta.yaml", read_text(committed_meta)):
                warn += " ⚠️ Sync style_meta.yaml lên Supabase thất bại."
            
        return True, "", warn.strip()
    except Exception as e:
        if staging_dir and staging_dir.exists():
            shutil.rmtree(staging_dir, ignore_errors=True)
        return False, f"Lỗi ghi file atomic: {str(e)}", ""

def create_style(
    mode: str,
    name: str,
    slug: str,
    description: str,
    clone_from: str = "reflective"
) -> Tuple[bool, str]:
    if not validate_slug(slug):
        return False, "Slug không hợp lệ. Chỉ chấp nhận chữ thường, số, dấu gạch ngang (2-50 ký tự)."

    target_dir = resolve_path(f"skills/{mode}/{slug}")
    if target_dir.exists():
        return False, f"Style slug '{slug}' đã tồn tại trong chế độ '{mode}'."

    source_dir = resolve_path(f"skills/{mode}/{clone_from}")
    if not source_dir.is_dir() and mode == "deep":
        source_dir = resolve_path(f"skills/{clone_from}")
    if not source_dir.is_dir():
        return False, f"Style gốc '{clone_from}' không tồn tại để nhân bản."

    staging_dir: Path | None = None
    try:
        staging_dir = clone_to_staging(source_dir, target_dir.parent, slug)
        meta_path = staging_dir / "style_meta.yaml"
        now_str = dt.datetime.now(dt.timezone.utc).isoformat()
        meta = {
            "name": name,
            "slug": slug,
            "mode": mode,
            "description": description,
            "created_at": now_str,
            "updated_at": now_str,
            "is_protected": False,
            "previous_slugs": [],
        }
        validate_style_metadata(
            meta, expected_slug=slug, expected_mode=mode
        )
        write_text(
            meta_path,
            yaml.safe_dump(meta, allow_unicode=True, sort_keys=False),
        )
        validate_style_directory(mode, slug, staging_dir)
        commit_staged_directory(staging_dir, target_dir)
        _sync_style_to_supabase(mode, slug, target_dir)
        return True, ""
    except Exception as e:
        if staging_dir and staging_dir.exists():
            shutil.rmtree(staging_dir, ignore_errors=True)
        return False, f"Lỗi khi nhân bản style (đã rollback): {str(e)}"

def rename_style(mode: str, old_slug: str, new_name: str, new_slug: str) -> Tuple[bool, str]:
    resolved = resolve_style_by_slug_or_alias(mode, old_slug)
    if not resolved:
        return False, f"Style '{old_slug}' không tồn tại."
    old_slug = resolved

    style_dir = resolve_path(f"skills/{mode}/{old_slug}")
    if not style_dir.is_dir() and mode == "deep":
        style_dir = resolve_path(f"skills/{old_slug}")

    meta_path = style_dir / "style_meta.yaml"
    meta = {}
    if meta_path.exists():
        try:
            meta = validate_style_metadata(
                load_yaml(meta_path),
                expected_slug=old_slug,
                expected_mode=mode,
            )
        except Exception as exc:
            return False, f"Metadata style không hợp lệ: {exc}"

    if meta.get("is_protected", False):
        if old_slug != new_slug:
            return False, "Không thể đổi kỹ thuật (slug) của System Style bảo vệ. Chỉ có thể đổi tên hiển thị."

    if not validate_slug(new_slug):
        return False, "Slug mới không hợp lệ. Chỉ chấp nhận chữ thường, số, dấu gạch ngang."

    target_dir = resolve_path(f"skills/{mode}/{new_slug}")
    if old_slug != new_slug and target_dir.exists():
        return False, f"Slug '{new_slug}' đã được sử dụng."

    staging_dir: Path | None = None
    try:
        staging_dir = clone_to_staging(style_dir, target_dir.parent, new_slug)
        if old_slug != new_slug:
            prev = meta.get("previous_slugs", [])
            if old_slug not in prev:
                prev.append(old_slug)
            meta["previous_slugs"] = prev
            meta["slug"] = new_slug

        meta["name"] = new_name
        meta["updated_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
        validate_style_metadata(
            meta, expected_slug=new_slug, expected_mode=mode
        )
        
        write_text(
            staging_dir / "style_meta.yaml",
            yaml.safe_dump(meta, allow_unicode=True, sort_keys=False),
        )
        validate_style_directory(
            mode,
            new_slug,
            staging_dir,
            namespace_exclude_slug=old_slug,
        )
        if old_slug == new_slug:
            commit_staged_directory(staging_dir, style_dir)
            _sync_style_to_supabase(mode, new_slug, style_dir)
        else:
            commit_staged_rename(staging_dir, style_dir, target_dir)
            # Sync style mới và xóa style cũ
            _sync_style_to_supabase(mode, new_slug, target_dir)
            delete_style_files(mode, old_slug)
        return True, ""
    except Exception as e:
        if staging_dir and staging_dir.exists():
            shutil.rmtree(staging_dir, ignore_errors=True)
        return False, f"Lỗi đổi tên style: {str(e)}"

def delete_style(mode: str, slug: str) -> Tuple[bool, str]:
    resolved = resolve_style_by_slug_or_alias(mode, slug)
    if not resolved:
        return False, f"Style '{slug}' không tồn tại."
    slug = resolved

    style_dir = resolve_path(f"skills/{mode}/{slug}")
    if not style_dir.is_dir() and mode == "deep":
        style_dir = resolve_path(f"skills/{slug}")

    meta_path = style_dir / "style_meta.yaml"
    if meta_path.exists():
        try:
            meta = validate_style_metadata(
                load_yaml(meta_path),
                expected_slug=slug,
                expected_mode=mode,
            )
            if meta.get("is_protected", False):
                return False, "Không thể xóa System Style bảo vệ (is_protected=True)."
        except Exception as exc:
            return False, f"Metadata style không hợp lệ; từ chối xóa: {exc}"

    try:
        trash_root = resolve_path(f"profile_history/style_trash/{mode}")
        trash_path = move_to_trash(style_dir, trash_root)
        delete_style_files(mode, slug)
        return True, f"Style đã chuyển vào thùng rác: {trash_path}"
    except Exception as e:
        return False, f"Lỗi khi xóa folder style: {str(e)}"
