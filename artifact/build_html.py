"""Build trang Artifact một file: artifact/dist/index.html (ART-3).

Gộp bundle.json (từ build_bundle.py) và các ES module trong artifact/src thành
một trang HTML duy nhất, vì Artifact chạy ổn định nhất với script inline (đã
kiểm chứng ở spike ART-0). Bundler ở đây cố ý tối giản và chặt: chỉ nhận
`import { a, b } from "./x.js"` hoặc "../core/x.js" và `export function|class|const|let`;
cú pháp khác bị từ chối thay vì đoán.

Không gọi API, không ghi vào runs/.

    python artifact/build_html.py [--config engine/config.example.yaml] [--out artifact/dist/index.html]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from artifact.build_bundle import DEFAULT_CONFIG, BundleBuildError, build_bundle_content, serialize  # noqa: E402

SRC = ROOT / "artifact" / "src"
ENTRY = "ui/app"
TEMPLATE = SRC / "ui" / "page.html"
DEFAULT_OUT = ROOT / "artifact" / "dist" / "index.html"

IMPORT_RE = re.compile(r'^import\s*\{([^}]*)\}\s*from\s*"([^"]+)";[ \t]*$', re.M)
EXPORT_RE = re.compile(r"^export\s+(?:async\s+)?(function\*?|class|const|let)\s+([A-Za-z_$][\w$]*)", re.M)
ANY_IMPORT_EXPORT_RE = re.compile(r"^\s*(import|export)\b", re.M)


class HtmlBuildError(ValueError):
    pass


def _module_key(importer: str, specifier: str) -> str:
    if not specifier.startswith((".", "/")) or not specifier.endswith(".js"):
        raise HtmlBuildError(f"{importer}: chỉ hỗ trợ import tương đối tới file .js, gặp {specifier!r}.")
    target = (SRC / importer).parent.joinpath(specifier).resolve()
    try:
        return target.relative_to(SRC.resolve()).with_suffix("").as_posix()
    except ValueError as exc:
        raise HtmlBuildError(f"{importer}: import ra ngoài artifact/src: {specifier!r}.") from exc


def _parse_module(key: str) -> Tuple[List[Tuple[List[str], str]], List[str], str]:
    path = SRC / f"{key}.js"
    if not path.is_file():
        raise HtmlBuildError(f"Không có module {key}.js.")
    source = path.read_text(encoding="utf-8")
    imports = []
    for match in IMPORT_RE.finditer(source):
        names = [name.strip() for name in match.group(1).replace("\n", " ").split(",") if name.strip()]
        if any(" as " in name for name in names):
            raise HtmlBuildError(f"{key}.js: không hỗ trợ `import ... as ...`.")
        imports.append((names, _module_key(f"{key}.js", match.group(2))))
    body = IMPORT_RE.sub("", source)
    exports = [match.group(2) for match in EXPORT_RE.finditer(body)]
    body = EXPORT_RE.sub(lambda m: m.group(0)[len("export "):].lstrip(), body)
    leftover = ANY_IMPORT_EXPORT_RE.search(body)
    if leftover:
        line = body[: leftover.start()].count("\n") + 1
        raise HtmlBuildError(f"{key}.js: cú pháp import/export không hỗ trợ ở dòng gần {line}.")
    if "</script" in source.lower():
        raise HtmlBuildError(f"{key}.js chứa '</script', sẽ làm vỡ trang.")
    return imports, exports, body


def bundle_modules(entry: str = ENTRY) -> str:
    """Gộp module theo thứ tự phụ thuộc; mỗi module là một hàm riêng, chỉ lộ phần export."""
    parsed: Dict[str, Tuple[List[Tuple[List[str], str]], List[str], str]] = {}
    order: List[str] = []
    visiting: List[str] = []

    def visit(key: str) -> None:
        if key in order:
            return
        if key in visiting:
            raise HtmlBuildError("Import vòng: " + " -> ".join(visiting + [key]))
        visiting.append(key)
        parsed[key] = _parse_module(key)
        for _, dependency in parsed[key][0]:
            visit(dependency)
        visiting.pop()
        order.append(key)

    visit(entry)
    chunks = []
    for key in order:
        imports, exports, body = parsed[key]
        lines = [f"// --- {key}.js", f"const {_var(key)} = (() => {{"]
        for names, dependency in imports:
            missing = [name for name in names if name not in parsed[dependency][1]]
            if missing:
                raise HtmlBuildError(f"{key}.js import tên không được export bởi {dependency}.js: {missing}")
            lines.append(f"  const {{ {', '.join(names)} }} = {_var(dependency)};")
        lines.append(body.strip("\n"))
        lines.append(f"  return {{ {', '.join(exports)} }};")
        lines.append("})();")
        chunks.append("\n".join(lines))
    return "\n\n".join(chunks) + "\n"


def _var(key: str) -> str:
    return "__module_" + re.sub(r"\W", "_", key)


def source_commit() -> Dict[str, str | None]:
    """Commit nguồn của bản build (để đồng đội so phiên bản); None nếu không có git."""
    try:
        out = subprocess.run(
            ["git", "-C", str(ROOT), "log", "-1", "--format=%h|%cI"],
            capture_output=True, text=True, timeout=10, check=True,
        ).stdout.strip()
        commit, date = out.split("|", 1)
        return {"commit": commit, "commit_date": date}
    except (OSError, subprocess.SubprocessError, ValueError):
        return {"commit": None, "commit_date": None}


def build_html(config_path: Path = DEFAULT_CONFIG) -> Tuple[str, str]:
    """Trả (content_hash của bundle, nội dung trang)."""
    content_hash, bundle_text = serialize(build_bundle_content(config_path))
    template = TEMPLATE.read_text(encoding="utf-8")
    for marker in ("/*__BUNDLE__*/", "/*__SCRIPT__*/", "/*__BUILD_INFO__*/"):
        if template.count(marker) != 1:
            raise HtmlBuildError(f"Template phải có đúng một {marker}.")
    # "<\/" là escape hợp lệ trong chuỗi JSON và chặn việc đóng thẻ script sớm.
    safe_bundle = bundle_text.strip().replace("</", "<\\/")
    page = template.replace("/*__BUNDLE__*/", safe_bundle).replace("/*__SCRIPT__*/", bundle_modules())
    # Tem phiên bản: build_id phủ cả code lẫn dữ liệu (content_hash chỉ phủ dữ liệu).
    build_info = {
        "build_id": hashlib.sha256(page.encode("utf-8")).hexdigest()[:12],
        "bundle_hash": content_hash,
        **source_commit(),
    }
    page = page.replace("/*__BUILD_INFO__*/", json.dumps(build_info, ensure_ascii=False))
    return content_hash, page


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    try:
        content_hash, page = build_html(args.config)
    except (BundleBuildError, HtmlBuildError) as exc:
        print(f"Build thất bại: {exc}", file=sys.stderr)
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(page, encoding="utf-8", newline="\n")
    print(json.dumps({"content_hash": content_hash, "out": str(args.out), "bytes": args.out.stat().st_size}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
