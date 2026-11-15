"""Sinh golden fixtures cho phần JS của Claude Artifact (ART-1, O-05).

Mỗi fixture ghi lại input và output thật của hàm Python trong engine. Test JS
(ART-2, ART-8.1) chạy cùng input và phải ra đúng output, nhờ vậy prompt,
parser và compiler của Artifact không lệch khỏi engine (rủi ro R1).

Chỉ gọi hàm thuần; input lấy từ fixture trong examples/ và chuỗi giả lập.
Không gọi run_workflow(), không gọi API, không ghi vào runs/.

    python artifact/make_golden.py          # ghi lại artifact/tests/golden/
    python artifact/make_golden.py --check  # báo lỗi nếu golden đã cũ
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import warnings
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.learning import (  # noqa: E402
    build_learning_prompt,
    build_offline_learning_report,
    build_offline_tuning_suggestions,
    build_tuning_prompt,
    render_offline_diff,
)
from engine.parser import (  # noqa: E402
    average_sentence_words,
    build_context_package,
    count_paragraphs,
    count_words,
    estimate_tokens,
    parse_stage_response,
    truncate_words,
)
from engine.utils import load_yaml, read_text, resolve_path  # noqa: E402
from engine.voice_lab.calibration import DEFAULT_CONTENT_BRIEF  # noqa: E402
from engine.voice_lab.compiler import compile_style  # noqa: E402
from engine.voice_lab.models import (  # noqa: E402
    StyleProfile,
    VoiceDNA,
    compute_profile_confidence,
)
from engine.voice_lab.parser import build_voice_dna, validate_evidence  # noqa: E402
from engine.voice_lab.prompts import (  # noqa: E402
    build_analysis_prompt,
    build_calibration_prompt,
    build_interview_patch_prompt,
    build_synthesis_prompt,
)
from engine.workflow_artifacts import derive_artifact_file_contents  # noqa: E402
from engine.workflow_context import build_step_prompt  # noqa: E402
from engine.workflow_resolution import load_workflow_skills, resolve_step_skill_path  # noqa: E402

GOLDEN_DIR = ROOT / "artifact" / "tests" / "golden"
FIXED_TIME = dt.datetime(2026, 11, 14, 0, 0, tzinfo=dt.timezone.utc)
WORKFLOW_FILES = {"deep": "flow/write_blog.yaml", "moment": "flow/write_moment_blog.yaml"}
VA_SAMPLES = [
    "examples/finals/VA_ket_noi_thien_nhien.md",
    "examples/finals/VA_ngheo_ma_hanh_phuc.md",
    "examples/finals/VA_nguoi_vo_su.md",
    "examples/finals/VA_vitamin_xanh.md",
]
# 1.600 từ: vượt mọi ngân sách token của learning prompt (lớn nhất khoảng 1.333 từ) để kích hoạt cắt ngắn.
LONG_TEXT = "Mình ngồi bên cửa sổ, nghe mưa rơi trên mái tôn và thấy lòng dịu lại 🌧️. " * 100


def _workflow(mode: str) -> Dict[str, Any]:
    return load_yaml(resolve_path(WORKFLOW_FILES[mode]))


def _fake_output(stage_id: str) -> Dict[str, str]:
    if stage_id in {"editor_agent", "breath_editor"}:
        artifact = (
            "## Edited Blog\n\nBản đã biên tập của stage giả lập, giữ giọng 'mình' 🌿.\n\n"
            "## Edit Log\n\n- Cắt một câu lặp.\n- Giữ nguyên emoji của tác giả."
        )
    else:
        artifact = (
            f"Artifact giả lập của stage `{stage_id}`.\n\n"
            "Dòng thứ hai có emoji 🌥️ và dấu tiếng Việt: Tà Xùa, biển mây."
        )
    return {
        "artifact": artifact,
        "handoff": f"Handoff giả lập của `{stage_id}`: tóm tắt ngắn cho stage sau.",
    }


# --- Workflow --------------------------------------------------------------

def golden_workflow_prompts() -> Dict[str, Any]:
    cases = []
    for mode, style, input_file in (
        ("deep", "reflective", "examples/blog_1.md"),
        ("moment", "va-natural", "examples/moment_1.md"),
    ):
        workflow = _workflow(mode)
        author_input = read_text(resolve_path(input_file))
        upstream: Dict[str, Dict[str, str]] = {}
        artifacts: Dict[str, str] = {}
        handoffs: Dict[str, str] = {}
        stages = []
        for step in workflow["steps"]:
            skill = load_yaml(resolve_step_skill_path(step, style, mode))
            package = build_context_package(step, artifacts, handoffs)
            stages.append(
                {
                    "stage_id": step["id"],
                    "context_package": package,
                    "prompt": build_step_prompt(workflow, step, skill, author_input, package),
                }
            )
            output = _fake_output(step["id"])
            upstream[step["id"]] = output
            artifacts[step["id"]] = output["artifact"]
            handoffs[step["id"]] = output["handoff"]
        cases.append(
            {
                "mode": mode,
                "style": style,
                "input_file": input_file,
                "author_input": author_input,
                "upstream": upstream,
                "stages": stages,
                "note": "Stage thứ n chỉ thấy artifact/handoff của các stage đứng trước nó trong upstream.",
            }
        )
    return {"description": "build_context_package + build_step_prompt", "cases": cases}


def golden_parser_cases() -> Dict[str, Any]:
    strict_inputs = {
        "ok": "## Artifact\n\nNội dung bài.\n\n## Handoff\n\nTóm tắt.",
        "preamble_allowed": "Đây là kết quả:\n\n## Artifact\n\nBài viết.\n\n## Handoff\n\nHandoff.",
        "case_and_trailing_space": "## artifact  \nA\n##\tHANDOFF\nH",
        "wrong_order": "## Handoff\n\nH\n\n## Artifact\n\nA",
        "missing_handoff": "## Artifact\n\nChỉ có artifact.",
        "empty_artifact": "## Artifact\n\n\n## Handoff\n\nH",
        "duplicate_artifact": "## Artifact\nA\n## Artifact\nB\n## Handoff\nH",
        "heading_level_three_ignored": "## Artifact\n\n### Handoff\n\nvẫn là artifact\n\n## Handoff\n\nH",
        "crlf": "## Artifact\r\n\r\nA\r\n\r\n## Handoff\r\n\r\nH",
        # Từ tests/test_handoff_parser.py
        "py_test_exact_contract": "## Artifact\n\nNội dung đầy đủ.\n\n### Chi tiết hợp lệ\n\nMột mục con.\n\n## Tiêu đề H2 thuộc Artifact\n\nNội dung bài viết.\n\n## Handoff\n\nTóm tắt bàn giao.\n",
        "py_test_trailing_duplicate_handoff": "## Artifact\nA\n## Handoff\nH\n## Handoff\nH2\n",
        "bom_before_artifact": "\ufeff## Artifact\n\nA\n\n## Handoff\n\nH",
    }
    strict = []
    for name, text in strict_inputs.items():
        try:
            artifact, handoff, _ = parse_stage_response(text, strict=True)
            strict.append({"name": name, "input": text, "ok": True, "artifact": artifact, "handoff": handoff})
        except ValueError as exc:
            strict.append({"name": name, "input": text, "ok": False, "error": str(exc)})

    word_texts = [
        "Mình đi Tà Xùa lần thứ 5",
        "🌥️🌥️🌥️ biển mây",
        "snake_case và số 2026, dấu-gạch",
        "Emoji ghép 👩‍👩‍👧 và ZWJ",
        "  \n\t ",
        LONG_TEXT[:400],
    ]
    words = [{"text": t, "count_words": count_words(t), "estimate_tokens": estimate_tokens(t)} for t in word_texts]
    truncation = [
        {"text": t, "max_words": n, "result": truncate_words(t, max_words=n)}
        for t, n in ((LONG_TEXT, 30), ("ngắn thôi", 30), ("  một hai ba bốn  ", 3))
    ]

    split_skills = {
        "deep/reflective/editor_agent": load_yaml(resolve_path("skills/deep/reflective/editor_agent.yaml")),
        "moment/va-natural/breath_editor": load_yaml(resolve_path("skills/moment/va-natural/breath_editor.yaml")),
        "deep/reflective/story_architect": load_yaml(resolve_path("skills/deep/reflective/story_architect.yaml")),
    }
    split_artifacts = {
        "edited_blog_and_log": "## Edited Blog\n\nBài đã sửa.\n\n## Edit Log\n\n- Sửa 1",
        "snake_case_headings": "### edited_blog\n\nBài đã sửa.\n\n### edit_log\n\n- Sửa 1",
        "edited_draft_heading": "## Edited Draft\nBài.\n## Edit Log\nLog.",
        "no_headings": "Chỉ có bài, không có tiêu đề nào.",
        # Moment: tiêu đề theo output.sections hoặc theo tên file (lỗi thấy khi nghiệm thu ART-3)
        "moment_section_headings": "## edited_moment_blog\n\nBài khoảnh khắc 🌿\n\n## edit_log\n\n- Cắt một câu.",
        "moment_spaced_headings": "## Edited Moment Blog\n\nBài khoảnh khắc 🌿\n\n## Edit Log\n\n- Cắt một câu.",
        "moment_filename_headings": "### moment_edited.md\n\nBài khoảnh khắc 🌿\n\n### edit_log.md\n\n- Cắt một câu.",
        # Từ tests/test_handoff_parser.py: giữ H2 nội bộ của bài
        "internal_blog_headings": "## Edited Blog\n\n# Kết nối\n\n## Nơi mình thuộc về\n\nEdited article section.\n\n## Vẫn đi tiếp\n\nAnother edited article section.\n\n## Edit Log\n\n- Merged two paragraphs.\n",
    }
    splits = []
    for skill_name, skill in split_skills.items():
        for artifact_name, artifact in split_artifacts.items():
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                files = derive_artifact_file_contents(skill, artifact)
            splits.append(
                {
                    "skill": skill_name,
                    "artifact_case": artifact_name,
                    "artifact": artifact,
                    "files": files,
                    "warned": any(issubclass(w.category, UserWarning) for w in caught),
                }
            )
    return {
        "description": "parse_stage_response(strict=True), count_words, estimate_tokens, truncate_words, derive_artifact_file_contents",
        "strict_parse": strict,
        "words": words,
        "truncate_words": truncation,
        "artifact_split": splits,
        "note": "artifact_split dùng skill data trong bundle: styles[mode][style].files[<file>].data",
    }


# --- Learning --------------------------------------------------------------

def golden_learning_prompts() -> Dict[str, Any]:
    def step_outputs(mode: str, long: bool) -> Dict[str, str]:
        return {
            step["id"]: (LONG_TEXT if long else _fake_output(step["id"])["artifact"])
            for step in _workflow(mode)["steps"]
        }

    specs = [
        ("deep_short", "deep", "reflective", "examples/blog_1.md", False, "final_blog.md", 12000),
        ("deep_long_truncated", "deep", "reflective", "examples/blog_1.md", True, "final_blog.md", 12000),
        ("moment_short", "moment", "va-natural", "examples/moment_1.md", False, "moment_edited.md", 12000),
        ("budget_exceeded", "deep", "reflective", "examples/blog_1.md", False, "final_blog.md", 1500),
    ]
    learning = []
    for name, mode, style, input_file, long, label, budget in specs:
        inputs = {
            "mode": mode,
            "style": style,
            "author_input": read_text(resolve_path(input_file)),
            "step_outputs": step_outputs(mode, long),
            "final_blog": LONG_TEXT if long else "Bản nháp AI: Hoa nở không vì ai 🌷.",
            "production_blog": LONG_TEXT if long else "Bản người viết đã sửa: Hoa cứ là hoa 🌷.",
            "comparison_label": label,
            "max_context_tokens": budget,
        }
        entry: Dict[str, Any] = {"name": name, "inputs": inputs}
        try:
            entry["prompt"] = build_learning_prompt(
                workflow=_workflow(mode),
                skills=load_workflow_skills(_workflow(mode), style, mode),
                author_input=inputs["author_input"],
                step_outputs=inputs["step_outputs"],
                final_blog=inputs["final_blog"],
                production_blog=inputs["production_blog"],
                comparison_label=label,
                mode=mode,
                max_context_tokens=budget,
            )
        except ValueError as exc:
            entry["error"] = str(exc)
        learning.append(entry)

    tuning = []
    for name, report, mode, budget in (
        ("deep_short", "## Báo cáo\n\n- Người viết bỏ emoji ở cuối bài.", "deep", 6000),
        ("moment_long_truncated", LONG_TEXT * 2, "moment", 6000),
    ):
        stage_ids = [step["id"] for step in _workflow(mode)["steps"]]
        entry = {"name": name, "inputs": {"report": report, "mode": mode, "stage_ids": stage_ids, "max_context_tokens": budget}}
        try:
            entry["prompt"] = build_tuning_prompt(report, mode=mode, stage_ids=stage_ids, max_context_tokens=budget)
        except ValueError as exc:
            entry["error"] = str(exc)
        tuning.append(entry)
    ai_draft = (
        "# Chiều mưa\n\nMưa rơi trên mái tôn. Mình ngồi yên, không vội.\n\n"
        "Ly cà phê tan đá. Hình như không cần giải quyết mọi thứ ngay lập tức.\n\n"
        "Người ơi, chậm lại một chút cũng được 🌿."
    )
    human_edit = (
        "# Chiều mưa qua khung cửa\n\nMưa rơi trên mái tôn. Mình ngồi yên.\n\n"
        "Ly cà phê tan đá, chiếc lá bàng rơi nghiêng chạm vũng nước. Không cần vội.\n\n"
        "Người ơi, chậm lại một chút cũng được 🌿.\n\nMưa tạnh rồi đi tiếp."
    )
    offline_specs = [
        ("moment_edit", "moment", "moment_edited.md", ai_draft, human_edit, True),
        ("identical", "deep", "edited_blog.md", ai_draft, ai_draft, True),
        ("long_autojunk", "deep", "final_blog.md", LONG_TEXT, LONG_TEXT.replace("dịu lại", "nhẹ đi", 7) + "\nĐoạn kết mới.", True),
        ("shorter_no_steps", "moment", "moment_edited.md", human_edit, "Mưa.\nMình ngồi.", False),
        ("crlf_and_blank_lines", "moment", "moment_edited.md", "A.\r\n\r\n\r\nB! C?", "A.\n  \nB!\n\nC? D。", True),
    ]
    offline = []
    for name, mode, label, final_blog, production_blog, with_steps in offline_specs:
        steps = {step["id"]: _fake_output(step["id"])["artifact"] for step in _workflow(mode)["steps"]} if with_steps else {}
        stage_ids = [step["id"] for step in _workflow(mode)["steps"]] if with_steps else []
        offline.append(
            {
                "name": name,
                "inputs": {"mode": mode, "comparison_label": label, "final_blog": final_blog, "production_blog": production_blog, "step_outputs": steps, "stage_ids": stage_ids},
                "report": build_offline_learning_report(final_blog, production_blog, steps, comparison_label=label, mode=mode),
                "tuning": build_offline_tuning_suggestions("", mode=mode, stage_ids=stage_ids),
                "diff": render_offline_diff(final_blog, production_blog, comparison_label=label),
                "metrics": {
                    "paragraphs": [count_paragraphs(final_blog), count_paragraphs(production_blog)],
                    "sentence_avg": [average_sentence_words(final_blog), average_sentence_words(production_blog)],
                },
            }
        )
    floats = [0.0625, 0.125, 2.675, 1.0005, 0.5, 1.5, 2.5, 0.1234567, 12.3456, 0.0, -0.0, 0.9995, 1 / 3, 99.995, 2 / 3, 7.125, 0.875]
    return {
        "description": "build_learning_prompt, build_tuning_prompt, báo cáo offline. YAML của workflow/skill lấy từ bundle.learning và styles[mode][style].learning_compact_skills_yaml.",
        "learning": learning,
        "tuning": tuning,
        "offline": offline,
        "format_fixed": [{"value": v, "3f": f"{v:.3f}", "2f": f"{v:.2f}"} for v in floats],
        "signed_int": [{"value": n, "+d": f"{n:+d}"} for n in (-12, -1, 0, 1, 40)],
    }


# --- Voice Lab -------------------------------------------------------------

def _va_samples() -> List[Dict[str, str]]:
    return [
        {"sample_id": f"sample_{i + 1}", "content": read_text(resolve_path(p)).replace("\r\n", "\n")}
        for i, p in enumerate(VA_SAMPLES)
    ]


def golden_voicelab_prompts() -> Dict[str, Any]:
    samples = _va_samples()
    evidence = [
        {"id": "ev-1", "sample_id": "sample_3", "dimension": "emoji", "claim": "Emoji cuối câu", "exact_quote": "Hoa thì không cần điều đó. 😇", "stance": "support"},
        {"id": "ev-2", "sample_id": "sample_1", "dimension": "tone", "claim": "Thừa nhận nỗi sợ", "exact_quote": "Mình rất sợ khi nhìn ra điều đó.", "stance": "support"},
    ]
    batch_dimensions = [{"tone": {"description": "Giọng tâm tình", "strength": 0.8, "do": ["Thừa nhận điểm yếu"], "avoid": []}}]
    current_dimensions = [
        {"dimension": "emoji", "profile": {"description": "Emoji vừa phải", "strength": 1.0, "do": [], "avoid": ["Rải emoji giữa câu"]}},
    ]
    answers = [{"question_id": "q-1", "dimension": "emoji", "question": "Bạn muốn dùng emoji thế nào?", "answer": "Ít thôi, chỉ ở cuối bài 🌿"}]
    fixed_constraints = {"tone": "Giọng tâm tình", "rhythm": "Nhịp ngắt quãng, strength 0.5"}
    return {
        "description": "Prompt Voice Lab của engine (bản Gemini). Bản Claude nối thêm JSON Schema vào cuối prompt (quyết định ART-0).",
        "note": "Các payload có số thực như 1.0: json.dumps của Python giữ '1.0' và dùng separators ', ' / ': '.",
        "analysis": {"inputs": {"samples": samples}, "prompt": build_analysis_prompt(samples)},
        "synthesis": {
            "inputs": {"verified_evidence": evidence, "batch_dimensions": batch_dimensions},
            "prompt": build_synthesis_prompt(evidence, batch_dimensions),
        },
        "interview_patch": {
            "inputs": {"current_dimensions": current_dimensions, "answers": answers},
            "prompt": build_interview_patch_prompt(current_dimensions, answers),
        },
        "calibration": {
            "inputs": {"dimension": "emoji", "description": "Emoji vừa phải ở cuối câu", "content_brief": DEFAULT_CONTENT_BRIEF, "fixed_constraints": fixed_constraints},
            "prompt": build_calibration_prompt("emoji", "Emoji vừa phải ở cuối câu", DEFAULT_CONTENT_BRIEF, fixed_constraints),
        },
    }


def _dump(model: Any) -> Any:
    return model.model_dump(mode="json")


def golden_voicelab_logic() -> Dict[str, Any]:
    samples_by_id = {
        "s1": "Sáng nay 🌿 mình ra ban công.\r\nHoa cứ là hoa. Mình biết vậy.",
        "s2": "Còn bạn thì sao?",
    }
    raw_evidence = [
        {"id": "e1", "sample_id": "s1", "dimension": "rhythm", "claim": "Câu ngắn", "exact_quote": "Hoa cứ là hoa.", "stance": "support"},
        {"id": "e2", "sample_id": "s1", "dimension": "tone", "claim": "Sau emoji, có CRLF", "exact_quote": "mình ra ban công.\r\nHoa", "stance": "support"},
        {"id": "e3", "sample_id": "s2", "dimension": "perspective", "claim": "Hỏi bạn đọc", "exact_quote": "Còn bạn thì sao?", "stance": "support"},
        {"id": "e4", "sample_id": "s1", "dimension": "rhythm", "claim": "Mâu thuẫn", "exact_quote": "Mình biết vậy.", "stance": "contradict"},
        {"id": "e5", "sample_id": "s1", "dimension": "tone", "claim": "Quote bị diễn đạt lại", "exact_quote": "Hoa là hoa.", "stance": "support"},
        {"id": "e6", "sample_id": "s9", "dimension": "tone", "claim": "Sample không tồn tại", "exact_quote": "Hoa cứ là hoa.", "stance": "support"},
        {"id": "e7", "sample_id": "s1", "dimension": "mood", "claim": "Dimension lạ", "exact_quote": "Hoa cứ là hoa.", "stance": "support"},
        {"id": "e8", "sample_id": "s2", "dimension": "emoji", "claim": "Quote rỗng", "exact_quote": "", "stance": "support"},
    ]
    active, rejected, counts = validate_evidence(raw_evidence, samples_by_id)
    evidence_case = {
        "inputs": {"evidence": raw_evidence, "samples_by_id": samples_by_id},
        "active": [_dump(c) for c in active],
        "rejected": [_dump(c) for c in rejected],
        "returned_by_dimension": counts,
        "note": "quote_start/quote_end tính theo code point (str.find của Python), không theo UTF-16.",
    }

    raw_dna = {
        "rhythm": {"description": "Câu ngắn đứng riêng", "strength": 0.8, "do": ["Tách câu ngắn"], "avoid": ["Câu dài lồng nhau"]},
        "tone": {"description": "Giọng tâm tình", "strength": 0.7, "do": ["Thừa nhận điểm yếu", "  "], "avoid": []},
        "perspective": {"description": "Xưng mình, hỏi bạn", "strength": 0.9, "do": [], "avoid": []},
        "humor": {"description": "Không có evidence nên phải rỗng", "strength": 0.4, "do": [], "avoid": []},
    }
    dna_cases = []
    for total_samples in (1, 2, 4):
        dna = build_voice_dna(raw_dna, active, rejected, counts, total_samples)
        profile = StyleProfile(slug="golden-voice", mode="deep", dna=dna, created_at=FIXED_TIME, updated_at=FIXED_TIME)
        dna_cases.append(
            {"total_samples": total_samples, "dna": _dump(dna), "profile_confidence": compute_profile_confidence(profile)}
        )

    full_dna = VoiceDNA.model_validate(
        {
            "tone": {"description": "Giọng tâm tình, tự trào nhẹ", "strength": 0.85, "do": ["Viết như tâm sự"], "avoid": ["Giảng đạo"], "examples": ["Cũng đúng mà :)", "ví dụ 2", "ví dụ 3"]},
            "emoji": {"description": "Emoji cuối câu", "strength": 0.5, "do": ["Đặt emoji cuối câu"], "avoid": ["Rải emoji giữa câu"]},
            "sensory_density": {"description": "Giác quan dày khi tả cảnh", "strength": 0.65, "do": ["Dùng từ láy"], "avoid": []},
            "perspective": {"description": "Xưng mình", "strength": 0.9, "do": ["Xưng mình"], "avoid": ["Xưng tôi"]},
        }
    )
    compile_cases = []
    for name, mode, base, changed, dna in (
        ("deep_full", "deep", "reflective", None, full_dna),
        ("deep_partial_emoji", "deep", "reflective", ["emoji", "khong_ton_tai"], full_dna),
        ("moment_full_base_va_natural", "moment", "va-natural", None, full_dna),
        ("moment_no_dna", "moment", "reflective", None, None),
        (
            "duplicate_do_avoid_error",
            "deep",
            "reflective",
            None,
            VoiceDNA.model_validate({"tone": {"description": "x", "do": ["Giảng đạo"], "avoid": ["giảng đạo "]}}),
        ),
    ):
        profile = StyleProfile(
            slug="golden-voice", mode=mode, base_style_slug=base, revision=3, dna=dna,
            created_at=FIXED_TIME, updated_at=FIXED_TIME,
        )
        entry: Dict[str, Any] = {"name": name, "inputs": {"profile": _dump(profile), "mode": mode, "changed_dimensions": changed}}
        try:
            entry["result"] = _dump(compile_style(profile, mode, changed))
        except ValueError as exc:
            entry["error"] = str(exc)
        compile_cases.append(entry)
    return {
        "description": "validate_evidence, build_voice_dna, compute_profile_confidence, compile_style. Base skill lấy từ bundle styles[mode][base].files.",
        "evidence": evidence_case,
        "dna": {"inputs": {"raw_dna": raw_dna}, "cases": dna_cases},
        "compile": compile_cases,
    }


# --- Voice Lab: luồng phân tích, phỏng vấn, calibration (ART-8.1) -----------

TIME_KEYS = {"created_at", "updated_at", "confirmed_at"}


def _scrub(value: Any) -> Any:
    """Thời điểm do utc_now() sinh nên không cố định: thay bằng '<time>'."""
    if isinstance(value, dict):
        return {k: ("<time>" if k in TIME_KEYS and v is not None else _scrub(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [_scrub(v) for v in value]
    return value


class _Ids:
    """uuid4 thay thế: id-0001, id-0002… theo thứ tự tạo."""

    def __init__(self) -> None:
        self.count = 0

    def __call__(self) -> str:
        self.count += 1
        return f"id-{self.count:04d}"


class _FixedRandom:
    def __init__(self, value: float) -> None:
        self.value = value

    def random(self) -> float:
        return self.value


def _patched_ids():
    import contextlib
    import engine.voice_lab.models as vl_models
    from unittest import mock

    ids = _Ids()

    @contextlib.contextmanager
    def ctx():
        with mock.patch.object(vl_models.uuid, "uuid4", side_effect=ids):
            yield ids

    return ctx()


def _recording_client(responses):
    """Gemini giả: trả lần lượt các phản hồi (chuỗi hoặc hàm của prompt) và ghi lại lời gọi."""
    calls: List[Dict[str, Any]] = []

    def client(prompt: str, *, stage_id: str, **_: Any) -> str:
        item = responses[len(calls)]
        text = item(prompt) if callable(item) else item
        calls.append({"stage_id": stage_id, "prompt": prompt, "response": text})
        return text

    return client, calls


def _analysis_error(fn) -> Dict[str, Any]:
    from engine.voice_lab.models import AnalysisError

    try:
        fn()
    except AnalysisError as exc:
        return {"code": exc.code, "user_message": exc.user_message}
    raise AssertionError("expected AnalysisError")


def _value_error(fn) -> str:
    try:
        fn()
    except ValueError as exc:
        return str(exc)
    raise AssertionError("expected ValueError")


def golden_voicelab_flow() -> Dict[str, Any]:
    import os
    from unittest import mock

    import engine.voice_lab.analyzer as vl_analyzer
    from engine.voice_lab.calibration import apply_calibration_selection, calibrate_ab
    from engine.voice_lab.interview_routing import generate_interview
    from engine.voice_lab.models import StyleProfile as Profile
    from engine.voice_lab.overrides import apply_conflict_resolutions, merge_overrides
    from engine.voice_lab.profile_patch import apply_interview_patch, propose_interview_patch
    from engine.voice_lab.prompts import (
        CalibrationPayload,
        InterviewPatchPayload,
        ModelAnalysisPayload,
        ModelSynthesisPayload,
    )

    out: Dict[str, Any] = {
        "description": "Luồng Voice Lab của engine với Gemini giả: estimate_tokens, _chunk_samples, analyze_samples (một lượt, nhiều lượt, lỗi), generate_interview, propose/apply_interview_patch, calibrate_ab, apply_calibration_selection, merge_overrides, kiểm tra schema. uuid4 thay bằng id-0001…; thời điểm thay bằng '<time>'.",
    }

    estimate_inputs = ["", "abc", "abcde", "Mình", "🌿", "Sáng nay 🌿 mình ra ban công.\nHoa cứ là hoa.", LONG_TEXT[:500]]
    out["estimate_tokens"] = [{"text": t, "tokens": vl_analyzer.estimate_tokens(t)} for t in estimate_inputs]

    long_vi = ("Sáng nay mình ra ban công 🌿, nghe chim hót và thấy lòng nhẹ hơn. " * 40).strip()
    chunk_samples = [
        {"sample_id": "sample_1", "content": "Short ascii sample."},
        {"sample_id": "sample_2", "content": long_vi},
        {"sample_id": "sample_3", "content": "Một đoạn trung bình, có emoji 😇 và xuống dòng.\nDòng thứ hai." * 6},
    ]
    out["chunk"] = [
        {"budget": budget, "batches": vl_analyzer._chunk_samples(chunk_samples, budget)}
        for budget in (300, 1000, 5000)
    ]
    out["chunk_inputs"] = chunk_samples

    # Phân tích một lượt.
    single_samples = [
        "Sáng nay 🌿 mình ra ban công.\r\nHoa cứ là hoa. Mình biết vậy.",
        "   ",
        "Còn bạn thì sao? Mình thì vẫn chưa biết. 😇",
    ]
    single_response = json.dumps(
        {
            "dna": {
                "tone": {"description": "Giọng tâm tình", "strength": 0.7, "do": ["Thừa nhận điểm yếu"], "avoid": []},
                "rhythm": {"description": "Câu ngắn đứng riêng", "strength": 0.8, "do": ["Tách câu"], "avoid": ["Câu dài"]},
                "emoji": {"description": "Emoji cuối câu", "strength": 1, "do": [], "avoid": ["Rải emoji"]},
                "humor": {"description": "Không có evidence", "strength": 0.3},
            },
            "evidence": [
                {"sample_id": "sample_1", "dimension": "rhythm", "claim": "Câu ngắn", "exact_quote": "Hoa cứ là hoa."},
                {"sample_id": "sample_1", "dimension": "tone", "claim": "Qua CRLF", "exact_quote": "ban công.\r\nHoa"},
                {"sample_id": "sample_3", "dimension": "emoji", "claim": "Emoji cuối", "exact_quote": "chưa biết. 😇"},
                {"sample_id": "sample_3", "dimension": "rhythm", "claim": "Mâu thuẫn", "exact_quote": "Mình thì vẫn chưa biết.", "stance": "contradict"},
                {"sample_id": "sample_3", "dimension": "tone", "claim": "Diễn đạt lại", "exact_quote": "Bạn thì sao?"},
                {"sample_id": "sample_2", "dimension": "tone", "claim": "Mẫu rỗng bị bỏ nên sample_2 không tồn tại", "exact_quote": "Hoa"},
            ],
            "warnings": ["Mẫu ngắn"],
        },
        ensure_ascii=False,
    )
    with _patched_ids(), mock.patch.dict(os.environ, {"VOICE_LAB_GEMINI_CONTEXT_TOKENS": "200000"}):
        client, calls = _recording_client([single_response])
        with mock.patch.object(vl_analyzer, "call_gemini", client):
            single = vl_analyzer.analyze_samples(single_samples, slug="golden-voice", mode="deep")
    single_profile = single.profile
    out["analyze_single"] = {
        "inputs": {"samples": single_samples, "slug": "golden-voice", "mode": "deep", "token_budget": int(200000 * vl_analyzer.INPUT_BUDGET_RATIO)},
        "calls": calls,
        "result": _scrub(single.model_dump(mode="json")),
    }

    # Phân tích nhiều lượt: ngân sách context 20.000 token (đủ chỗ cho prompt + output) với 4 bài mẫu thật.
    va = [read_text(resolve_path(p)) for p in VA_SAMPLES]
    # Lặp lại để vượt ngân sách: mẫu cuối dài hơn ngân sách nên bị cắt có gối đầu (CHUNK_OVERLAP_CHARS).
    multi_samples = [va[0] + "\n\n" + va[0], va[1] + "\r\n\r\n" + va[1], va[2], va[3], "\n\n".join(va * 5)]

    def batch_response(prompt: str) -> str:
        data = json.loads(prompt.split("SAMPLE_DATA\n", 1)[1])
        evidence = []
        for unit in data:
            content = unit["content"]
            evidence.append({"sample_id": unit["sample_id"], "dimension": "tone", "claim": "Mở đoạn", "exact_quote": content[:40]})
            evidence.append({"sample_id": unit["sample_id"], "dimension": "tone", "claim": "Trùng", "exact_quote": content[:40]})
            evidence.append({"sample_id": unit["sample_id"], "dimension": "rhythm", "claim": "Kết đoạn", "exact_quote": content[-25:]})
            evidence.append({"sample_id": unit["sample_id"], "dimension": "emoji", "claim": "Bịa", "exact_quote": "không có trong bài ✨"})
        return json.dumps(
            {"dna": {"tone": {"description": f"Giọng của lô {len(data)}", "strength": 0.6}}, "evidence": evidence, "warnings": []},
            ensure_ascii=False,
        )

    synthesis_response = json.dumps(
        {
            "dna": {
                "tone": {"description": "Giọng tâm tình, tự trào", "strength": 0.75, "do": ["Viết như tâm sự"], "avoid": ["Giảng đạo"]},
                "rhythm": {"description": "Kết đoạn bằng câu ngắn", "strength": 0.55},
            },
            "warnings": ["Tổng hợp từ nhiều lô"],
        },
        ensure_ascii=False,
    )
    with _patched_ids(), mock.patch.dict(os.environ, {"VOICE_LAB_GEMINI_CONTEXT_TOKENS": "20000"}):
        prepared = vl_analyzer._prepare_samples(multi_samples)
        batches = vl_analyzer._chunk_samples(prepared, int(20000 * vl_analyzer.INPUT_BUDGET_RATIO))
        client, calls = _recording_client([batch_response] * len(batches) + [synthesis_response])
        with mock.patch.object(vl_analyzer, "call_gemini", client):
            multi = vl_analyzer.analyze_samples(multi_samples, slug="golden-multi", mode="moment")
    out["analyze_multi"] = {
        "inputs": {"samples": multi_samples, "slug": "golden-multi", "mode": "moment", "token_budget": int(20000 * vl_analyzer.INPUT_BUDGET_RATIO)},
        "calls": calls,
        "result": _scrub(multi.model_dump(mode="json")),
    }

    def run_error(samples, responses):
        def go():
            client, _ = _recording_client(responses)
            with mock.patch.object(vl_analyzer, "call_gemini", client), mock.patch.dict(os.environ, {"VOICE_LAB_GEMINI_CONTEXT_TOKENS": "200000"}):
                vl_analyzer.analyze_samples(samples)
        return go

    ok_samples = ["Hoa cứ là hoa."]
    out["analyze_errors"] = [
        {"name": name, "samples": samples, "responses": responses, "error": _analysis_error(run_error(samples, responses))}
        for name, samples, responses in (
            ("not_json", ok_samples, ["không phải JSON"]),
            ("extra_field", ok_samples, ['{"dna": {}, "evidence": [], "warnings": [], "score": 1}']),
            ("bad_stance", ok_samples, ['{"evidence": [{"sample_id": "sample_1", "dimension": "tone", "claim": "x", "exact_quote": "Hoa", "stance": "maybe"}]}']),
            ("no_valid_evidence", ok_samples, ['{"dna": {"tone": {"description": "x"}}, "evidence": [{"sample_id": "sample_1", "dimension": "tone", "claim": "x", "exact_quote": "Hoa là hoa"}]}']),
            ("empty_samples", ["", "  \n "], []),
        )
    ]

    # Phỏng vấn.
    with _patched_ids():
        questions = generate_interview(single_profile)
    out["interview_questions"] = {"profile": _scrub(single_profile.model_dump(mode="json")), "questions": [q.model_dump(mode="json") for q in questions]}
    answers = {questions[0].id: "  Mình muốn giữ, nhưng nhẹ hơn 🌿  ", questions[1].id: "   ", questions[2].id: "Đổi hẳn: kể chậm lại."}
    patch_response = json.dumps(
        {
            "changes": [
                {"dimension": questions[0].dimension, "description": "Nhẹ hơn", "strength": 0.4, "do": ["Giữ"], "avoid": []},
                {"dimension": questions[2].dimension, "description": "Kể chậm", "strength": 0.25, "avoid": ["Vội"]},
                {"dimension": "tone" if questions[0].dimension != "tone" else "rhythm", "description": "Không được hỏi", "strength": 0.9},
            ]
        },
        ensure_ascii=False,
    )
    client, calls = _recording_client([patch_response])
    patch = propose_interview_patch(single_profile, questions, answers, gemini_client=client)
    empty_client, empty_calls = _recording_client([])
    empty_patch = propose_interview_patch(single_profile, questions, {}, gemini_client=empty_client)
    bad_client, _ = _recording_client(['{"changes": [{"dimension": "tone", "description": "x"}]}'])
    try:
        propose_interview_patch(single_profile, questions, answers, gemini_client=bad_client)
        bad_patch = None
    except Exception as exc:  # AnalysisError
        bad_patch = {"code": exc.code, "user_message": exc.user_message}
    patch_with_stranger = InterviewPatchPayload.model_validate(
        {"changes": [*patch.model_dump()["changes"], {"dimension": "mood", "description": "x", "strength": 0.5}]}
    )
    with _patched_ids():
        applied = apply_interview_patch(single_profile, patch_with_stranger, questions, answers, confirmed=True)
        follow_up = generate_interview(applied)
    out["interview_patch"] = {
        "answers": answers,
        "calls": calls,
        "patch": patch.model_dump(mode="json"),
        "empty_patch": empty_patch.model_dump(mode="json"),
        "empty_calls": len(empty_calls),
        "invalid_patch_error": bad_patch,
        "apply_patch_input": patch_with_stranger.model_dump(mode="json"),
        "applied_profile": _scrub(applied.model_dump(mode="json")),
        "unconfirmed_error": _value_error(lambda: apply_interview_patch(single_profile, patch, questions, answers, confirmed=False)),
        "follow_up_questions": [q.model_dump(mode="json") for q in follow_up],
    }

    # Calibration.
    amplified = " ".join(["Mình", "thả", "emoji", "🌿", "khắp", "nơi"] * 20)
    restrained = " ".join(["Mình", "giữ", "câu", "chữ", "thật", "yên"] * 18)
    cal_response = json.dumps({"variant_amplified": f"  {amplified}  ", "variant_restrained": restrained}, ensure_ascii=False)
    sessions = []
    with _patched_ids():
        for value in (0.3, 0.7):
            client, calls = _recording_client([cal_response])
            session = calibrate_ab("emoji", single_profile, rng=_FixedRandom(value), gemini_client=client)
            sessions.append({"random": value, "calls": calls, "session": _scrub(session.model_dump(mode="json"))})
        session = calibrate_ab("emoji", single_profile, rng=_FixedRandom(0.3), gemini_client=_recording_client([cal_response])[0])
        selected = apply_calibration_selection(single_profile, session, "B")

    def cal_error(response, dimension="emoji"):
        def go():
            calibrate_ab(dimension, single_profile, rng=_FixedRandom(0.1), gemini_client=_recording_client([response])[0])
        return go

    short = json.dumps({"variant_amplified": "Quá ngắn", "variant_restrained": restrained}, ensure_ascii=False)
    same = json.dumps({"variant_amplified": restrained, "variant_restrained": restrained}, ensure_ascii=False)
    out["calibration"] = {
        "sessions": sessions,
        "apply": {"session": _scrub(session.model_dump(mode="json")), "selected": "B", "profile": _scrub(selected.model_dump(mode="json"))},
        "reapply_error": _value_error(lambda: apply_calibration_selection(selected, session, "A")),
        "bad_label_error": _value_error(lambda: apply_calibration_selection(single_profile, session, "C")),
        "errors": [
            {"name": "too_short", "response": short, "error": _analysis_error(cal_error(short))},
            {"name": "identical", "response": same, "error": _analysis_error(cal_error(same))},
            {"name": "missing_field", "response": '{"variant_amplified": "x"}', "error": _analysis_error(cal_error('{"variant_amplified": "x"}'))},
        ],
        "value_errors": [
            {"dimension": "mood", "error": _value_error(cal_error(cal_response, "mood"))},
            {"dimension": "humor", "error": _value_error(cal_error(cal_response, "humor"))},
        ],
    }

    # Merge ba chiều của Canonical IR.
    full_dna = VoiceDNA.model_validate({"tone": {"description": "Giọng tâm tình", "strength": 0.85, "do": ["Viết như tâm sự"]}})
    compiled = compile_style(Profile(slug="m", mode="deep", dna=full_dna, created_at=FIXED_TIME, updated_at=FIXED_TIME), "deep")
    base_ir = compiled["writing_agent.yaml"]
    current_ir = json.loads(json.dumps(base_ir))
    current_ir["style_overlays"] = {"tone": ["Mô tả: bản đang chạy"]}
    override_ir = json.loads(json.dumps(base_ir))
    override_ir["style_overlays"] = {"tone": ["Mô tả: bản người dùng sửa"]}
    only_override = json.loads(json.dumps(base_ir))
    only_override["context_policy"] = {"reference": "đổi phía override"}
    bad_invariant = json.loads(json.dumps(base_ir))
    bad_invariant["base_hash"] = "x"
    merges = []
    for name, current, override in (
        ("unchanged", base_ir, base_ir),
        ("override_only", base_ir, only_override),
        ("current_only", current_ir, base_ir),
        ("both_changed", current_ir, override_ir),
        ("invariant_modified", base_ir, bad_invariant),
    ):
        merges.append({"name": name, "current": current, "override": override, "result": merge_overrides(base_ir, current, override).model_dump(mode="json")})
    conflict = merge_overrides(base_ir, current_ir, override_ir)
    resolved = apply_conflict_resolutions(conflict, {"style_overlays": override_ir["style_overlays"]})
    out["merge"] = {
        "base": base_ir,
        "cases": merges,
        "resolved": resolved,
        "missing_resolution_error": _value_error(lambda: apply_conflict_resolutions(conflict, {})),
        "unknown_resolution_error": _value_error(lambda: apply_conflict_resolutions(conflict, {"style_overlays": [], "x": 1})),
        "invariant_error": _value_error(lambda: apply_conflict_resolutions(merge_overrides(base_ir, base_ir, bad_invariant), {})),
        "mismatched_id_error": _value_error(lambda: merge_overrides(base_ir, {**base_ir, "id": "khác"}, base_ir)),
    }

    # Kiểm tra schema: kết luận của Pydantic với từng payload.
    def verdicts(model, payloads):
        rows = []
        for payload in payloads:
            text = json.dumps(payload, ensure_ascii=False)
            try:
                rows.append({"payload": payload, "valid": True, "value": model.model_validate_json(text).model_dump(mode="json")})
            except Exception:
                rows.append({"payload": payload, "valid": False})
        return rows

    fixed_profile = {**single_profile.model_dump(mode="json"), "created_at": "2026-11-14T00:00:00Z", "updated_at": "2026-11-14T00:00:00Z"}
    out["schema_cases"] = {
        "analysis_payload": verdicts(ModelAnalysisPayload, [
            {},
            {"dna": {"tone": {"description": "x"}}, "evidence": [{"sample_id": "s", "dimension": "tone", "claim": "c", "exact_quote": "q"}]},
            {"dna": {"tone": {"description": "x", "strength": 1}}, "warnings": ["w"]},
            {"dna": {"tone": {"description": "x", "strength": 1.5}}},
            {"dna": {"tone": {"description": "x", "strength": -0.1}}},
            {"dna": {"tone": {"description": "x", "confidence": 0.9}}},
            {"dna": {"tone": "x"}},
            {"evidence": [{"sample_id": "s", "dimension": "tone", "claim": "c"}]},
            {"evidence": [{"sample_id": "s", "dimension": "tone", "claim": "c", "exact_quote": "q", "stance": "neutral"}]},
            {"evidence": [{"sample_id": "s", "dimension": "tone", "claim": "c", "exact_quote": 5}]},
            {"warnings": "w"},
            {"warnings": [1]},
            {"evidence": {}},
            {"dna": {}, "extra": True},
            {"dna": {"tone": {"do": "x"}}},
            {"dna": None},
        ]),
        "synthesis_payload": verdicts(ModelSynthesisPayload, [
            {"dna": {"rhythm": {"description": "y", "strength": 0.0}}},
            {"dna": {"rhythm": {"description": "y"}}, "evidence": []},
        ]),
        "interview_patch_payload": verdicts(InterviewPatchPayload, [
            {"changes": [{"dimension": "tone", "description": "x", "strength": 0.5}]},
            {"changes": [{"dimension": "tone", "description": "x"}]},
            {"changes": [{"dimension": "tone", "description": "x", "strength": 0.5, "examples": []}]},
            {},
        ]),
        "calibration_payload": verdicts(CalibrationPayload, [
            {"variant_amplified": "a", "variant_restrained": "b"},
            {"variant_amplified": "a"},
            {"variant_amplified": "a", "variant_restrained": None},
        ]),
        "style_profile": verdicts(Profile, [
            fixed_profile,
            {**fixed_profile, "schema_version": 1},
            {**fixed_profile, "confidence": 2},
            {**fixed_profile, "created_at": "hôm qua"},
            {"slug": "x", "mode": "deep", "created_at": "2026-11-14T00:00:00Z", "updated_at": "2026-11-14T00:00:00Z"},
            {"slug": "x", "mode": "poem", "created_at": "2026-11-14T00:00:00Z", "updated_at": "2026-11-14T00:00:00Z"},
        ]),
    }
    out["schema_cases"]["style_profile"] = [{**row, "value": _scrub(row["value"])} if row["valid"] else row for row in out["schema_cases"]["style_profile"]]
    return out


GOLDEN_BUILDERS = {
    "workflow_prompts.json": golden_workflow_prompts,
    "parser_cases.json": golden_parser_cases,
    "learning_prompts.json": golden_learning_prompts,
    "voicelab_prompts.json": golden_voicelab_prompts,
    "voicelab_logic.json": golden_voicelab_logic,
    "voicelab_flow.json": golden_voicelab_flow,
}


def render_all() -> Dict[str, str]:
    return {
        name: json.dumps(builder(), ensure_ascii=False, indent=1) + "\n"
        for name, builder in GOLDEN_BUILDERS.items()
    }


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="Không ghi; báo lỗi nếu golden khác kết quả hiện tại.")
    args = parser.parse_args(argv)
    rendered = render_all()
    if args.check:
        stale = [n for n, text in rendered.items() if not (GOLDEN_DIR / n).exists() or (GOLDEN_DIR / n).read_text(encoding="utf-8") != text]
        if stale:
            print("Golden đã cũ: " + ", ".join(stale) + ". Chạy: python artifact/make_golden.py", file=sys.stderr)
            return 1
        print("Golden khớp engine hiện tại.")
        return 0
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    for name, text in rendered.items():
        (GOLDEN_DIR / name).write_text(text, encoding="utf-8", newline="\n")
    print(json.dumps({name: len(text.encode("utf-8")) for name, text in rendered.items()}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
