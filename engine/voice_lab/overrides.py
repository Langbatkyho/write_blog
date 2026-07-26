from typing import Dict, Any

def resolve_conflict_with_llm(base_val: Any, current_val: Any, override_val: Any, key: str) -> Any:
    """
    Fallback for when a 3-way diff encounters a conflict that cannot be trivially merged.
    """
    # In a real system, this would prompt an LLM to merge base_val, current_val and override_val.
    if isinstance(current_val, str) and isinstance(override_val, str):
        return f"{override_val}\n# Note: LLM resolved conflict between current and override."
    return override_val

def merge_overrides(base_ir: Dict[str, Any], current_ir: Dict[str, Any], overrides_ir: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge user overrides into the current Canonical IR using a Three-way diff approach based on ID.
    Enforces the Invariant Contract by protecting core agent properties.
    """
    if base_ir.get("id") != current_ir.get("id") or current_ir.get("id") != overrides_ir.get("id"):
        raise ValueError("Cannot merge IRs with mismatched IDs")

    invariant_fields = {
        "agent_id", "filename", "output_contract", "handoff_contract", "workflow_order", "context_policy", "id"
    }
    
    merged = dict(current_ir)
    
    # All keys across the three dicts
    all_keys = set(base_ir.keys()) | set(current_ir.keys()) | set(overrides_ir.keys())
    
    for key in all_keys:
        if key in invariant_fields:
            continue
            
        b = base_ir.get(key)
        c = current_ir.get(key)
        o = overrides_ir.get(key)
        
        # 3-way diff logic
        if c == o:
            continue # no conflict, already matches
        elif b == c and b != o:
            # Only overrides changed it
            merged[key] = o
        elif b == o and b != c:
            # Only current changed it, keep current
            merged[key] = c
        else:
            # Both changed it differently (Conflict)
            if isinstance(c, list) and isinstance(o, list):
                # Simple list merge: deduplicate while preserving order
                new_list = list(c)
                for item in o:
                    if item not in new_list:
                        new_list.append(item)
                merged[key] = new_list
            else:
                merged[key] = resolve_conflict_with_llm(b, c, o, key)
            
    return merged
