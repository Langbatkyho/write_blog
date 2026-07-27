from __future__ import annotations

from engine.voice_lab.models import (
    DimensionProfile,
    InterviewQuestion,
    StyleProfile,
    VOICE_DIMENSIONS,
)


DIMENSION_VI = {
    "tone": "Giọng điệu",
    "vocabulary": "Từ vựng",
    "sentence_structure": "Cấu trúc câu",
    "rhythm": "Nhịp điệu",
    "formatting": "Định dạng",
    "humor": "Sự hài hước",
    "sensory_density": "Mật độ giác quan",
    "emoji": "Biểu tượng cảm xúc",
    "metaphor_density": "Mật độ ẩn dụ",
    "emotional_depth": "Chiều sâu cảm xúc",
    "pacing": "Nhịp độ",
    "perspective": "Góc nhìn / Ngôi kể",
}


def _dimension_priority(profile: StyleProfile, dimension: str) -> tuple:
    value = getattr(profile.dna, dimension) if profile.dna else DimensionProfile()
    contradictions = sum(
        item.dimension == dimension and item.stance == "contradict"
        for item in profile.evidence
    )
    confirmed = any(
        record.dimension == dimension for record in profile.interview_history
    )
    return (
        confirmed,
        bool(value.description.strip()),
        value.confidence,
        -contradictions,
        VOICE_DIMENSIONS.index(dimension),
    )


def generate_interview(
    profile: StyleProfile, *, max_questions: int = 3
) -> list[InterviewQuestion]:
    """Select at most three weak or contradicted dimensions."""
    if not profile.dna:
        return []
    confirmed_dimensions = {
        record.dimension for record in profile.interview_history
    }
    contradicted_dimensions = {
        item.dimension
        for item in profile.evidence
        if item.stance == "contradict" and item.status == "active"
    }
    candidates = [
        dimension
        for dimension in VOICE_DIMENSIONS
        if dimension not in confirmed_dimensions
        or dimension in contradicted_dimensions
    ]
    selected = sorted(
        candidates,
        key=lambda dimension: _dimension_priority(profile, dimension),
    )[: max(0, min(max_questions, 3))]
    questions: list[InterviewQuestion] = []
    for dimension in selected:
        current = getattr(profile.dna, dimension)
        label = DIMENSION_VI[dimension]
        observed = current.description or "chưa có đủ bằng chứng"
        questions.append(
            InterviewQuestion(
                dimension=dimension,
                question=(
                    f"Mẫu hiện đang cho thấy {label.lower()} như thế nào, và bạn "
                    "muốn giữ hay thay đổi đặc điểm đó khi viết?"
                ),
                context=(
                    f"Quan sát hiện tại: “{observed}”. "
                    f"Độ chắc chắn: {current.confidence:.2f}."
                ),
            )
        )
    return questions
