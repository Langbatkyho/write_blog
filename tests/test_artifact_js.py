"""ART-2: chạy bộ test JS của Claude Artifact trong regression của dự án.

Test JS dùng client giả, không gọi API. Bundle được build vào thư mục tạm của
hệ điều hành; không ghi vào repo hay runs/.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ARTIFACT_DIR = Path(__file__).resolve().parents[1] / "artifact"


@pytest.mark.skipif(shutil.which("node") is None, reason="Cần Node.js >= 22 để chạy test JS.")
def test_artifact_js_suite_passes():
    result = subprocess.run(
        ["node", "--test", "tests/js/**/*.test.js"],
        cwd=ARTIFACT_DIR,
        env={**os.environ, "PYTHON": sys.executable},
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=600,
    )
    summary = "\n".join(line for line in result.stdout.splitlines() if line.startswith(("# tests", "# pass", "# fail", "not ok")))
    assert result.returncode == 0, f"Test JS lỗi:\n{summary}\n{result.stdout[-4000:]}\n{result.stderr[-2000:]}"
    assert "# fail 0" in result.stdout, summary
