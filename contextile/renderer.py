from __future__ import annotations

from pathlib import Path

from .models import Lesson
from .retrieval import search_lessons
from .rules import select_rules_for_task
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
    rule_limit: int = 6,
    include_rules: bool = True,
) -> str:
    """Build a compact Markdown context block for an LLM."""
    root_path = Path(root)
    files = files or []
    tags = tags or []

    intro_sections: list[str] = [
        "# Contextile Context",
        "",
        "## Current Task",
        task.strip() or "No task provided.",
    ]

    instruction_sections = _load_relevant_instruction_sections(root_path, task, files, tags)
    if instruction_sections:
        intro_sections.extend(["", "## Relevant Instructions"])
        intro_sections.extend(instruction_sections)

    rule_sections: list[str] = []
    if include_rules:
        rule_sections = _load_relevant_rules(root_path, task, files, tags, limit=rule_limit)

    tail_sections: list[str] = []
    results = search_lessons(lessons, task, tags=tags, files=files, limit=lesson_limit)
    if results:
        tail_sections.extend(["## Relevant Lessons"])
        for result in results:
            lesson = result.lesson
            tail_sections.append(f"- **{lesson.id}**")
            tail_sections.append(f"  - When: {lesson.when}")
            tail_sections.append(f"  - Do: {lesson.do}")
            tail_sections.append(f"  - Avoid: {lesson.avoid}")
            if lesson.scope:
                tail_sections.append(f"  - Scope: {lesson.scope}")
            if lesson.tags:
                tail_sections.append(f"  - Tags: {', '.join(lesson.tags)}")
    else:
        tail_sections.extend(["## Relevant Lessons", "No matching lessons found."])

    tail_sections.extend([
        "",
        "## Working Rules",
        "- Prefer minimal, safe changes that preserve existing project patterns.",
        "- Do not claim that tests, lint, build, or validation were run unless they were actually run.",
        "- Preserve existing domain terminology and public contracts unless the task explicitly asks for a change.",
    ])

    intro_text = _join_lines(intro_sections)
    rules_text = _join_lines(["## Relevant Rules", *rule_sections]) if rule_sections else ""
    tail_text = _join_lines(tail_sections)

    # Rules are essential and must not be truncated by token budget.
    if include_rules and rules_text:
        remaining_tokens = max(0, max_tokens)
        intro_trimmed = truncate_to_token_budget(intro_text, remaining_tokens)
        remaining_tokens = max(0, remaining_tokens - estimate_tokens(intro_trimmed))
        tail_trimmed = truncate_to_token_budget(tail_text, remaining_tokens)
        return _join_blocks([intro_trimmed, rules_text, tail_trimmed])

    context = _join_blocks([intro_text, tail_text])
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


def _load_relevant_rules(
    root: Path,
    task: str,
    files: list[str],
    tags: list[str],
    *,
    limit: int,
) -> list[str]:
    selections = select_rules_for_task(
        root=root,
        task=task,
        files=files,
        tags=tags,
        limit=limit,
    )
    sections: list[str] = []
    for selection in selections:
        rule = selection.rule
        summary = rule.instructions or rule.title
        snippet = rule.body.strip()
        sections.append(f"### {rule.path.name}")
        sections.append(f"- Rule id: `{rule.id}`")
        sections.append(f"- Mode: `{rule.mode}`")
        sections.append(f"- Apply: {rule.apply or 'by model decision'}")
        sections.append(f"- Summary: {summary}")
        sections.append(f"- Why selected: {', '.join(selection.reasons[:3])}")
        sections.append(snippet)
    return sections


def _join_lines(lines: list[str]) -> str:
    text = "\n".join(lines).strip()
    return f"{text}\n" if text else ""


def _join_blocks(blocks: list[str]) -> str:
    clean = [block.strip() for block in blocks if block and block.strip()]
    if not clean:
        return ""
    return "\n\n".join(clean).strip() + "\n"
