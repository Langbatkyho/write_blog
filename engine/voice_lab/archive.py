from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Optional

from engine.voice_lab.migration import migrate_profile_data
from engine.voice_lab.models import SCHEMA_VERSION, StyleProfile


def _checksum(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_member(name: str) -> bool:
    path = PurePosixPath(name.replace("\\", "/"))
    return bool(name) and not path.is_absolute() and ".." not in path.parts


def export_style(
    slug: str,
    mode: str,
    output_path: str,
    profile_data: str,
    yaml_content: Optional[str] = None,
    *,
    effective_skills: Optional[Dict[str, str]] = None,
) -> str:
    """Export a schema-v2 package with checksums for every payload file."""
    raw_profile = json.loads(profile_data)
    raw_profile.setdefault("slug", slug)
    raw_profile.setdefault("mode", mode)
    profile = StyleProfile.model_validate(raw_profile)
    canonical_profile = profile.model_dump_json(indent=2).encode("utf-8")

    payloads: Dict[str, bytes] = {"profile.json": canonical_profile}
    if effective_skills:
        for filename, content in sorted(effective_skills.items()):
            if not _safe_member(filename) or not filename.endswith(".yaml"):
                raise ValueError(f"Tên skill không an toàn: {filename}")
            payloads[f"skills/{filename}"] = content.encode("utf-8")
    elif yaml_content:
        payloads[f"skills/{slug}.yaml"] = yaml_content.encode("utf-8")

    manifest = {
        "slug": slug,
        "mode": mode,
        "schema_version": SCHEMA_VERSION,
        "checksums": {name: _checksum(data) for name, data in payloads.items()},
    }
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in payloads.items():
            archive.writestr(name, data)
        archive.writestr(
            "manifest.json",
            json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"),
        )
    return output_path


def import_style(zip_path: str, extract_to: Optional[str] = None) -> Dict[str, Any]:
    """
    Validate the whole package before optional extraction.

    Version 1 profiles are migrated in memory. Future schema versions fail
    closed. Import never publishes a style.
    """
    extracted: Dict[str, bytes] = {}
    with zipfile.ZipFile(zip_path, "r") as archive:
        names = archive.namelist()
        if "manifest.json" not in names:
            raise ValueError("Invalid archive: manifest.json is missing.")
        if any(not _safe_member(name) for name in names):
            raise ValueError("Invalid archive: path traversal detected.")

        try:
            manifest = json.loads(archive.read("manifest.json"))
        except json.JSONDecodeError as exc:
            raise ValueError("Invalid archive: manifest.json is not valid JSON.") from exc

        version = int(float(manifest.get("schema_version", 1)))
        if version > SCHEMA_VERSION:
            raise ValueError(
                f"Archive schema v{version} mới hơn phiên bản hỗ trợ v{SCHEMA_VERSION}."
            )
        checksums = manifest.get("checksums")
        if not isinstance(checksums, dict) or "profile.json" not in checksums:
            raise ValueError("Invalid archive: checksums/profile.json is missing.")

        for filename, expected_hash in checksums.items():
            if filename not in names:
                raise ValueError(f"Missing file declared in manifest: {filename}")
            data = archive.read(filename)
            if _checksum(data) != expected_hash:
                raise ValueError(f"Checksum mismatch for {filename}.")
            extracted[filename] = data

    try:
        profile_data = json.loads(extracted["profile.json"])
        migrated = migrate_profile_data(profile_data)
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        raise ValueError("Invalid archive: profile.json is invalid.") from exc
    extracted["profile.json"] = json.dumps(
        migrated, ensure_ascii=False, indent=2
    ).encode("utf-8")
    manifest["schema_version"] = SCHEMA_VERSION
    manifest["profile"] = migrated

    if extract_to is not None:
        target_root = Path(extract_to).resolve()
        target_root.mkdir(parents=True, exist_ok=True)
        for name, data in extracted.items():
            target = (target_root / PurePosixPath(name)).resolve()
            if target_root not in target.parents and target != target_root:
                raise ValueError(f"Security error: unsafe extraction path {name}.")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)

    return manifest
