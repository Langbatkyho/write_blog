from pydantic import BaseModel, Field
from typing import List, Optional
import re

class InterviewQuestion(BaseModel):
    id: str
    dimension: str
    question: str
    context: str

class EvidenceClaim(BaseModel):
    dimension: str = Field(description="The dimension of style (e.g., tone, vocabulary)")
    claim: str = Field(description="The claim about this dimension")
    quote: str = Field(description="Exact quote from the sample supporting the claim")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence level of the claim")
    evidence_ids: List[str] = Field(default_factory=list, description="IDs of samples or sources")
    status: str = Field(default="active", description="Active or rejected claim")

class VoiceDNA(BaseModel):
    tone: str = ""
    vocabulary: str = ""
    sentence_structure: str = ""
    rhythm: str = ""
    formatting: str = ""
    humor: str = ""
    sensory_density: str = ""
    emoji: str = ""
    metaphor_density: str = ""
    emotional_depth: str = ""
    pacing: str = ""
    perspective: str = ""

class StyleProfile(BaseModel):
    slug: str
    mode: str
    profile_version: int = Field(default=1, description="Version of the profile")
    status: str = Field(default="draft", description="draft or confirmed")
    provenance: str = Field(default="user_generated", description="Can be user_generated or inferred_from_yaml")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    dna: Optional[VoiceDNA] = None
    evidence: List[EvidenceClaim] = Field(default_factory=list)
    is_draft: bool = Field(default=True, description="Draft profiles cannot be auto-published")
    
class CanonicalIR(BaseModel):
    """
    Canonical Internal Representation of a compiled Agent Style.
    """
    id: str = Field(description="Stable ID for three-way diff")
    agent_id: str
    filename: str
    output_contract: str
    handoff_contract: str
    workflow_order: int
    context_policy: str
    prompt: str
    style_rules: List[str]

def sanitize_sample(sample: str) -> str:
    """
    Sanitize untrusted user sample text to prevent prompt injection.
    """
    if not sample:
        return ""
    # Remove XML/HTML tags
    sanitized = re.sub(r'<[^>]+>', '', sample)
    
    # Escape structural keywords that might confuse LLM
    sanitized = sanitized.replace('System:', '[System]')
    sanitized = sanitized.replace('Human:', '[Human]')
    sanitized = sanitized.replace('Assistant:', '[Assistant]')
    
    # Optional: Html escape if we want to be overly safe
    # sanitized = html.escape(sanitized)
    
    # Truncate to reasonable length per sample to avoid context overflow/injection
    return sanitized.strip()[:10000]
