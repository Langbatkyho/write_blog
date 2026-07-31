from __future__ import annotations

from typing import Any, MutableMapping


SESSION_DEFAULTS: dict[str, Any] = {
    "mode": "deep",
    "selected_style_slug": "reflective",
    "active_tab": 0,
    "vl_step": 1,
    "vl_samples": [""],
    "vl_dna": None,
    "vl_claims": [],
    "vl_interview": [],
    "vl_answers": {},
    "vl_calibration": None,
    "vl_calibration_selection": None,
    "vl_interview_patch": None,
    "vl_profile": None,
    "vl_compiled_ir": {},
    "vl_style_name": "",
    "vl_style_slug": "",
    "bw_step": 1,
    "bw_input_text": "",
    "bw_article_length": 600,
    "bw_ai_result": "",
    "bw_run_log": "",
    "bw_human_edited": "",
    "bw_tuning_suggestions": "",
    "bw_run_dir": "",
}

VOICE_LAB_TRANSIENT_KEYS = (
    "vl_step",
    "vl_dna",
    "vl_claims",
    "vl_interview",
    "vl_answers",
    "vl_calibration",
    "vl_calibration_selection",
    "vl_interview_patch",
    "vl_profile",
    "vl_compiled_ir",
)

BLOG_WORKFLOW_TRANSIENT_KEYS = (
    "bw_step",
    "bw_input_text",
    "bw_article_length",
    "bw_ai_result",
    "bw_run_log",
    "bw_human_edited",
    "bw_tuning_suggestions",
    "bw_run_dir",
)


def initialize_session_state(state: MutableMapping[str, Any]) -> None:
    for key, value in SESSION_DEFAULTS.items():
        if key not in state:
            state[key] = value.copy() if isinstance(value, (dict, list)) else value


def reset_voice_lab_state(state: MutableMapping[str, Any]) -> None:
    for key in VOICE_LAB_TRANSIENT_KEYS:
        value = SESSION_DEFAULTS[key]
        state[key] = value.copy() if isinstance(value, (dict, list)) else value


def reset_blog_workflow_state(state: MutableMapping[str, Any]) -> None:
    for key in BLOG_WORKFLOW_TRANSIENT_KEYS:
        value = SESSION_DEFAULTS[key]
        state[key] = value.copy() if isinstance(value, (dict, list)) else value


def switch_mode(state: MutableMapping[str, Any], mode: str) -> bool:
    if mode not in {"deep", "moment"}:
        raise ValueError(f"Mode không hợp lệ: {mode}")
    if state.get("mode") == mode:
        return False
    state["mode"] = mode
    state["selected_style_slug"] = "reflective"
    reset_voice_lab_state(state)
    reset_blog_workflow_state(state)
    return True
