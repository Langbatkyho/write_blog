from __future__ import annotations

import copy
import hashlib
import json
from typing import Any, Dict, List, Optional

from engine.utils import load_yaml, resolve_path
from engine.voice_lab.models import (
    CanonicalIR,
    CompileResult,
    DimensionProfile,
    StyleProfile,
    VOICE_DIMENSIONS,
)


DIMENSION_AGENTS = {
    "tone": ["architect", "writer", "editor", "moment_writer", "gentle_witness"],
    "vocabulary": ["writer", "editor", "sensory", "moment_writer"],
    "sentence_structure": ["editor", "reader", "breath_editor"],
    "rhythm": ["writer", "moment_writer", "breath_editor"],
    "formatting": ["editor", "breath_editor", "reflection"],
    "humor": ["writer", "coach", "moment_writer"],
    "sensory_density": ["sensory", "moment_writer"],
    "emoji": ["writer", "coach", "gentle_witness"],
    "metaphor_density": ["architect", "writer", "cosmic_signal"],
    "emotional_depth": ["reflection", "inner_weather", "gentle_witness"],
    "pacing": ["reader", "breath_editor"],
    "perspective": ["architect", "future", "cosmic_signal"],
}

AGENT_FILENAME_MAP = {
    "deep": {
        "architect": "story_architect.yaml",
        "writer": "writing_agent.yaml",
        "reader": "reader_experience.yaml",
        "editor": "editor_agent.yaml",
        "coach": "coach_agent.yaml",
        "future": "future_self.yaml",
        "reflection": "reflection_engine.yaml",
        "sensory": "sensory_capture.yaml",
        "inner_weather": "inner_weather.yaml",
        "cosmic_signal": "cosmic_signal_reader.yaml",
        "moment_writer": "moment_writer.yaml",
        "breath_editor": "breath_editor.yaml",
        "gentle_witness": "gentle_witness.yaml",
    },
    "moment": {
        "sensory": "sensory_capture.yaml",
        "inner_weather": "inner_weather.yaml",
        "cosmic_signal": "cosmic_signal_reader.yaml",
        "moment_writer": "moment_writer.yaml",
        "breath_editor": "breath_editor.yaml",
        "gentle_witness": "gentle_witness.yaml",
        "architect": "story_architect.yaml",
        "writer": "writing_agent.yaml",
        "reader": "reader_experience.yaml",
        "editor": "editor_agent.yaml",
        "coach": "coach_agent.yaml",
        "future": "future_self.yaml",
        "reflection": "reflection_engine.yaml",
    },
}

REQUIRED_AGENTS = {
    "deep": [
        "architect",
        "reflection",
        "writer",
        "reader",
        "editor",
        "coach",
        "future",
    ],
    "moment": [
        "sensory",
        "inner_weather",
        "cosmic_signal",
        "moment_writer",
        "breath_editor",
        "gentle_witness",
    ],
}

SKILL_LEVEL_INVARIANTS = (
    "name",
    "mode",
    "purpose",
    "identity",
    "input",
    "output",
    "workflow",
    "tasks",
    "handoff_contract",
    "context_policy",
)


def get_affected_agents(changed_dimensions: List[str], mode: str = "deep") -> List[str]:
    required = REQUIRED_AGENTS.get(mode, [])
    affected = {
        agent
        for dimension in changed_dimensions
        for agent in DIMENSION_AGENTS.get(dimension, [])
    }
    return [agent for agent in required if agent in affected]


def _load_base_skill(mode: str, base_style_slug: str, filename: str) -> dict:
    candidate = resolve_path(f"skills/{mode}/{base_style_slug}/{filename}")
    if not candidate.exists() and mode == "deep":
        legacy = resolve_path(f"skills/{base_style_slug}/{filename}")
        if legacy.exists():
            candidate = legacy
    if not candidate.exists():
        raise FileNotFoundError(
            f"Base skill không tồn tại: mode={mode}, "
            f"style={base_style_slug}, file={filename}"
        )
    return load_yaml(candidate)


def stable_skill_hash(data: Dict[str, Any]) -> str:
    encoded = json.dumps(
        data, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_base_snapshot(
    artifact: CanonicalIR,
    *,
    mode: str,
    base_style_slug: str,
) -> None:
    if artifact.base_style_slug != base_style_slug:
        raise ValueError(
            f"{artifact.filename}: base style trong Canonical IR không khớp profile."
        )
    current_base = _load_base_skill(mode, base_style_slug, artifact.filename)
    if stable_skill_hash(current_base) != artifact.base_hash:
        raise ValueError(
            f"{artifact.filename}: base style đã thay đổi sau khi compile; "
            "cần compile lại trước khi publish."
        )


def _rules_for_dimension(
    dimension: str,
    profile: DimensionProfile,
) -> List[str]:
    if not profile.description.strip():
        return []
    duplicated = {
        item.strip().casefold() for item in profile.do if item.strip()
    } & {item.strip().casefold() for item in profile.avoid if item.strip()}
    if duplicated:
        raise ValueError(
            f"Dimension '{dimension}' có rule đồng thời trong do và avoid: "
            + ", ".join(sorted(duplicated))
        )
    rules = [
        f"Mô tả: {profile.description}",
        f"Cường độ mục tiêu: {profile.strength:.2f}",
    ]
    rules.extend(f"Nên: {item}" for item in profile.do if item.strip())
    rules.extend(f"Tránh: {item}" for item in profile.avoid if item.strip())
    rules.extend(
        f"Ví dụ tham chiếu: {item}" for item in profile.examples[:2] if item.strip()
    )
    return rules


def _invariant_snapshot(
    base: Dict[str, Any],
    *,
    filename: str,
    workflow_order: int,
    agent_id: str,
) -> Dict[str, Any]:
    snapshot = {
        key: copy.deepcopy(base[key])
        for key in SKILL_LEVEL_INVARIANTS
        if key in base
    }
    snapshot.update(
        {
            "agent_id": agent_id,
            "filename": filename,
            "workflow_order": workflow_order,
        }
    )
    return snapshot


def _contract_object(value: Any) -> Optional[Dict[str, Any]]:
    """Normalize legacy scalar contracts into a JSON-safe object contract."""
    if value is None:
        return None
    if isinstance(value, dict):
        return copy.deepcopy(value)
    return {"reference": copy.deepcopy(value)}


def compile_style(
    profile: StyleProfile,
    mode: str,
    changed_dimensions: Optional[List[str]] = None,
) -> CompileResult:
    """Compile deterministic full-template overlays from an explicit base style."""
    if mode not in REQUIRED_AGENTS:
        raise ValueError(f"Mode không hợp lệ: {mode}")
    if profile.mode != mode:
        raise ValueError(
            f"Profile mode '{profile.mode}' không khớp compile mode '{mode}'."
        )
    filename_map = AGENT_FILENAME_MAP[mode]
    required = REQUIRED_AGENTS[mode]
    warnings: List[str] = []
    if changed_dimensions is None:
        agents_to_compile = required
    else:
        unknown = sorted(set(changed_dimensions) - set(VOICE_DIMENSIONS))
        if unknown:
            warnings.append("Dimension không được map: " + ", ".join(unknown))
        agents_to_compile = get_affected_agents(changed_dimensions, mode)

    artifacts: Dict[str, CanonicalIR] = {}
    for agent_slug in agents_to_compile:
        filename = filename_map[agent_slug]
        base = _load_base_skill(mode, profile.base_style_slug, filename)
        workflow_order = required.index(agent_slug) + 1
        agent_id = str(base.get("name") or agent_slug)
        overlays: Dict[str, List[str]] = {}
        if profile.dna:
            for dimension in VOICE_DIMENSIONS:
                if agent_slug not in DIMENSION_AGENTS[dimension]:
                    continue
                rules = _rules_for_dimension(
                    dimension, getattr(profile.dna, dimension)
                )
                if rules:
                    overlays[dimension] = rules

        effective = copy.deepcopy(base)
        if overlays:
            effective["voice_lab_style"] = {
                "schema_version": 2,
                "profile_revision": profile.revision,
                "dimensions": overlays,
            }
        else:
            effective.pop("voice_lab_style", None)
        invariants = _invariant_snapshot(
            base,
            filename=filename,
            workflow_order=workflow_order,
            agent_id=agent_id,
        )
        for key, expected in invariants.items():
            if key in effective and key in base and effective[key] != expected:
                raise ValueError(f"Compiler đã thay đổi invariant '{key}'.")

        artifacts[filename] = CanonicalIR(
            id=f"{mode}:{profile.base_style_slug}:{agent_slug}",
            agent_id=agent_id,
            filename=filename,
            workflow_order=workflow_order,
            output_contract=_contract_object(
                base.get("output_contract", base.get("output"))
            ),
            handoff_contract=_contract_object(
                base.get(
                    "handoff_contract",
                    base.get("output", {}).get("handoff")
                    if isinstance(base.get("output"), dict)
                    else None,
                )
            ),
            context_policy=_contract_object(base.get("context_policy")),
            base_style_slug=profile.base_style_slug,
            base_hash=stable_skill_hash(base),
            invariants=invariants,
            style_overlays=overlays,
            effective_skill=effective,
        )
    return CompileResult(artifacts=artifacts, warnings=warnings)
