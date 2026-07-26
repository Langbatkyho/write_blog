from typing import Dict, List, Optional
from pathlib import Path
from engine.voice_lab.models import StyleProfile, CanonicalIR
from engine.utils import load_yaml, resolve_path

# Adjacency Matrix mapping dimensions to affected agents (internal slugs)
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
    "perspective": ["architect", "future", "cosmic_signal"]
}

# Maps internal agent slug -> actual filename on disk, per mode
# Must match what the workflow YAML files reference as skill filenames
AGENT_FILENAME_MAP = {
    "deep": {
        "architect":    "story_architect.yaml",
        "writer":       "writing_agent.yaml",
        "reader":       "reader_experience.yaml",
        "editor":       "editor_agent.yaml",
        "coach":        "coach_agent.yaml",
        "future":       "future_self.yaml",
        "reflection":   "reflection_engine.yaml",
        # Not used in deep mode workflow — included for completeness
        "sensory":       "sensory_capture.yaml",
        "inner_weather": "inner_weather.yaml",
        "cosmic_signal": "cosmic_signal_reader.yaml",
        "moment_writer": "moment_writer.yaml",
        "breath_editor": "breath_editor.yaml",
        "gentle_witness":"gentle_witness.yaml",
    },
    "moment": {
        "sensory":       "sensory_capture.yaml",
        "inner_weather": "inner_weather.yaml",
        "cosmic_signal": "cosmic_signal_reader.yaml",
        "moment_writer": "moment_writer.yaml",
        "breath_editor": "breath_editor.yaml",
        "gentle_witness":"gentle_witness.yaml",
        # Not used in moment mode workflow — included for completeness
        "architect":    "story_architect.yaml",
        "writer":       "writing_agent.yaml",
        "reader":       "reader_experience.yaml",
        "editor":       "editor_agent.yaml",
        "coach":        "coach_agent.yaml",
        "future":       "future_self.yaml",
        "reflection":   "reflection_engine.yaml",
    }
}

# Required agents per mode (must align with workflow step order)
REQUIRED_AGENTS = {
    "deep":   ["architect", "reflection", "writer", "reader", "editor", "coach", "future"],
    "moment": ["sensory", "inner_weather", "cosmic_signal", "moment_writer", "breath_editor", "gentle_witness"],
}

def get_affected_agents(changed_dimensions: List[str]) -> List[str]:
    """Determine which agents need recompilation based on changed dimensions."""
    affected = set()
    for dim in changed_dimensions:
        agents = DIMENSION_AGENTS.get(dim, [])
        affected.update(agents)
    return list(affected)

def _load_base_skill(mode: str, filename: str) -> dict:
    """Try to load an existing skill file as base template."""
    for style_dir in resolve_path(f"skills/{mode}").iterdir() if resolve_path(f"skills/{mode}").exists() else []:
        candidate = style_dir / filename
        if candidate.exists():
            try:
                return load_yaml(candidate)
            except Exception:
                pass
    return {}

def compile_style(profile: StyleProfile, mode: str, changed_dimensions: Optional[List[str]] = None) -> Dict[str, dict]:
    """
    Compile the StyleProfile into agent configurations.
    Returns a dict mapping agent filename (e.g. 'story_architect.yaml') to IR dict.
    Supports incremental compilation if changed_dimensions is provided.
    """
    filename_map = AGENT_FILENAME_MAP.get(mode, AGENT_FILENAME_MAP["deep"])
    required = REQUIRED_AGENTS.get(mode, REQUIRED_AGENTS["deep"])

    if changed_dimensions is not None:
        agents_to_compile = [a for a in get_affected_agents(changed_dimensions) if a in required]
    else:
        agents_to_compile = required

    compiled_results = {}

    for agent_slug in agents_to_compile:
        filename = filename_map.get(agent_slug, f"{agent_slug}.yaml")

        rules = []
        if profile.dna:
            dna_dict = profile.dna.model_dump()
            for dim in DIMENSION_AGENTS.keys():
                if agent_slug in DIMENSION_AGENTS.get(dim, []):
                    val = dna_dict.get(dim)
                    if val:
                        rules.append(f"{dim.capitalize().replace('_', ' ')}: {val}")

        # Load base template from existing style if available for reference
        base = _load_base_skill(mode, filename)

        ir = CanonicalIR(
            id=f"{mode}_{agent_slug}_ir",
            agent_id=f"{mode}_{agent_slug}",
            filename=filename,
            output_contract=base.get("output_contract", "standard_output_contract"),
            handoff_contract=base.get("handoff_contract", "standard_handoff_contract"),
            workflow_order=required.index(agent_slug) + 1 if agent_slug in required else 100,
            context_policy=base.get("context_policy", "strict_context"),
            prompt=base.get("prompt", f"You are the {agent_slug} agent. Follow the style rules carefully."),
            style_rules=rules
        )
        compiled_results[filename] = ir.model_dump()

    return compiled_results

