from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import yaml

from engine.voice_lab.models import (
    SCHEMA_VERSION,
    EvidenceClaim,
    StyleProfile,
    VOICE_DIMENSIONS,
)


_LEGACY_PROFILE_FIELDS = {
    "profile_version",
    "name",
    "interview_answers",
    "calibration_selected",
}
_LEGACY_EVIDENCE_FIELDS = {"quote", "confidence", "evidence_ids"}


def _normalize_legacy_evidence(raw: Any) -> list[dict[str, Any]]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError("Legacy evidence phải là danh sách.")
    normalized: list[dict[str, Any]] = []
    allowed = set(EvidenceClaim.model_fields) | _LEGACY_EVIDENCE_FIELDS
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("Legacy evidence item phải là object.")
        unknown = set(item) - allowed
        if unknown:
            raise ValueError(
                f"Legacy evidence có field không hỗ trợ: {sorted(unknown)}"
            )
        claim = dict(item)
        if "exact_quote" not in claim and "quote" in claim:
            claim["exact_quote"] = claim.pop("quote")
        evidence_ids = claim.pop("evidence_ids", [])
        if not claim.get("sample_id") and evidence_ids:
            claim["sample_id"] = str(evidence_ids[0])
        claim.pop("confidence", None)
        normalized.append(claim)
    return normalized


def _normalize_legacy_dna(raw: Any) -> Any:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError("Legacy dna phải là object.")
    unknown = set(raw) - set(VOICE_DIMENSIONS)
    if unknown:
        raise ValueError(f"Legacy dna có dimension lạ: {sorted(unknown)}")
    normalized: dict[str, Any] = {}
    for dimension, value in raw.items():
        if isinstance(value, str):
            normalized[dimension] = {
                "description": value,
                "confidence": 0.0,
                "source": "legacy",
            }
        else:
            normalized[dimension] = value
    return normalized


def migrate_profile_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Pure, idempotent v1 adapter; current v2 contract stays fail-closed."""
    if not isinstance(data, dict):
        raise ValueError("Profile phải là object.")
    raw = dict(data)
    try:
        version = int(float(raw.get("schema_version", 1)))
    except (TypeError, ValueError) as exc:
        raise ValueError("schema_version không hợp lệ.") from exc
    if version > SCHEMA_VERSION:
        raise ValueError(
            f"Profile schema v{version} mới hơn phiên bản hỗ trợ v{SCHEMA_VERSION}."
        )
    if version == SCHEMA_VERSION:
        return StyleProfile.model_validate(raw).model_dump(mode="json")
    if version != 1:
        raise ValueError(f"Profile schema v{version} không được hỗ trợ.")

    allowed = set(StyleProfile.model_fields) | _LEGACY_PROFILE_FIELDS
    unknown = set(raw) - allowed
    if unknown:
        raise ValueError(f"Legacy profile có field không hỗ trợ: {sorted(unknown)}")
    migrated = {
        key: value
        for key, value in raw.items()
        if key in StyleProfile.model_fields
    }
    migrated["schema_version"] = SCHEMA_VERSION
    migrated["revision"] = int(
        raw.get("profile_version", raw.get("revision", 1))
    )
    migrated["dna"] = _normalize_legacy_dna(raw.get("dna"))
    migrated["evidence"] = _normalize_legacy_evidence(raw.get("evidence"))
    migrated["rejected_evidence"] = _normalize_legacy_evidence(
        raw.get("rejected_evidence")
    )
    warnings = list(raw.get("analysis_warnings", []))
    warnings.append("Profile v1 đã được chuyển sang schema v2.")
    dropped = sorted(set(raw) & _LEGACY_PROFILE_FIELDS - {"profile_version"})
    if dropped:
        warnings.append(
            "Dữ liệu legacy không ánh xạ trực tiếp và không được đưa vào "
            f"runtime contract v2: {', '.join(dropped)}."
        )
    migrated["analysis_warnings"] = warnings
    migrated["analysis_status"] = (
        "partial" if migrated["evidence"] else "incomplete_legacy_data"
    )
    migrated["is_draft"] = True
    migrated["status"] = "draft"
    profile = StyleProfile.model_validate(migrated)
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
