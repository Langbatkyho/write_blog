"""Deterministic length check for the Moment article, using the flow's default."""

from __future__ import annotations

import re

from engine.parser import count_words


def requested_word_range(author_input: str, flow: dict) -> tuple[int | None, int | None]:
    match = re.search(r"(?im)^[ \t]*desired_length[ \t]*:[ \t]*(.*)$", author_input)
    value = match.group(1).strip() if match else ""
    if match and not value:
        following = author_input[match.end():].splitlines()
        value = next((line.strip() for line in following if line.strip()), "")
    if not value:
        value = str(flow["input"]["desired_length"]["default"])

    range_match = re.search(r"(?<!\d)(\d+)[ \t]*[-–—][ \t]*(\d+)(?!\d)", value)
    if range_match:
        minimum, maximum = map(int, range_match.groups())
        if 0 < minimum <= maximum:
            return minimum, maximum
    under_match = re.search(r"(?:dưới|under|less than)[ \t]+(\d+)", value, re.IGNORECASE)
    if under_match:
        return None, int(under_match.group(1)) - 1
    maximum_match = re.search(r"(?:tối đa|không quá|at most|up to)[ \t]+(\d+)", value, re.IGNORECASE)
    if maximum_match:
        return None, int(maximum_match.group(1))
    minimum_match = re.search(r"(?:tối thiểu|ít nhất|at least)[ \t]+(\d+)", value, re.IGNORECASE)
    if minimum_match:
        return int(minimum_match.group(1)), None
    raise ValueError(f"Cannot enforce desired_length: {value!r}")


def check_moment_article_length(article: str, author_input: str, flow: dict) -> int:
    minimum, maximum = requested_word_range(author_input, flow)
    count = count_words(article)
    if (minimum is not None and count < minimum) or (maximum is not None and count > maximum):
        expected = f"{minimum}–{maximum}" if minimum is not None and maximum is not None else (
            f"at least {minimum}" if minimum is not None else f"at most {maximum}"
        )
        raise ValueError(f"Moment article has {count} words; desired_length requires {expected} words")
    return count
