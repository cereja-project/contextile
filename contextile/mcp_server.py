from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

from .models import Lesson, LessonValidationError
from .renderer import build_context
from .retrieval import search_lessons
from .rules import (
    detect_project_dependencies,
    detect_project_profiles,
    list_rule_scenarios,
    load_project_rule_settings,
    resolve_active_profiles,
    select_rules_for_task,
    update_enabled_scenarios,
    validate_rules,
)
from .store import LessonStore
from .tokens import estimate_tokens
from .workspace import lessons_path_for_root

_DEFAULT_AGENTS_TASK = "General coding and maintenance tasks for this repository."
_SHELL_FENCE_LANGS = {"", "bash", "sh", "zsh", "shell", "pwsh", "powershell", "cmd"}


def tool_build_context(
    *,
    task: str,
    root: str = ".",
    files: list[str] | None = None,
    tags: list[str] | None = None,
    max_tokens: int = 800,
    lesson_limit: int = 5,
    rule_limit: int = 6,
    include_rules: bool = True,
) -> dict[str, Any]:
    lessons = LessonStore(lessons_path_for_root(root)).list()
    context = build_context(
        task=task,
        lessons=lessons,
        root=root,
        files=files or [],
        tags=tags or [],
        max_tokens=max_tokens,
        lesson_limit=lesson_limit,
        rule_limit=rule_limit,
        include_rules=include_rules,
    )
    return {
        "context": context,
        "estimated_tokens": estimate_tokens(context),
        "root": str(Path(root)),
    }


def tool_search_lessons(
    *,
    query: str,
    root: str = ".",
    tags: list[str] | None = None,
    files: list[str] | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    lessons = LessonStore(lessons_path_for_root(root)).list()
    results = search_lessons(
        lessons,
        query,
        tags=tags or [],
        files=files or [],
        limit=limit,
    )
    return {
        "count": len(results),
        "results": [
            {
                "id": result.lesson.id,
                "score": result.score,
                "when": result.lesson.when,
                "do": result.lesson.do,
                "avoid": result.lesson.avoid,
                "scope": result.lesson.scope,
                "tags": result.lesson.tags,
                "reasons": result.reasons,
            }
            for result in results
        ],
    }


def tool_add_lesson(
    *,
    id: str,
    when: str,
    do: str,
    avoid: str,
    root: str = ".",
    scope: str = "",
    tags: list[str] | str | None = None,
    why: str = "",
    updated_at: str = "",
) -> dict[str, Any]:
    lesson = Lesson.from_dict(
        {
            "id": id,
            "when": when,
            "do": do,
            "avoid": avoid,
            "scope": scope,
            "tags": tags or [],
            "why": why,
            "updated_at": updated_at,
        }
    )
    store = LessonStore(lessons_path_for_root(root))
    store.append(lesson)
    return {
        "path": str(store.path),
        "lesson": lesson.to_dict(),
    }


def tool_build_agents_md(
    *,
    root: str = ".",
    task: str = _DEFAULT_AGENTS_TASK,
    files: list[str] | None = None,
    tags: list[str] | None = None,
    rule_limit: int = 10,
    lesson_limit: int = 8,
    output_path: str = "AGENTS.md",
    write: bool = True,
    overwrite: bool = False,
) -> dict[str, Any]:
    root_path = Path(root)
    files = files or []
    tags = tags or []

    detect = tool_detect_rules(root=str(root_path))
    selections = select_rules_for_task(
        root=root_path,
        task=task,
        files=files,
        tags=tags,
        limit=max(0, rule_limit),
    )
    lessons = LessonStore(lessons_path_for_root(root_path)).list()
    lesson_results = search_lessons(
        lessons,
        query=task,
        tags=tags,
        files=files,
        limit=max(0, lesson_limit),
    )
    instruction_docs = _load_instruction_documents(root_path)
    setup_commands = _extract_setup_commands(instruction_docs, root_path=root_path)

    sections: list[str] = [
        "# AGENTS.md",
        "",
        "## Project Overview",
        f"- Repository root: `{root_path}`",
        f"- Active profiles: {', '.join(detect['active_profiles']) if detect['active_profiles'] else 'none'}",
        f"- Enabled scenarios: {', '.join(detect['settings']['enabled_scenarios']) if detect['settings']['enabled_scenarios'] else 'none'}",
        f"- Detected dependencies: {', '.join(detect['dependencies']) if detect['dependencies'] else 'none'}",
    ]

    if setup_commands:
        sections.extend(["", "## Setup Commands"])
        sections.extend([f"- `{command}`" for command in setup_commands])

    sections.extend(
        [
            "",
            "## Operating Constraints",
            "- Prefer minimal, safe changes that preserve existing project patterns.",
            "- Run relevant tests/validation after changes and report what was actually run.",
            "- Preserve existing domain terminology and public contracts unless explicitly asked to change them.",
        ]
    )

    if selections:
        required_rules = [item for item in selections if item.rule.mode == "required"]
        advisory_rules = [item for item in selections if item.rule.mode != "required"]
        sections.extend(["", "## Rule Priorities"])
        if required_rules:
            sections.append("### Required Rules")
            for item in required_rules:
                summary = item.rule.instructions or item.rule.title
                sections.append(f"- `{item.rule.id}` ({item.rule.path.name}): {summary}")
        if advisory_rules:
            sections.append("### Advisory Rules")
            for item in advisory_rules:
                summary = item.rule.instructions or item.rule.title
                sections.append(f"- `{item.rule.id}` ({item.rule.path.name}): {summary}")

    if lesson_results:
        sections.extend(["", "## Lessons Learned"])
        for result in lesson_results:
            lesson = result.lesson
            sections.append(f"- `{lesson.id}`")
            sections.append(f"  - When: {lesson.when}")
            sections.append(f"  - Do: {lesson.do}")
            sections.append(f"  - Avoid: {lesson.avoid}")

    if instruction_docs:
        sections.extend(["", "## Project Instructions"])
        for name, text in instruction_docs:
            sections.append(f"### {name}")
            sections.append(text)

    content = "\n".join(sections).strip() + "\n"
    target_path = (root_path / output_path).resolve()

    if write:
        if target_path.exists() and not overwrite:
            raise LessonValidationError(
                f"{target_path} already exists. Use overwrite=True to replace it."
            )
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(content, encoding="utf-8")

    return {
        "root": str(root_path),
        "path": str(target_path),
        "written": write,
        "estimated_tokens": estimate_tokens(content),
        "content": content,
    }


def tool_select_rules(
    *,
    task: str,
    root: str = ".",
    files: list[str] | None = None,
    tags: list[str] | None = None,
    limit: int = 6,
) -> dict[str, Any]:
    selections = select_rules_for_task(
        root=root,
        task=task,
        files=files or [],
        tags=tags or [],
        limit=limit,
    )
    return {
        "count": len(selections),
        "results": [
            {
                "id": item.rule.id,
                "path": str(item.rule.path),
                "mode": item.rule.mode,
                "priority": item.rule.priority,
                "profiles": item.rule.profiles,
                "tags": item.rule.tags,
                "instructions": item.rule.instructions,
                "score": item.score,
                "reasons": item.reasons,
            }
            for item in selections
        ],
    }


def tool_detect_rules(*, root: str = ".") -> dict[str, Any]:
    settings = load_project_rule_settings(root)
    dependencies = sorted(detect_project_dependencies(root))
    detected_profiles = detect_project_profiles(root)
    active_profiles, _ = resolve_active_profiles(root, settings)
    return {
        "root": str(Path(root)),
        "dependencies": dependencies,
        "detected_profiles": detected_profiles,
        "active_profiles": active_profiles,
        "settings": {
            "rules_dir": settings.rules_dir,
            "base_profiles": settings.base_profiles,
            "enable_profiles": settings.enable_profiles,
            "disable_profiles": settings.disable_profiles,
            "enabled_scenarios": settings.enabled_scenarios,
            "force_rules": settings.force_rules,
            "disable_rules": settings.disable_rules,
        },
    }


def tool_validate_rules(*, root: str = ".") -> dict[str, Any]:
    error_count, errors = validate_rules(root)
    return {
        "valid": error_count == 0,
        "error_count": error_count,
        "errors": errors,
    }


def tool_list_rule_scenarios(*, root: str = ".") -> dict[str, Any]:
    scenarios = list_rule_scenarios(root)
    return {
        "count": len(scenarios),
        "scenarios": [
            {
                "id": scenario.id,
                "description": scenario.description,
                "profiles": scenario.profiles,
                "rule_count": len(scenario.rule_ids),
                "rule_ids": scenario.rule_ids,
            }
            for scenario in scenarios
        ],
    }


def tool_apply_rule_scenario(
    *,
    root: str = ".",
    scenarios: list[str],
    replace: bool = False,
) -> dict[str, Any]:
    path, enabled = update_enabled_scenarios(root, scenarios, replace=replace)
    return {
        "path": str(path),
        "enabled_scenarios": enabled,
    }


def create_mcp_app(*, default_root: str = ".", server_name: str = "Contextile MCP") -> Any:
    try:
        from mcp.server.fastmcp import FastMCP
    except ModuleNotFoundError as exc:
        raise LessonValidationError(
            "MCP dependency is not installed. Install with: pip install \"contextile[mcp]\""
        ) from exc

    mcp = FastMCP(
        server_name,
        instructions=(
            "Contextile MCP server for building compact project context, storing/searching lessons, "
            "building AGENTS.md drafts, and selecting project rules from .aiassistant/rules."
        ),
        json_response=True,
        stateless_http=True,
    )

    @mcp.tool()
    def build_context_tool(
        task: str,
        root: str = default_root,
        files: list[str] | None = None,
        tags: list[str] | None = None,
        max_tokens: int = 800,
        lesson_limit: int = 5,
        rule_limit: int = 6,
        include_rules: bool = True,
    ) -> dict[str, Any]:
        """Build compact context with instructions, rules, and lessons."""
        return tool_build_context(
            task=task,
            root=root,
            files=files,
            tags=tags,
            max_tokens=max_tokens,
            lesson_limit=lesson_limit,
            rule_limit=rule_limit,
            include_rules=include_rules,
        )

    @mcp.tool()
    def search_lessons_tool(
        query: str,
        root: str = default_root,
        tags: list[str] | None = None,
        files: list[str] | None = None,
        limit: int = 5,
    ) -> dict[str, Any]:
        """Search stored lessons by query, tags, and file hints."""
        return tool_search_lessons(
            query=query,
            root=root,
            tags=tags,
            files=files,
            limit=limit,
        )

    @mcp.tool()
    def add_lesson_tool(
        id: str,
        when: str,
        do: str,
        avoid: str,
        root: str = default_root,
        scope: str = "",
        tags: list[str] | str | None = None,
        why: str = "",
        updated_at: str = "",
    ) -> dict[str, Any]:
        """Add and persist a lesson in .contextile/lessons.jsonl."""
        return tool_add_lesson(
            id=id,
            when=when,
            do=do,
            avoid=avoid,
            root=root,
            scope=scope,
            tags=tags,
            why=why,
            updated_at=updated_at,
        )

    @mcp.tool()
    def build_agents_md_tool(
        root: str = default_root,
        task: str = _DEFAULT_AGENTS_TASK,
        files: list[str] | None = None,
        tags: list[str] | None = None,
        rule_limit: int = 10,
        lesson_limit: int = 8,
        output_path: str = "AGENTS.md",
        write: bool = True,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        """Build an AGENTS.md draft from project rules, lessons, and instructions."""
        return tool_build_agents_md(
            root=root,
            task=task,
            files=files,
            tags=tags,
            rule_limit=rule_limit,
            lesson_limit=lesson_limit,
            output_path=output_path,
            write=write,
            overwrite=overwrite,
        )

    @mcp.tool()
    def select_rules_tool(
        task: str,
        root: str = default_root,
        files: list[str] | None = None,
        tags: list[str] | None = None,
        limit: int = 6,
    ) -> dict[str, Any]:
        """Select relevant rules from .aiassistant/rules for a task."""
        return tool_select_rules(
            task=task,
            root=root,
            files=files,
            tags=tags,
            limit=limit,
        )

    @mcp.tool()
    def detect_rules_tool(root: str = default_root) -> dict[str, Any]:
        """Detect project profiles and dependencies for rule selection."""
        return tool_detect_rules(root=root)

    @mcp.tool()
    def validate_rules_tool(root: str = default_root) -> dict[str, Any]:
        """Validate rule files in .aiassistant/rules."""
        return tool_validate_rules(root=root)

    @mcp.tool()
    def list_rule_scenarios_tool(root: str = default_root) -> dict[str, Any]:
        """List predefined scenarios mapped to rules in .aiassistant/rules."""
        return tool_list_rule_scenarios(root=root)

    @mcp.tool()
    def apply_rule_scenario_tool(
        scenarios: list[str],
        root: str = default_root,
        replace: bool = False,
    ) -> dict[str, Any]:
        """Enable scenario(s) in .contextile/project-rules.json."""
        return tool_apply_rule_scenario(root=root, scenarios=scenarios, replace=replace)

    return mcp


def run_mcp_server(
    *,
    root: str = ".",
    transport: str = "stdio",
    server_name: str = "Contextile MCP",
) -> int:
    mcp = create_mcp_app(default_root=root, server_name=server_name)
    if transport == "stdio":
        mcp.run()
    else:
        mcp.run(transport=transport)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="contextile-mcp",
        description="Run Contextile MCP server.",
    )
    parser.add_argument("--root", default=".", help="Project root. Defaults to the current directory.")
    parser.add_argument("--name", default="Contextile MCP", help="Server name shown to MCP clients.")
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default="stdio",
        help="Transport mode. Default is stdio.",
    )
    args = parser.parse_args(argv)
    return run_mcp_server(root=args.root, transport=args.transport, server_name=args.name)


def _load_instruction_documents(root: Path) -> list[tuple[str, str]]:
    instructions_dir = root / ".contextile" / "instructions"
    if not instructions_dir.exists():
        return []

    docs: list[tuple[str, str]] = []
    for path in sorted(instructions_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8").strip()
        if not text or "TODO:" in text:
            continue
        docs.append((path.name, text))
    return docs


def _extract_setup_commands(
    instruction_docs: list[tuple[str, str]],
    *,
    root_path: Path,
    limit: int = 12,
) -> list[str]:
    commands: list[str] = []
    seen: set[str] = set()
    fence_pattern = re.compile(r"```([^\n`]*)\n(.*?)```", re.DOTALL)

    for _, text in instruction_docs:
        for language, body in fence_pattern.findall(text):
            if language.strip().lower() not in _SHELL_FENCE_LANGS:
                continue
            for raw_line in body.splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("$"):
                    line = line[1:].strip()
                if line and line not in seen:
                    commands.append(line)
                    seen.add(line)
                if len(commands) >= limit:
                    return commands

    # Fallback commands when instructions have no explicit shell blocks.
    fallback: list[str] = []
    if (root_path / "pyproject.toml").exists():
        fallback.append("python -m pip install -e .")
    if (root_path / "tests").exists():
        fallback.append("python -m pytest")

    for command in fallback:
        if command not in seen:
            commands.append(command)
            seen.add(command)
        if len(commands) >= limit:
            break

    return commands


if __name__ == "__main__":
    raise SystemExit(main())
