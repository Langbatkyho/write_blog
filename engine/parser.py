import re
from typing import Any


class StageResponseError(ValueError):
    pass


_CONTRACT_SECTION_RE = re.compile(
    r"(?im)^##[ \t]+(Artifact|Handoff)[ \t]*$"
)


def _parse_strict_stage_response(response_text: str) -> tuple[str, str]:
    sections = list(_CONTRACT_SECTION_RE.finditer(response_text))
    names = [match.group(1).strip().casefold() for match in sections]
    if names != ["artifact", "handoff"]:
        raise StageResponseError(
            "Stage response strict phải có đúng hai section contract theo thứ tự: "
            "## Artifact, ## Handoff."
        )
    if response_text[: sections[0].start()].strip():
        raise StageResponseError(
            "Stage response strict không được có nội dung trước ## Artifact."
        )
    artifact = response_text[
        sections[0].end() : sections[1].start()
    ].strip()
    handoff = response_text[sections[1].end() :].strip()
    if not artifact or not handoff:
        raise StageResponseError("Stage response có Artifact/Handoff rỗng.")
    return artifact, handoff


def count_words(text: str) -> int:
    return len(re.findall(r"\w+", text, flags=re.UNICODE))

def count_paragraphs(text: str) -> int:
    return len([part for part in re.split(r"\n\s*\n", text.strip()) if part.strip()])

def average_sentence_words(text: str) -> float:
    sentences = [part for part in re.split(r"[.!?。！？]+", text) if part.strip()]
    if not sentences:
        return 0.0
    return count_words(text) / len(sentences)

def estimate_tokens(text: str) -> int:
    # Rough cross-language estimate. Good enough for comparing artifact vs handoff size.
    return max(1, int(count_words(text) * 1.35)) if text.strip() else 0

def truncate_words(text: str, max_words: int = 220) -> str:
    words = re.findall(r"\S+", text)
    if len(words) <= max_words:
        return text.strip()
    return " ".join(words[:max_words]).strip() + "\n\n[Fallback handoff truncated locally.]"

def parse_stage_response(
    response_text: str, *, strict: bool = False
) -> tuple[str, str, bool]:
    if strict:
        artifact, handoff = _parse_strict_stage_response(response_text)
        return artifact, handoff, False

    artifact_match = re.search(
        r"(?ims)^##\s*Artifact\s*$\s*(.*?)(?=^##\s*Handoff\s*$|\Z)",
        response_text,
    )
    handoff_match = re.search(r"(?ims)^##\s*Handoff\s*$\s*(.*)\Z", response_text)

    artifact = artifact_match.group(1).strip() if artifact_match else response_text.strip()
    handoff = handoff_match.group(1).strip() if handoff_match else ""
    used_fallback = False

    if not handoff:
        handoff = truncate_words(artifact)
        used_fallback = True

    return artifact, handoff, used_fallback

def build_context_package(
    step: dict[str, Any],
    artifacts: dict[str, str],
    handoffs: dict[str, str],
) -> dict[str, dict[str, str]]:
    policy = step.get("context_policy", {})
    selected_handoffs = {
        step_id: handoffs[step_id]
        for step_id in policy.get("handoffs", [])
        if step_id in handoffs
    }
    selected_artifacts = {
        step_id: artifacts[step_id]
        for step_id in policy.get("artifacts", [])
        if step_id in artifacts
    }
    return {"handoffs": selected_handoffs, "artifacts": selected_artifacts}

def slugify(text: str, fallback: str = "blog") -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = re.sub(r"[\s_]+", "-", text, flags=re.UNICODE)
    text = text.strip("-")
    return text[:60] or fallback

def extract_title(input_markdown: str) -> str:
    match = re.search(r"(?im)^title:\s*(.+)$", input_markdown)
    if match and match.group(1).strip():
        return match.group(1).strip()
    first_heading = re.search(r"(?m)^#\s+(.+)$", input_markdown)
    return first_heading.group(1).strip() if first_heading else "blog"
