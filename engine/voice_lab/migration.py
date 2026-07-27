from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import yaml

from engine.voice_lab.models import StyleProfile


def migrate_profile_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Pure, idempotent profile migration. Pydantic owns v1 field conversion."""
    profile = StyleProfile.model_validate(data)
    return profile.model_dump(mode="json")


def import_existing_style(mode: str, slug: str) -> StyleProfile:
    """
    Import an existing runtime style as a draft profile.

    A prior Voice Lab profile is migrated when present. Plain legacy YAML has
    no trustworthy evidence, so it is represented explicitly as incomplete.
    """
    base_dir = Path(__file__).resolve().parents[2]
    style_dir = base_dir / "skills" / mode / slug
    if not style_dir.is_dir() and mode == "deep":
        legacy_dir = base_dir / "skills" / slug
        if legacy_dir.is_dir():
            style_dir = legacy_dir
    if not style_dir.is_dir():
        raise FileNotFoundError(f"Không tìm thấy style '{slug}' trong mode '{mode}'.")

    profile_path = style_dir / "profile_dna.json"
    if profile_path.exists():
        try:
            raw = json.loads(profile_path.read_text(encoding="utf-8-sig"))
            raw.setdefault("slug", slug)
            raw.setdefault("mode", mode)
            return StyleProfile.model_validate(migrate_profile_data(raw))
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            warning = f"Không thể đọc profile cũ: {exc}"
    else:
        warning = "Legacy style không có profile_dna.json hoặc evidence có thể kiểm chứng."

    # Confirm at least one valid YAML exists, without inferring style from it.
    yaml_files = sorted(
        path for path in style_dir.glob("*.yaml") if path.name != "style_meta.yaml"
    )
    if not yaml_files:
        raise ValueError(f"Style '{slug}' không có file YAML agent.")
    try:
        yaml.safe_load(yaml_files[0].read_text(encoding="utf-8-sig"))
    except (OSError, yaml.YAMLError) as exc:
        warning = f"Không thể đọc YAML legacy: {exc}"

    return StyleProfile(
        slug=slug,
        mode=mode,
        provenance="inferred_from_yaml",
        confidence=0.0,
        dna=None,
        evidence=[],
        analysis_status="incomplete_legacy_data",
        analysis_warnings=[warning],
        is_draft=True,
    )
