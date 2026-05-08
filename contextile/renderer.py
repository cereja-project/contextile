from __future__ import annotations

from pathlib import Path

from .models import Lesson
from .retrieval import search_lessons
from .tokens import estimate_tokens, truncate_to_token_budget


def build_context(
    *,
    task: str,
    lessons: list[Lesson],
    root: str | Path = ".",
    files: list[str] | None = None,
    tags: list[str] | None = None,
    max_tokens: int = 800,
    lesson_limit: int = 5,
) -> str:
    """Build a compact Markdown context block for an LLM."""
    root_path = Path(root)
    files = files or []
    tags = tags or []

    sections: list[str] = [
        "# Contextile Context",
        "",
        "## Current Task",
        task.strip() or "No task provided.",
    ]

    instruction_sections = _load_relevant_instruction_sections(root_path, task, files, tags)
    if instruction_sections:
        sections.extend(["", "## Relevant Instructions"])
        sections.extend(instruction_sections)

    results = search_lessons(lessons, task, tags=tags, files=files, limit=lesson_limit)
    if results:
        sections.extend(["", "## Relevant Lessons"])
        for result in results:
            lesson = result.lesson
            sections.append(f"- **{lesson.id}**")
            sections.append(f"  - When: {lesson.when}")
            sections.append(f"  - Do: {lesson.do}")
            sections.append(f"  - Avoid: {lesson.avoid}")
            if lesson.scope:
                sections.append(f"  - Scope: {lesson.scope}")
            if lesson.tags:
                sections.append(f"  - Tags: {', '.join(lesson.tags)}")
    else:
        sections.extend(["", "## Relevant Lessons", "No matching lessons found."])

    sections.extend([
        "",
        "## Working Rules",
        "- Prefer minimal, safe changes that preserve existing project patterns.",
        "- Do not claim that tests, lint, build, or validation were run unless they were actually run.",
        "- Preserve existing domain terminology and public contracts unless the task explicitly asks for a change.",
    ])

    context = "\n".join(sections).strip() + "\n"
    return truncate_to_token_budget(context, max_tokens)


def _load_relevant_instruction_sections(
    root: Path,
    task: str,
    files: list[str],
    tags: list[str],
) -> list[str]:
    instructions_dir = root / ".contextile" / "instructions"
    if not instructions_dir.exists():
        return []

    query_text = " ".join([task, " ".join(files), " ".join(tags)]).lower()
    candidates = sorted(instructions_dir.glob("*.md"))
    sections: list[str] = []

    for path in candidates:
        text = path.read_text(encoding="utf-8").strip()
        if not text or "TODO:" in text:
            continue

        stem_tokens = set(path.stem.replace("-", " ").split())
        is_relevant = path.stem in {"project-context", "architecture-rules", "validation"}
        is_relevant = is_relevant or any(token in query_text for token in stem_tokens)

        if is_relevant:
            snippet = _compact_instruction(text, token_budget=180)
            sections.append(f"### {path.name}\n{snippet}")

    return sections


def _compact_instruction(text: str, token_budget: int) -> str:
    if estimate_tokens(text) <= token_budget:
        return text
    return truncate_to_token_budget(text, token_budget)
