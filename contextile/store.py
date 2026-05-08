from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .models import Lesson, LessonValidationError


DEFAULT_CONTEXTILE_DIR = ".contextile"
DEFAULT_LESSONS_FILE = "lessons.jsonl"


class LessonStore:
    """Read, write, and validate JSONL lessons."""

    def __init__(self, path: str | Path = Path(DEFAULT_CONTEXTILE_DIR) / DEFAULT_LESSONS_FILE) -> None:
        self.path = Path(path)

    def ensure_exists(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("", encoding="utf-8")

    def list(self) -> list[Lesson]:
        if not self.path.exists():
            return []

        lessons: list[Lesson] = []
        errors: list[str] = []

        for line_number, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                if not isinstance(data, dict):
                    raise LessonValidationError("Line must contain a JSON object.")
                lessons.append(Lesson.from_dict(data))
            except (json.JSONDecodeError, LessonValidationError) as exc:
                errors.append(f"line {line_number}: {exc}")

        if errors:
            joined = "\n".join(errors)
            raise LessonValidationError(f"Invalid lessons file: {self.path}\n{joined}")

        return lessons

    def append(self, lesson: Lesson) -> None:
        self.ensure_exists()
        existing_ids = {item.id for item in self.list()}
        if lesson.id in existing_ids:
            raise LessonValidationError(f"A lesson with id '{lesson.id}' already exists.")
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(lesson.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")

    def write_all(self, lessons: Iterable[Lesson]) -> None:
        self.ensure_exists()
        ids: set[str] = set()
        lines: list[str] = []
        for lesson in lessons:
            if lesson.id in ids:
                raise LessonValidationError(f"Duplicate lesson id: {lesson.id}")
            ids.add(lesson.id)
            lines.append(json.dumps(lesson.to_dict(), ensure_ascii=False, sort_keys=True))
        self.path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

    def compact(self) -> tuple[int, int]:
        """Remove exact duplicate ids, keeping the last occurrence.

        Returns:
            A tuple with (before_count, after_count).
        """
        lessons = self.list()
        before = len(lessons)
        by_id: dict[str, Lesson] = {}
        for lesson in lessons:
            by_id[lesson.id] = lesson
        compacted = list(by_id.values())
        self.write_all(compacted)
        return before, len(compacted)

    def validate_unique_ids(self) -> None:
        seen: set[str] = set()
        duplicates: list[str] = []
        for lesson in self.list():
            if lesson.id in seen:
                duplicates.append(lesson.id)
            seen.add(lesson.id)
        if duplicates:
            raise LessonValidationError(f"Duplicate lesson id(s): {', '.join(sorted(set(duplicates)))}")
