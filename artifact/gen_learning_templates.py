"""Sinh artifact/src/core/learning_templates.js từ mã nguồn engine/learning.py (ART-5).

Các template f-string của learning loop được tách bằng `ast` thành đoạn chữ cố
định và chỗ chèn giá trị (giữ biểu thức gốc và format spec), nên phần JS không
phải chép tay văn bản và engine vẫn là nguồn chân lý duy nhất.

    python artifact/gen_learning_templates.py          # ghi lại file JS
    python artifact/gen_learning_templates.py --check  # báo lỗi nếu file JS đã cũ
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "engine" / "learning.py"
TARGET = ROOT / "artifact" / "src" / "core" / "learning_templates.js"
FUNCTIONS = {
    "build_learning_prompt": "LEARNING_PROMPT_TEMPLATE",
    "build_tuning_prompt": "TUNING_PROMPT_TEMPLATE",
    "build_offline_learning_report": "OFFLINE_REPORT_TEMPLATE",
    "build_offline_tuning_suggestions": "OFFLINE_TUNING_TEMPLATE",
}


def _dedent_template(function: ast.FunctionDef, source: str) -> List[Dict[str, Any]]:
    """Template là đối số f-string duy nhất của lời gọi textwrap.dedent(...) trong hàm."""
    calls = [
        node
        for node in ast.walk(function)
        if isinstance(node, ast.Call)
        and ast.unparse(node.func) == "textwrap.dedent"
        and node.args
        and isinstance(node.args[0], ast.JoinedStr)
    ]
    if len(calls) != 1:
        raise SystemExit(f"{function.name}: cần đúng một textwrap.dedent(f-string), thấy {len(calls)}.")
    segments: List[Dict[str, Any]] = []
    for part in calls[0].args[0].values:
        if isinstance(part, ast.Constant):
            segments.append({"text": part.value})
        elif isinstance(part, ast.FormattedValue):
            spec = ""
            if part.format_spec is not None:
                spec = "".join(v.value for v in part.format_spec.values if isinstance(v, ast.Constant))
            if part.conversion != -1:
                raise SystemExit(f"{function.name}: không hỗ trợ !r/!s/!a.")
            segments.append({"expr": ast.get_source_segment(source, part.value), "spec": spec})
        else:
            raise SystemExit(f"{function.name}: phần tử f-string lạ {type(part).__name__}.")
    return segments


def render() -> str:
    source = SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    lines = [
        "// File sinh tự động bởi artifact/gen_learning_templates.py từ engine/learning.py.",
        "// Không sửa tay: sửa engine rồi chạy lại script. Mỗi phần tử là đoạn chữ cố định",
        "// ({text}) hoặc chỗ chèn giá trị ({expr, spec}) với biểu thức Python gốc làm khóa.",
        "",
    ]
    for name, const in FUNCTIONS.items():
        segments = _dedent_template(functions[name], source)
        lines.append(f"export const {const} = {json.dumps(segments, ensure_ascii=False, indent=1)};")
        lines.append("")
    return "\n".join(lines)


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    text = render()
    if args.check:
        if not TARGET.exists() or TARGET.read_text(encoding="utf-8") != text:
            print("learning_templates.js đã cũ. Chạy: python artifact/gen_learning_templates.py", file=sys.stderr)
            return 1
        print("learning_templates.js khớp engine/learning.py.")
        return 0
    TARGET.write_text(text, encoding="utf-8", newline="\n")
    print(json.dumps({"out": str(TARGET), "bytes": len(text.encode("utf-8"))}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
