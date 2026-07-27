from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


SLUG_REGEX = re.compile(r"^[a-z0-9][a-z0-9-]{1,48}[a-z0-9]$")


def is_valid_style_slug(slug: str) -> bool:
    if not slug or len(slug) < 2 or len(slug) > 50:
        return False
    if ".." in slug or "/" in slug or "\\" in slug:
        return False
    return bool(SLUG_REGEX.fullmatch(slug))


class StyleMetadata(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str = Field(min_length=1)
    slug: str = Field(min_length=2, max_length=50)
    mode: Literal["deep", "moment"]
    description: str = ""
    is_protected: bool = False
    previous_slugs: list[str] = Field(default_factory=list)
    created_at: str | None = None
    updated_at: str | None = None

    @model_validator(mode="after")
    def validate_slugs(self) -> "StyleMetadata":
        if not is_valid_style_slug(self.slug):
            raise ValueError(f"Metadata slug không hợp lệ: {self.slug}")
        invalid_aliases = [
            slug
            for slug in self.previous_slugs
            if not is_valid_style_slug(slug)
        ]
        if invalid_aliases:
            raise ValueError(f"Metadata alias không hợp lệ: {invalid_aliases}")
        return self


def validate_style_metadata(
    data: dict[str, Any],
    *,
    expected_slug: str | None = None,
    expected_mode: str | None = None,
) -> dict[str, Any]:
    metadata = StyleMetadata.model_validate(data)
    if expected_slug and metadata.slug != expected_slug:
        raise ValueError(
            f"Metadata slug '{metadata.slug}' không khớp folder '{expected_slug}'."
        )
    if expected_mode and metadata.mode != expected_mode:
        raise ValueError(
            f"Metadata mode '{metadata.mode}' không khớp '{expected_mode}'."
        )
    return metadata.model_dump(mode="json")
