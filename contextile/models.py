from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class LessonValidationError(ValueError):
    """Raised when a lesson record is invalid."""


@dataclass(frozen=True)
class Lesson:
    """A durable lesson used to guide future LLM-assisted work."""

    id: str
    when: str
    do: str
    avoid: str
    scope: str = ""
    tags: list[str] = field(default_factory=list)
    why: str = ""
    updated_at: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Lesson":
        lesson = cls(
            id=str(data.get("id", "")).strip(),
            when=str(data.get("when", "")).strip(),
            do=str(data.get("do", "")).strip(),
            avoid=str(data.get("avoid", "")).strip(),
            scope=str(data.get("scope", "")).strip(),
            tags=_normalize_tags(data.get("tags", [])),
            why=str(data.get("why", "")).strip(),
            updated_at=str(data.get("updated_at", "")).strip(),
        )
        lesson.validate()
        return lesson

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": self.id,
            "when": self.when,
            "do": self.do,
            "avoid": self.avoid,
        }
        if self.scope:
            data["scope"] = self.scope
        if self.tags:
            data["tags"] = self.tags
        if self.why:
            data["why"] = self.why
        if self.updated_at:
            data["updated_at"] = self.updated_at
        return data

    def validate(self) -> None:
        missing = [name for name in ("id", "when", "do", "avoid") if not getattr(self, name)]
        if missing:
            raise LessonValidationError(f"Missing required field(s): {', '.join(missing)}")

        if not _is_stable_id(self.id):
            raise LessonValidationError(
                "Invalid lesson id. Use lowercase letters, numbers, hyphens, underscores, or dots."
            )

        if len(self.when) < 8:
            raise LessonValidationError("The 'when' field is too short to be useful.")

        if len(self.do) < 8:
            raise LessonValidationError("The 'do' field is too short to be useful.")

        if len(self.avoid) < 8:
            raise LessonValidationError("The 'avoid' field is too short to be useful.")

        if any(not tag for tag in self.tags):
            raise LessonValidationError("Tags must not be empty.")


def _normalize_tags(value: Any) -> list[str]:
    if value is None:
        return []

    if isinstance(value, str):
        raw_tags = value.split(",")
    elif isinstance(value, list):
        raw_tags = value
    else:
        raise LessonValidationError("The 'tags' field must be a string or a list of strings.")

    tags: list[str] = []
    seen: set[str] = set()
    for item in raw_tags:
        tag = str(item).strip().lower()
        if tag and tag not in seen:
            tags.append(tag)
            seen.add(tag)
    return tags


def _is_stable_id(value: str) -> bool:
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789-_.")
    return bool(value) and all(char in allowed for char in value)
