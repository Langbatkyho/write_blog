import pytest
from engine.voice_lab.models import StyleProfile, VoiceDNA
from engine.voice_lab.compiler import DIMENSION_AGENTS, compile_style

def test_adjacency_matrix_coverage():
    """
    Contract Test: Ensure the Adjacency Matrix (DIMENSION_AGENTS) mapped in compiler.py
    covers 100% of dimensions and agents.
    """
    # 1. Check Dimensions coverage against VoiceDNA fields
    dna_fields = set(VoiceDNA.model_fields.keys())
    matrix_dimensions = set(DIMENSION_AGENTS.keys())
    
    assert matrix_dimensions == dna_fields, f"Missing or extra dimensions in matrix: {matrix_dimensions ^ dna_fields}"

    # 2. Check Agents coverage (we expect the 13 core agents to be mapped)
    expected_agents = {
        "architect", "writer", "reader", "editor", "coach", "future", "reflection",
        "sensory", "inner_weather", "cosmic_signal", "moment_writer", "breath_editor", "gentle_witness"
    }
    matrix_agents = set()
    for agents in DIMENSION_AGENTS.values():
        matrix_agents.update(agents)
        
    assert matrix_agents == expected_agents, f"Missing or extra agents in matrix: {matrix_agents ^ expected_agents}"


def verify_smoke_test_invariants_and_coverage(profile: StyleProfile, baseline_yaml: dict, generated_yaml: dict):
    """
    Zero-cost Smoke Test utility that:
    - Takes a StyleProfile, and baseline/generated Effective YAML (as dicts).
    - Asserts keyword/synonym coverage of the dimensions inside the prompt/rules using simple text search (no LLM).
    - Validates Invariant diffs (Agent ID, workflow_order, context_policy must remain unchanged from baseline).
    """
    # 1. Validate Invariants (must remain unchanged from baseline)
    invariants = [
        "agent_id",
        "filename",
        "output_contract",
        "handoff_contract",
        "workflow_order",
        "context_policy"
    ]
    
    for field in invariants:
        assert field in baseline_yaml, f"Baseline is missing invariant field: {field}"
        assert field in generated_yaml, f"Generated YAML is missing invariant field: {field}"
        assert baseline_yaml[field] == generated_yaml[field], \
            f"Invariant violation for '{field}': changed from '{baseline_yaml[field]}' to '{generated_yaml[field]}'"
            
    # 2. Assert keyword coverage of dimensions
    # Combine prompt and rules into a single lowercased corpus for text search
    prompt = generated_yaml.get("prompt", "")
    rules = " ".join(generated_yaml.get("style_rules", []))
    corpus = f"{prompt} {rules}".lower()
    
    if profile.dna:
        agent_slug = generated_yaml.get("filename", "").replace(".yaml", "")
        dna_dict = profile.dna.model_dump()
        
        for dim, mapped_agents in DIMENSION_AGENTS.items():
            if agent_slug in mapped_agents:
                expected_value = dna_dict.get(dim)
                if expected_value:
                    # Simple text search to assert coverage (no LLM)
                    # We expect the keyword/value from the profile to be present in the generated rules
                    assert expected_value.lower() in corpus, \
                        f"Coverage violation: Dimension '{dim}' value '{expected_value}' not found in {agent_slug} YAML."


def test_smoke_test_utility_valid():
    """Test that the utility passes when given valid compiler output."""
    dna = VoiceDNA(
        tone="authoritative and calm",
        vocabulary="precise",
        sentence_structure="varied",
        rhythm="steady",
        formatting="markdown lists"
    )
    profile = StyleProfile(
        slug="test-style",
        mode="deep",
        dna=dna
    )
    
    # We can actually compile this to get a realistic baseline and generated YAML
    compiled_baselines = compile_style(StyleProfile(slug="test-style", mode="deep"), mode="deep")
    compiled_generated = compile_style(profile, mode="deep")
    
    writer_baseline = compiled_baselines["writing_agent.yaml"]
    writer_generated = compiled_generated["writing_agent.yaml"]
    
    # This should pass without raising any AssertionError
    verify_smoke_test_invariants_and_coverage(profile, writer_baseline, writer_generated)

def test_smoke_test_utility_invariant_violation():
    """Test that the utility catches invariant violations."""
    profile = StyleProfile(slug="test", mode="test")
    baseline = {
        "agent_id": "test_writer",
        "filename": "writer.yaml",
        "output_contract": "standard",
        "handoff_contract": "standard",
        "workflow_order": 1,
        "context_policy": "strict",
        "prompt": "",
        "style_rules": []
    }
    
    # Change workflow_order intentionally
    generated = baseline.copy()
    generated["workflow_order"] = 2
    
    with pytest.raises(AssertionError, match="Invariant violation for 'workflow_order'"):
        verify_smoke_test_invariants_and_coverage(profile, baseline, generated)

def test_smoke_test_utility_coverage_violation():
    """Test that the utility catches missing keywords in generated YAML."""
    dna = VoiceDNA(tone="extremely funny")
    profile = StyleProfile(slug="test", mode="test", dna=dna)
    baseline = {
        "agent_id": "test_writer",
        "filename": "writer.yaml",
        "output_contract": "standard",
        "handoff_contract": "standard",
        "workflow_order": 1,
        "context_policy": "strict",
        "prompt": "You are the writer.",
        "style_rules": []
    }
    
    # Generated YAML omits the tone entirely
    generated = baseline.copy()
    generated["style_rules"] = ["Vocabulary: basic"]
    
    with pytest.raises(AssertionError, match="Coverage violation"):
        verify_smoke_test_invariants_and_coverage(profile, baseline, generated)
