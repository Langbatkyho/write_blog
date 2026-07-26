import os
import yaml
from pathlib import Path
from engine.voice_lab.models import StyleProfile, VoiceDNA

def import_existing_style(mode: str, slug: str) -> StyleProfile:
    """
    Converts an existing style YAML into a draft StyleProfile with:
    - provenance: inferred_from_yaml
    - low confidence
    - no evidence
    - blocking auto-publish (is_draft=True)
    """
    base_dir = Path(__file__).parent.parent.parent
    yaml_dir = base_dir / "skills" / mode / slug
    
    dna = VoiceDNA()
    if yaml_dir.exists() and yaml_dir.is_dir():
        # Iterate to find the first yaml file as a heuristic, or just find style_meta.yaml
        yaml_path = yaml_dir / "style_meta.yaml"
        if not yaml_path.exists():
            yaml_path = list(yaml_dir.glob("*.yaml"))[0] if list(yaml_dir.glob("*.yaml")) else None
            
        if yaml_path:
            try:
                with open(yaml_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    if isinstance(data, dict):
                        # We can attempt some basic inference if we want,
                        # but the main requirement is the metadata.
                        pass
        except Exception as e:
            print(f"Failed to load yaml from {yaml_path}: {e}")

    return StyleProfile(
        slug=slug,
        mode=mode,
        provenance="inferred_from_yaml",
        confidence=0.1,  # Low confidence
        evidence=[],     # No evidence
        dna=dna,
        is_draft=True    # Blocking auto-publish
    )
