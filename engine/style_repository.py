from __future__ import annotations

import datetime as dt
import os
import shutil
import uuid
from pathlib import Path


def create_staging_dir(parent: Path, label: str) -> Path:
    parent.mkdir(parents=True, exist_ok=True)
    staging = parent / f".{label}.staging-{uuid.uuid4().hex}"
    staging.mkdir(parents=False, exist_ok=False)
    return staging


def clone_to_staging(source: Path, parent: Path, label: str) -> Path:
    parent.mkdir(parents=True, exist_ok=True)
    staging = parent / f".{label}.staging-{uuid.uuid4().hex}"
    shutil.copytree(source, staging)
    return staging


def commit_staged_directory(staging: Path, target: Path) -> None:
    tombstone = target.parent / f".{target.name}.old-{uuid.uuid4().hex}"
    moved = False
    try:
        if target.exists():
            os.replace(target, tombstone)
            moved = True
        os.replace(staging, target)
    except Exception:
        if target.exists() and moved:
            shutil.rmtree(target, ignore_errors=True)
        if moved and tombstone.exists():
            os.replace(tombstone, target)
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        raise
    if tombstone.exists():
        shutil.rmtree(tombstone)


def commit_staged_rename(
    staging: Path, source: Path, target: Path
) -> None:
    tombstone = source.parent / f".{source.name}.old-{uuid.uuid4().hex}"
    source_moved = False
    try:
        os.replace(source, tombstone)
        source_moved = True
        os.replace(staging, target)
    except Exception:
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)
        if source_moved and tombstone.exists():
            os.replace(tombstone, source)
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        raise
    shutil.rmtree(tombstone)


def move_to_trash(source: Path, trash_root: Path) -> Path:
    trash_root.mkdir(parents=True, exist_ok=True)
    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    target = trash_root / f"{source.name}_{timestamp}_{uuid.uuid4().hex[:8]}"
    os.replace(source, target)
    return target
