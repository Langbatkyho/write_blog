"""ART-3: build trang Artifact một file (artifact/build_html.py).

Ghi file vào tmp_path; không gọi API, không ghi runs/.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from artifact import build_html as bh  # noqa: E402

SCRIPT_RE = re.compile(r'<script type="module">\n(.*)</script>', re.S)
BUNDLE_RE = re.compile(r'<script type="application/json" id="bundle-data">(.*?)</script>', re.S)


@pytest.fixture(scope="module")
def page() -> str:
    return bh.build_html()[1]


def test_build_is_deterministic(tmp_path):
    first, second = tmp_path / "a.html", tmp_path / "b.html"
    assert bh.main(["--out", str(first)]) == 0
    assert bh.main(["--out", str(second)]) == 0
    assert first.read_bytes() == second.read_bytes()


def test_page_embeds_bundle_and_all_modules(page):
    bundle = json.loads(BUNDLE_RE.search(page).group(1))
    assert bundle["bundle_format"] == 1
    assert page.count("<title>") == 1 and "<title>Mindful Blog Workflow</title>" in page
    script = SCRIPT_RE.search(page).group(1)
    for module in ("core/contracts", "core/orchestrator", "core/client_sample", "ui/app"):
        assert f"// --- {module}.js" in script
    assert script.index("// --- core/orchestrator.js") < script.index("// --- ui/app.js")
    assert not re.search(r"^\s*(import|export)\b", script, re.M)


@pytest.mark.skipif(shutil.which("node") is None, reason="Cần Node.js để kiểm tra cú pháp.")
def test_page_script_is_valid_javascript(page, tmp_path):
    script = tmp_path / "page.mjs"
    script.write_text(SCRIPT_RE.search(page).group(1), encoding="utf-8")
    result = subprocess.run(["node", "--check", str(script)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


@pytest.fixture
def fake_src(tmp_path, monkeypatch):
    (tmp_path / "ui").mkdir()
    (tmp_path / "core").mkdir()
    monkeypatch.setattr(bh, "SRC", tmp_path)
    return tmp_path


def _write(src: Path, key: str, text: str) -> None:
    (src / f"{key}.js").write_text(text, encoding="utf-8")


def test_bundler_scopes_modules_and_exposes_exports(fake_src):
    _write(fake_src, "core/a", 'const hidden = 1;\nexport function shown() { return hidden; }\n')
    _write(fake_src, "core/b", 'const hidden = 2;\nexport const value = hidden;\n')
    _write(fake_src, "ui/app", 'import { shown } from "../core/a.js";\nimport { value } from "../core/b.js";\nshown(value);\n')
    script = bh.bundle_modules()
    assert "const { shown } = __module_core_a;" in script
    assert "return { shown };" in script and "return { value };" in script
    assert script.count("const hidden") == 2  # mỗi module có phạm vi riêng nên không đụng tên


@pytest.mark.parametrize(
    "files, message",
    [
        ({"ui/app": "export default 1;\n"}, "không hỗ trợ"),
        ({"ui/app": 'import x from "../core/a.js";\n'}, "không hỗ trợ"),
        ({"ui/app": 'import { a } from "lib";\n'}, "import tương đối"),
        ({"ui/app": 'import { a } from "../../outside.js";\n'}, "ra ngoài"),
        ({"ui/app": 'import { missing } from "../core/a.js";\n', "core/a": "export const a = 1;\n"}, "không được export"),
        ({"ui/app": 'import { a } from "../core/a.js";\n', "core/a": 'import { b } from "./b.js";\nexport const a = b;\n', "core/b": 'import { a } from "./a.js";\nexport const b = a;\n'}, "Import vòng"),
        ({"ui/app": 'const s = "</script>";\n'}, "</script"),
        ({"ui/app": 'import { a as b } from "../core/a.js";\n', "core/a": "export const a = 1;\n"}, "as"),
    ],
)
def test_bundler_rejects_unsupported_input(fake_src, files, message):
    for key, text in files.items():
        _write(fake_src, key, text)
    with pytest.raises(bh.HtmlBuildError, match=message):
        bh.bundle_modules()
