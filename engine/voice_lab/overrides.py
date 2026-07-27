from __future__ import annotations

from typing import Any, Dict

from engine.voice_lab.models import CanonicalIR, MergeConflict, MergeResult


IR_LEVEL_INVARIANTS = {
    "id",
    "schema_version",
    "agent_id",
    "filename",
    "workflow_order",
    "base_style_slug",
    "base_hash",
    "invariants",
}


def merge_overrides(
    base_ir: Dict[str, Any],
    current_ir: Dict[str, Any],
    overrides_ir: Dict[str, Any],
) -> MergeResult:
    """Deterministic three-way merge; ambiguous changes remain explicit."""
    ids = {base_ir.get("id"), current_ir.get("id"), overrides_ir.get("id")}
    if len(ids) != 1 or None in ids:
        raise ValueError("Cannot merge IRs with mismatched IDs")

    merged = dict(current_ir)
    conflicts = []
    keys = set(base_ir) | set(current_ir) | set(overrides_ir)
    for key in sorted(keys):
        base = base_ir.get(key)
        current = current_ir.get(key)
        override = overrides_ir.get(key)
        if key in IR_LEVEL_INVARIANTS:
            if override != base or current != base:
                conflicts.append(
                    MergeConflict(
                        key=key,
                        base_value=base,
                        current_value=current,
                        override_value=override,
                        reason="invariant_modified",
                    )
                )
            continue
        if current == override:
            continue
        if current == base and override != base:
            merged[key] = override
        elif override == base and current != base:
            merged[key] = current
        else:
            conflicts.append(
                MergeConflict(
                    key=key,
                    base_value=base,
                    current_value=current,
                    override_value=override,
                    reason="both_sides_changed",
                )
            )
    return MergeResult(merged_ir=merged, conflicts=conflicts)


def apply_conflict_resolutions(
    result: MergeResult,
    resolutions: Dict[str, Any],
) -> Dict[str, Any]:
    """Apply explicit user choices and revalidate Canonical IR + invariants."""
    unresolved = {item.key: item for item in result.conflicts}
    invariant_conflicts = [
        item.key
        for item in result.conflicts
        if item.reason == "invariant_modified"
    ]
    if invariant_conflicts:
        raise ValueError(
            "Không thể resolve thay đổi invariant: "
            + ", ".join(sorted(invariant_conflicts))
        )
    missing = sorted(set(unresolved) - set(resolutions))
    unknown = sorted(set(resolutions) - set(unresolved))
    if missing:
        raise ValueError("Thiếu lựa chọn cho conflict: " + ", ".join(missing))
    if unknown:
        raise ValueError("Resolution không khớp conflict: " + ", ".join(unknown))

    merged = dict(result.merged_ir)
    merged.update(resolutions)
    artifact = CanonicalIR.model_validate(merged)
    for key, expected in artifact.invariants.items():
        if key in artifact.effective_skill and artifact.effective_skill[key] != expected:
            raise ValueError(f"Resolution làm thay đổi invariant '{key}'.")
    return artifact.model_dump()
