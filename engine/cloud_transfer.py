"""Portable run archives for separate Cloud tasks."""

from __future__ import annotations

import hashlib
import io
import json
import os
import tempfile
import zipfile
from pathlib import Path

from engine.workflow_contracts import validate_relative_output_path
from engine.cloud_stages import verify_run


def export_run(run_dir: Path, archive: Path, config_path: Path = Path("engine/config.example.yaml")) -> Path:
    if not (run_dir / "metadata.json").is_file() or not (run_dir / "step_outputs.json").is_file():
        raise ValueError("Run lacks checkpoint files")
    if archive.exists():
        raise FileExistsError(archive)
    if verify_run(run_dir, config_path)["status"] != "ok":
        raise ValueError("Run needs recovery before export")
    files = {}
    for path in run_dir.rglob("*"):
        if path.is_symlink():
            raise ValueError("Run contains symlink")
        if path.is_file():
            relative = path.relative_to(run_dir).as_posix()
            validate_relative_output_path(relative, field_name="archive path")
            files[relative] = path.read_bytes()
    manifest = {
        "format": 1,
        "run_id": run_dir.name,
        "sha256": {name: hashlib.sha256(data).hexdigest() for name, data in files.items()},
    }
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w", zipfile.ZIP_DEFLATED) as bundle:
        for name, data in files.items():
            bundle.writestr(name, data)
        bundle.writestr("_manifest.json", json.dumps(manifest, ensure_ascii=False))
    archive.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix=".export-", suffix=".zip", dir=archive.parent, delete=False) as temporary:
        temporary.write(payload.getvalue())
        staged_archive = Path(temporary.name)
    try:
        os.link(staged_archive, archive)
    finally:
        staged_archive.unlink(missing_ok=True)
    return archive


def import_run(archive: Path, output_root: Path, config_path: Path = Path("engine/config.example.yaml")) -> Path:
    with zipfile.ZipFile(archive) as bundle:
        names = bundle.namelist()
        if len(names) != len(set(names)) or "_manifest.json" not in names:
            raise ValueError("Invalid archive entries")
        manifest = json.loads(bundle.read("_manifest.json"))
        if manifest.get("format") != 1:
            raise ValueError("Unsupported archive format")
        run_id = validate_relative_output_path(manifest["run_id"], field_name="run id")
        if "/" in run_id:
            raise ValueError("Run ID must be one directory name")
        expected = manifest["sha256"]
        if set(names) != set(expected) | {"_manifest.json"}:
            raise ValueError("Manifest does not match archive entries")
        files = {}
        total_size = 0
        for name, digest in expected.items():
            validate_relative_output_path(name, field_name="archive path")
            entry = bundle.getinfo(name)
            if entry.is_dir() or entry.file_size > 32 * 1024 * 1024:
                raise ValueError("Invalid or oversized archive entry")
            total_size += entry.file_size
            if total_size > 128 * 1024 * 1024:
                raise ValueError("Archive exceeds size limit")
            data = bundle.read(name)
            if hashlib.sha256(data).hexdigest() != digest:
                raise ValueError("Archive checksum mismatch")
            files[name] = data
    if not {"metadata.json", "step_outputs.json", "input.md"}.issubset(files):
        raise ValueError("Run checkpoint is incomplete")
    output_root.mkdir(parents=True, exist_ok=True)
    target = output_root / run_id
    if target.exists():
        raise FileExistsError(target)
    with tempfile.TemporaryDirectory(prefix=".import-", dir=output_root) as temporary:
        staged = Path(temporary) / run_id
        staged.mkdir()
        for name, data in files.items():
            destination = staged / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
        if verify_run(staged, config_path)["status"] != "ok":
            raise ValueError("Imported run needs recovery")
        # Rename only after every file has been written. A collision must never
        # replace an existing run, including one created during staging.
        if target.exists():
            raise FileExistsError(target)
        os.rename(staged, target)
    return target
