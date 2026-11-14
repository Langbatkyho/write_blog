"""Build trang spike ART-0 (docs/2026-11-14-claude-artifact-plan.md).

Chỉ dựng prompt bằng hàm Python thuần từ fixture trong examples/.
Không gọi run_workflow(), không gọi API, không ghi vào runs/.

    python artifact/spike/build_spike.py <output.html>
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from engine.utils import load_yaml  # noqa: E402
from engine.voice_lab.prompts import analysis_schema, build_analysis_prompt  # noqa: E402
from engine.workflow_context import build_step_prompt  # noqa: E402

DEEP_INPUT = ROOT / "examples" / "blog_1.md"
VL_SAMPLES = [
    ROOT / "examples" / "finals" / name
    for name in (
        "VA_ket_noi_thien_nhien.md",
        "VA_ngheo_ma_hanh_phuc.md",
        "VA_nguoi_vo_su.md",
        "VA_vitamin_xanh.md",
    )
]


def writing_agent_prompt() -> str:
    workflow = load_yaml(ROOT / "flow" / "write_blog.yaml")
    step = next(s for s in workflow["steps"] if s["id"] == "writing_agent")
    skill = load_yaml(ROOT / "skills" / "deep" / "reflective" / "writing_agent.yaml")
    author_input = DEEP_INPUT.read_text(encoding="utf-8")
    return build_step_prompt(
        workflow, step, skill, author_input, {"handoffs": {}, "artifacts": {}}
    )


def analysis_prompt() -> str:
    samples = [
        {"sample_id": f"sample_{i + 1}", "content": p.read_text(encoding="utf-8")}
        for i, p in enumerate(VL_SAMPLES)
    ]
    # Gemini nhận schema qua API; sample.json của Artifact thì không, nên nhúng schema vào prompt.
    schema = json.dumps(analysis_schema(), ensure_ascii=False)
    return build_analysis_prompt(samples) + "\n\nRESPONSE SCHEMA (JSON Schema)\n" + schema


def main() -> None:
    out = Path(sys.argv[1])
    data = {
        "writing_agent_prompt": writing_agent_prompt(),
        "analysis_prompt": analysis_prompt(),
        "analysis_schema": analysis_schema(),
    }
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    build_id = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]
    template = (Path(__file__).parent / "spike_template.html").read_text(encoding="utf-8")
    html = template.replace("/*__SPIKE_DATA__*/null", payload).replace("__BUILD_ID__", build_id)
    out.write_text(html, encoding="utf-8")
    sizes = {k: len(v.encode("utf-8")) for k, v in data.items() if isinstance(v, str)}
    print(json.dumps({"out": str(out), "build_id": build_id, "prompt_bytes": sizes}))


if __name__ == "__main__":
    main()
