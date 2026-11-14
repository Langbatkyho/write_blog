from __future__ import annotations

import re
import warnings
from pathlib import Path
from typing import Any

from engine.utils import read_text, write_text


def append_run_log(log_file: Path, title: str, body: str) -> None:
    existing = read_text(log_file) if log_file.exists() else ""
    separator = "\n\n" if existing else ""
    write_text(log_file, f"{existing}{separator}# {title}\n\n{body.strip()}\n")


LEGACY_PRIMARY_HEADINGS = ("Edited Blog", "edited_blog", "Edited Draft")
LEGACY_LOG_HEADINGS = ("Edit Log", "edit_log")
MISSING_EDIT_LOG = "Edit log section was not found in the artifact."


def heading_pattern(heading: str) -> str:
    """Regex cho tiêu đề, coi gạch dưới và khoảng trắng là như nhau.

    Ví dụ "edited_moment_blog" khớp cả "Edited Moment Blog".
    """
    words = [word for word in re.split(r"[ _]+", heading.strip()) if word]
    return r"[ _]+".join(re.escape(word) for word in words)


def extract_markdown_section(markdown: str, heading: str) -> str | None:
    pattern = rf"(?ims)^##+\s*{heading_pattern(heading)}\s*$\s*(.*?)(?=^##+\s+|\Z)"
    match = re.search(pattern, markdown)
    return match.group(1).strip() if match else None


def extract_markdown_section_before(
    markdown: str, heading: str, stop_headings: list[str]
) -> str | None:
    start_pattern = rf"(?im)^##+\s*{heading_pattern(heading)}\s*$"
    start_match = re.search(start_pattern, markdown)
    if not start_match:
        return None
    stop_alternatives = "|".join(
        heading_pattern(stop_heading) for stop_heading in stop_headings
    )
    stop_pattern = rf"(?im)^##+\s*(?:{stop_alternatives})\s*$"
    stop_match = re.search(stop_pattern, markdown[start_match.end() :])
    section_end = (
        start_match.end() + stop_match.start()
        if stop_match
        else len(markdown)
    )
    return markdown[start_match.end() : section_end].strip()


def derive_artifact_file_contents(
    skill: dict[str, Any], artifact: str
) -> dict[str, str]:
    output = skill.get("output", {})
    primary_name = output.get("name")
    if not isinstance(primary_name, str):
        primary_name = output.get("artifact")
    if not isinstance(primary_name, str):
        raise ValueError("Skill output thiếu name/artifact.")
    secondary_name = output.get("secondary_name") or output.get(
        "secondary_artifact"
    )
    if not isinstance(secondary_name, str):
        secondary_name = None

    contents = {primary_name: artifact}
    if secondary_name:
        # Tiêu đề hợp lệ: tên cũ của Deep, rồi tên phần mà skill khai báo trong
        # output.sections (Moment: edited_moment_blog, edit_log), rồi tên file
        # (model hay dùng tên file làm tiêu đề, ví dụ "### moment_edited.md").
        sections = output.get("sections")
        section_names = (
            [item for item in sections if isinstance(item, str)]
            if isinstance(sections, list)
            else []
        )
        primary_headings = [*LEGACY_PRIMARY_HEADINGS, *section_names[:1], primary_name]
        log_headings = [*LEGACY_LOG_HEADINGS, *section_names[1:2], secondary_name]
        edited_blog = next(
            (
                found
                for heading in primary_headings
                if (found := extract_markdown_section_before(artifact, heading, log_headings))
            ),
            None,
        ) or artifact
        edit_log = next(
            (
                found
                for heading in log_headings
                if (found := extract_markdown_section(artifact, heading))
            ),
            None,
        ) or MISSING_EDIT_LOG
        if edited_blog == artifact:
            warnings.warn(
                "Could not split artifact into primary/secondary files. "
                f"Falling back to full artifact for {primary_name}.",
                UserWarning,
                stacklevel=2,
            )
        contents[primary_name] = edited_blog
        contents[secondary_name] = edit_log
    return contents
