"""ART-4-AC4: engine Python đọc được run do Claude Artifact xuất ra (bố cục runs/).

Bộ file do artifact/src/core/export.js dựng (qua artifact/tests/js/export_fixture.mjs,
client giả, không gọi API) được ghi vào tmp_path; không ghi vào runs/.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.utils import load_yaml  # noqa: E402
from engine.workflow import run_learning_loop  # noqa: E402
from engine.workflow_learning import load_step_outputs_from_run  # noqa: E402

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="Cần Node.js để dựng bộ file xuất.")
FLOWS = {"deep": "flow/write_blog.yaml", "moment": "flow/write_moment_blog.yaml"}


@pytest.fixture(scope="module")
def exported() -> dict:
    result = subprocess.run(
        ["node", str(ROOT / "artifact" / "tests" / "js" / "export_fixture.mjs")],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHON": sys.executable},
        timeout=300,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def _write_run(root: Path, export: dict) -> Path:
    run_dir = root / export["folderName"]
    for name, content in export["files"].items():
        path = run_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")
    return run_dir


@pytest.mark.parametrize("key", ["deep/reflective", "moment/va-natural"])
def test_engine_reads_exported_step_outputs(tmp_path, exported, key):
    mode = key.split("/")[0]
    run_dir = _write_run(tmp_path, exported[key])
    workflow = load_yaml(ROOT / FLOWS[mode])
    outputs = load_step_outputs_from_run(run_dir, workflow)
    assert list(outputs) == [step["id"] for step in workflow["steps"]]
    assert all(text.startswith("[FAKE]") or text.startswith("## Edited Blog") for text in outputs.values())
    metadata = json.loads((run_dir / "metadata.json").read_text(encoding="utf-8"))
    assert (metadata["mode"], metadata["style"], metadata["run_source"], metadata["status"]) == (mode, key.split("/")[1], "artifact", "completed")
    assert metadata["api_called"] is False


def test_engine_skips_failed_stages_of_exported_run(tmp_path, exported):
    run_dir = _write_run(tmp_path, exported["moment/reflective/failed"])
    outputs = load_step_outputs_from_run(run_dir, load_yaml(ROOT / FLOWS["moment"]))
    assert list(outputs) == ["sensory_capture"]


@pytest.mark.parametrize("key", ["deep/reflective", "moment/va-natural"])
def test_offline_learning_loop_runs_on_exported_run(tmp_path, exported, key):
    run_dir = _write_run(tmp_path / "exported", exported[key])
    primary = "edited_blog.md" if key.startswith("deep") else "moment_edited.md"
    (run_dir / "production_blog.md").write_text("Bản người viết đã sửa: mưa rơi, lòng dịu lại 🌧️.\n", encoding="utf-8")
    assert (run_dir / primary).exists()
    output_root = tmp_path / "learning"
    learning_dir = run_learning_loop(
        ROOT / "engine" / "config.example.yaml",
        run_dir,
        offline=True,
        persist=True,
        output_root=output_root,
        run_source="test",
    )
    assert Path(learning_dir).resolve().is_relative_to(output_root.resolve())
    assert (Path(learning_dir) / "metadata.json").exists()
