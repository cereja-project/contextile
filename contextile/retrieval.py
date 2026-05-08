from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .models import Lesson

_TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9_./-]+")


@dataclass(frozen=True)
class SearchResult:
    lesson: Lesson
    score: float
    reasons: list[str]


def search_lessons(
    lessons: list[Lesson],
    query: str,
    *,
    tags: list[str] | None = None,
    files: list[str] | None = None,
    limit: int = 5,
) -> list[SearchResult]:
    """Return the most relevant lessons using a dependency-free scoring strategy."""
    query_tokens = _tokenize(" ".join([query, " ".join(files or []), " ".join(tags or [])]))
    requested_tags = {tag.lower().strip() for tag in tags or [] if tag.strip()}

    results: list[SearchResult] = []
    for lesson in lessons:
        score, reasons = _score_lesson(lesson, query_tokens, requested_tags, files or [])
        if score > 0:
            results.append(SearchResult(lesson=lesson, score=score, reasons=reasons))

    results.sort(key=lambda item: (-item.score, item.lesson.id))
    return results[: max(0, limit)]


def _score_lesson(
    lesson: Lesson,
    query_tokens: set[str],
    requested_tags: set[str],
    files: list[str],
) -> tuple[float, list[str]]:
    score = 0.0
    reasons: list[str] = []

    lesson_tags = {tag.lower() for tag in lesson.tags}
    tag_matches = requested_tags & lesson_tags
    if tag_matches:
        score += 8 * len(tag_matches)
        reasons.append("tag match: " + ", ".join(sorted(tag_matches)))

    id_tokens = _tokenize(lesson.id)
    scope_tokens = _tokenize(lesson.scope)
    when_tokens = _tokenize(lesson.when)
    do_tokens = _tokenize(lesson.do)
    avoid_tokens = _tokenize(lesson.avoid)
    tag_tokens = set(lesson_tags)

    weighted_fields = [
        ("id", id_tokens, 5),
        ("tags", tag_tokens, 5),
        ("scope", scope_tokens, 3),
        ("when", when_tokens, 3),
        ("do", do_tokens, 2),
        ("avoid", avoid_tokens, 2),
    ]

    for field_name, field_tokens, weight in weighted_fields:
        matches = query_tokens & field_tokens
        if matches:
            score += weight * len(matches)
            reasons.append(f"{field_name}: " + ", ".join(sorted(matches)[:5]))

    file_names = {_normalize_file_hint(path) for path in files}
    combined_text = " ".join([lesson.when, lesson.scope, lesson.do, lesson.avoid, " ".join(lesson.tags)])
    combined_tokens = _tokenize(combined_text)
    file_matches = file_names & combined_tokens
    if file_matches:
        score += 4 * len(file_matches)
        reasons.append("file hint: " + ", ".join(sorted(file_matches)))

    return score, reasons


def _tokenize(text: str) -> set[str]:
    tokens = set()
    for token in _TOKEN_PATTERN.findall(text.lower()):
        token = token.strip("._-/")
        if len(token) >= 2:
            tokens.add(token)
            for part in re.split(r"[._/-]+", token):
                if len(part) >= 2:
                    tokens.add(part)
    return tokens


def _normalize_file_hint(path: str) -> str:
    name = Path(path).stem.lower().strip()
    return re.sub(r"[^a-z0-9_./-]+", "", name)
