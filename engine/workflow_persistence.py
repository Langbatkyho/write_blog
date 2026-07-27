from __future__ import annotations

import datetime as dt
import json
import os
import uuid
from pathlib import Path
from typing import Any

from engine.parser import extract_title, slugify
from engine.workflow_contracts import (
    RUN_INTERNAL_PATHS,
    StageResult,
    validate_relative_output_path,
    validate_run_artifact_path,
)


def build_run_dir(
    log_root: Path, input_markdown: str, style: str, mode: str = "deep"
) -> Path:
    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    suffix = uuid.uuid4().hex[:8]
    slug = slugify(extract_title(input_markdown))
    return log_root / f"{timestamp}_{suffix}_{mode}_{style}_{slug}"


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(content, encoding="utf-8", newline="\n")
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    atomic_write_text(
        path, json.dumps(data, ensure_ascii=False, indent=2, default=str)
    )


def resolve_relative_path(
    root_dir: Path,
    relative_path: str,
    *,
    field_name: str = "relative path",
) -> Path:
    validate_relative_output_path(relative_path, field_name=field_name)
    root = root_dir.resolve()
    target = (root / relative_path).resolve()
    if target != root and root not in target.parents:
        raise ValueError(f"Artifact path thoát khỏi run directory: {relative_path}")
    return target


def resolve_output_path(run_dir: Path, relative_path: str) -> Path:
    validate_run_artifact_path(relative_path, field_name="artifact path")
    return resolve_relative_path(
        run_dir,
        relative_path,
        field_name="artifact path",
    )


class RunRepository:
    def __init__(self, root: Path):
        self.root = root.resolve()

    def create(self, input_markdown: str, style: str, mode: str) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        for _ in range(5):
            run_dir = build_run_dir(self.root, input_markdown, style, mode)
            try:
                run_dir.mkdir(parents=False, exist_ok=False)
                return run_dir
            except FileExistsError:
                continue
        raise FileExistsError("Không thể tạo Run ID duy nhất sau 5 lần thử.")

    def write_metadata(self, run_dir: Path, metadata: dict[str, Any]) -> None:
        atomic_write_json(run_dir / "metadata.json", metadata)

    def checkpoint(
        self, run_dir: Path, stages: dict[str, StageResult]
    ) -> None:
        atomic_write_json(
            run_dir / "step_outputs.json",
            {stage_id: result.to_dict() for stage_id, result in stages.items()},
        )

    def write_artifact(
        self, run_dir: Path, relative_path: str, content: str
    ) -> None:
        atomic_write_text(resolve_output_path(run_dir, relative_path), content)

    def write_internal(
        self, run_dir: Path, filename: str, content: str
    ) -> None:
        normalized = Path(filename).as_posix().casefold()
        if normalized not in RUN_INTERNAL_PATHS:
            raise ValueError(f"Không phải file nội bộ của run: {filename!r}")
        atomic_write_text(run_dir / filename, content)
