from __future__ import annotations

import datetime as dt
import uuid
from typing import Any, Dict, Iterator, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


SCHEMA_VERSION = 2
VOICE_DIMENSIONS = (
    "tone",
    "vocabulary",
    "sentence_structure",
    "rhythm",
    "formatting",
    "humor",
    "sensory_density",
    "emoji",
    "metaphor_density",
    "emotional_depth",
    "pacing",
    "perspective",
)


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class DimensionProfile(BaseModel):
    description: str = ""
    strength: float = Field(default=0.5, ge=0.0, le=1.0)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    do: List[str] = Field(default_factory=list)
    avoid: List[str] = Field(default_factory=list)
    examples: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)
    source: Literal["analysis", "interview", "calibration", "legacy"] = "analysis"


class VoiceDNA(BaseModel):
    tone: DimensionProfile = Field(default_factory=DimensionProfile)
    vocabulary: DimensionProfile = Field(default_factory=DimensionProfile)
    sentence_structure: DimensionProfile = Field(default_factory=DimensionProfile)
    rhythm: DimensionProfile = Field(default_factory=DimensionProfile)
    formatting: DimensionProfile = Field(default_factory=DimensionProfile)
    humor: DimensionProfile = Field(default_factory=DimensionProfile)
    sensory_density: DimensionProfile = Field(default_factory=DimensionProfile)
    emoji: DimensionProfile = Field(default_factory=DimensionProfile)
    metaphor_density: DimensionProfile = Field(default_factory=DimensionProfile)
    emotional_depth: DimensionProfile = Field(default_factory=DimensionProfile)
    pacing: DimensionProfile = Field(default_factory=DimensionProfile)
    perspective: DimensionProfile = Field(default_factory=DimensionProfile)

    @field_validator(*VOICE_DIMENSIONS, mode="before")
    @classmethod
    def migrate_flat_dimension(cls, value: Any) -> Any:
        if isinstance(value, str):
            return {
                "description": value,
                "confidence": 0.0,
                "source": "legacy",
            }
        return value

    def non_empty_dimensions(self) -> Dict[str, DimensionProfile]:
        return {
            name: getattr(self, name)
            for name in VOICE_DIMENSIONS
            if getattr(self, name).description.strip()
        }


class EvidenceClaim(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sample_id: str = ""
    dimension: str
    claim: str
    exact_quote: str = ""
    quote_start: Optional[int] = None
    quote_end: Optional[int] = None
    stance: Literal["support", "contradict"] = "support"
    status: Literal["active", "rejected"] = "active"
    rejection_reason: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def migrate_v1_claim(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        data = dict(value)
        if "exact_quote" not in data and "quote" in data:
            data["exact_quote"] = data.pop("quote")
        evidence_ids = data.pop("evidence_ids", [])
        if not data.get("sample_id") and evidence_ids:
            data["sample_id"] = str(evidence_ids[0])
        data.pop("confidence", None)
        return data

    @property
    def quote(self) -> str:
        """Compatibility alias for the v1 UI."""
        return self.exact_quote


class InterviewQuestion(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    dimension: str
    question: str
    context: str


class InterviewRecord(BaseModel):
    question_id: str
    dimension: str
    answer: str
    before: Optional[DimensionProfile] = None
    after: DimensionProfile
    confirmed_at: dt.datetime = Field(default_factory=utc_now)


class CalibrationRecord(BaseModel):
    session_id: str
    dimension: str
    selected_label: Literal["A", "B"]
    selected_direction: Literal["amplified", "restrained"]
    selected_text: str
    before_strength: float
    after_strength: float
    confirmed_at: dt.datetime = Field(default_factory=utc_now)


class CalibrationSession(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    dimension: str
    content_brief: str
    variant_a: str
    variant_b: str
    shuffle_mapping: Dict[Literal["A", "B"], Literal["amplified", "restrained"]]
    selected: Optional[Literal["A", "B"]] = None
    created_at: dt.datetime = Field(default_factory=utc_now)

    def __iter__(self) -> Iterator[str]:
        """Allow legacy `variant_a, variant_b = calibrate_ab(...)` callers."""
        yield self.variant_a
        yield self.variant_b


class StyleProfile(BaseModel):
    schema_version: Literal[2] = SCHEMA_VERSION
    revision: int = Field(default=1, ge=1)
    slug: str
    mode: str
    status: Literal["draft", "confirmed"] = "draft"
    provenance: str = "user_generated"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    dna: Optional[VoiceDNA] = None
    evidence: List[EvidenceClaim] = Field(default_factory=list)
    rejected_evidence: List[EvidenceClaim] = Field(default_factory=list)
    analysis_status: Literal[
        "complete", "partial", "failed", "incomplete_legacy_data"
    ] = "partial"
    analysis_warnings: List[str] = Field(default_factory=list)
    interview_history: List[InterviewRecord] = Field(default_factory=list)
    calibration_history: List[CalibrationRecord] = Field(default_factory=list)
    base_style_slug: str = "reflective"
    is_draft: bool = True
    created_at: dt.datetime = Field(default_factory=utc_now)
    updated_at: dt.datetime = Field(default_factory=utc_now)

    @model_validator(mode="before")
    @classmethod
    def migrate_v1_profile(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        data = dict(value)
        version = data.get("schema_version", 1)
        if str(version) in {"1", "1.0"}:
            data["schema_version"] = 2
            data["revision"] = int(data.pop("profile_version", 1))
            data.setdefault("analysis_status", "partial")
            data.setdefault("analysis_warnings", ["Profile v1 đã được chuyển sang schema v2."])
            data.setdefault("is_draft", True)
        return data

    @model_validator(mode="after")
    def enforce_publish_state(self) -> "StyleProfile":
        if self.analysis_status != "complete":
            self.is_draft = True
            if self.status == "confirmed":
                self.status = "draft"
        return self


def compute_profile_confidence(profile: StyleProfile) -> float:
    """Compute profile confidence consistently from non-empty dimensions."""
    if not profile.dna:
        return 0.0
    dimensions = list(profile.dna.non_empty_dimensions().values())
    if not dimensions:
        return 0.0
    return round(
        sum(dimension.confidence for dimension in dimensions) / len(dimensions),
        4,
    )


class AnalysisResult(BaseModel):
    profile: StyleProfile
    rejected_evidence: List[EvidenceClaim] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    routing_mode: Literal["single_pass", "multi_pass"]
    usage: Dict[str, int] = Field(default_factory=dict)

    def __iter__(self) -> Iterator[Any]:
        """Allow legacy `dna, claims = analyze_samples(...)` callers."""
        yield self.profile.dna
        yield self.profile.evidence


class AnalysisError(RuntimeError):
    def __init__(
        self,
        code: Literal[
            "gemini_unavailable",
            "invalid_model_output",
            "insufficient_valid_evidence",
            "input_too_large",
        ],
        user_message: str,
        *,
        retryable: bool = False,
        detail: str = "",
    ) -> None:
        super().__init__(user_message)
        self.code = code
        self.user_message = user_message
        self.retryable = retryable
        self.detail = detail


class CanonicalIR(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    schema_version: Literal[2] = SCHEMA_VERSION
    agent_id: str
    filename: str
    workflow_order: int
    output_contract: Optional[Dict[str, Any]] = None
    handoff_contract: Optional[Dict[str, Any]] = None
    context_policy: Optional[Dict[str, Any]] = None
    base_style_slug: str
    base_hash: str
    invariants: Dict[str, Any]
    style_overlays: Dict[str, List[str]]
    effective_skill: Dict[str, Any]


class CompileResult(BaseModel):
    artifacts: Dict[str, CanonicalIR]
    warnings: List[str] = Field(default_factory=list)

    def __getitem__(self, key: str) -> Dict[str, Any]:
        return self.artifacts[key].model_dump()

    def __iter__(self) -> Iterator[str]:
        return iter(self.artifacts)

    def __len__(self) -> int:
        return len(self.artifacts)

    def keys(self):
        return self.artifacts.keys()

    def values(self):
        return (artifact.model_dump() for artifact in self.artifacts.values())

    def items(self):
        return (
            (filename, artifact.model_dump())
            for filename, artifact in self.artifacts.items()
        )


class MergeConflict(BaseModel):
    key: str
    base_value: Any = None
    current_value: Any = None
    override_value: Any = None
    reason: str


class MergeResult(BaseModel):
    merged_ir: Dict[str, Any]
    conflicts: List[MergeConflict] = Field(default_factory=list)

    @property
    def is_resolved(self) -> bool:
        return not self.conflicts


class PublishResult(BaseModel):
    runtime_dir: str
    backup_path: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)
