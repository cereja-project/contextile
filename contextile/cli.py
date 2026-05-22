from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .models import Lesson, LessonValidationError
from .renderer import build_context
from .retrieval import search_lessons
from .rules import (
    DEFAULT_PROJECT_RULES_CONFIG,
    RuleValidationError,
    detect_project_dependencies,
    detect_project_profiles,
    list_rule_scenarios,
    load_project_rule_settings,
    project_rules_path_for_root,
    resolve_active_profiles,
    select_rules_for_task,
    update_enabled_scenarios,
    validate_rules,
)
from .store import LessonStore
from .workspace import init_workspace, lessons_path_for_root


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        return args.func(args)
    except (LessonValidationError, RuleValidationError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="contextile",
        description="Manage and compact AI project instructions and lessons learned.",
    )
    parser.add_argument("--root", default=".", help="Project root. Defaults to the current directory.")

    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create a .contextile workspace.")
    _add_root_argument(init_parser)
    init_parser.add_argument("--force", action="store_true", help="Overwrite existing Contextile files.")
    init_parser.set_defaults(func=_cmd_init)

    add_parser = subparsers.add_parser("add-lesson", help="Append a lesson to lessons.jsonl.")
    _add_root_argument(add_parser)
    add_parser.add_argument("--id", required=True, help="Stable lesson id, e.g. preserve-domain-terms.")
    add_parser.add_argument("--when", required=True, help="Trigger/context where the lesson applies.")
    add_parser.add_argument("--do", dest="do", required=True, help="Expected action.")
    add_parser.add_argument("--avoid", required=True, help="Mistake to prevent.")
    add_parser.add_argument("--scope", default="", help="Where this lesson applies.")
    add_parser.add_argument("--tags", default="", help="Comma-separated tags.")
    add_parser.add_argument("--why", default="", help="Optional reason, only when non-obvious.")
    add_parser.add_argument("--updated-at", default="", help="Optional date or version marker.")
    add_parser.set_defaults(func=_cmd_add_lesson)

    search_parser = subparsers.add_parser("search", help="Search relevant lessons.")
    _add_root_argument(search_parser)
    search_parser.add_argument("query", help="Search query or task description.")
    search_parser.add_argument("--tag", action="append", default=[], help="Tag filter/hint. Can be repeated.")
    search_parser.add_argument("--file", action="append", default=[], help="File path hint. Can be repeated.")
    search_parser.add_argument("--limit", type=int, default=5, help="Maximum number of lessons to return.")
    search_parser.set_defaults(func=_cmd_search)

    build_parser = subparsers.add_parser("build-context", help="Build compact context for an LLM.")
    _add_root_argument(build_parser)
    build_parser.add_argument("--task", required=True, help="Current task description.")
    build_parser.add_argument("--tag", action="append", default=[], help="Tag hint. Can be repeated.")
    build_parser.add_argument("--file", action="append", default=[], help="File path hint. Can be repeated.")
    build_parser.add_argument(
        "--max-tokens",
        type=int,
        default=800,
        help="Approximate token budget for non-rule content. Relevant rules are always included in full.",
    )
    build_parser.add_argument("--lesson-limit", type=int, default=5, help="Maximum number of lessons to include.")
    build_parser.add_argument("--rule-limit", type=int, default=6, help="Maximum number of rules to include.")
    build_parser.add_argument("--no-rules", action="store_true", help="Disable automatic rule selection.")
    build_parser.add_argument("--output", help="Optional file to write the generated context.")
    build_parser.set_defaults(func=_cmd_build_context)

    validate_parser = subparsers.add_parser("validate", help="Validate lessons.jsonl.")
    _add_root_argument(validate_parser)
    validate_parser.set_defaults(func=_cmd_validate)

    compact_parser = subparsers.add_parser("compact", help="Compact lessons.jsonl by removing duplicate ids.")
    _add_root_argument(compact_parser)
    compact_parser.set_defaults(func=_cmd_compact)

    detect_rules_parser = subparsers.add_parser(
        "detect-rules",
        help="Detect project profiles/dependencies and optionally write project-rules.json.",
    )
    _add_root_argument(detect_rules_parser)
    detect_rules_parser.add_argument(
        "--write",
        action="store_true",
        help="Write detected profiles to .contextile/project-rules.json (enable_profiles).",
    )
    detect_rules_parser.set_defaults(func=_cmd_detect_rules)

    select_rules_parser = subparsers.add_parser("select-rules", help="Select the most relevant rules for a task.")
    _add_root_argument(select_rules_parser)
    select_rules_parser.add_argument("--task", required=True, help="Current task description.")
    select_rules_parser.add_argument("--tag", action="append", default=[], help="Tag hint. Can be repeated.")
    select_rules_parser.add_argument("--file", action="append", default=[], help="File path hint. Can be repeated.")
    select_rules_parser.add_argument("--limit", type=int, default=6, help="Maximum number of rules to include.")
    select_rules_parser.set_defaults(func=_cmd_select_rules)

    validate_rules_parser = subparsers.add_parser("validate-rules", help="Validate rule frontmatter and metadata.")
    _add_root_argument(validate_rules_parser)
    validate_rules_parser.set_defaults(func=_cmd_validate_rules)

    list_scenarios_parser = subparsers.add_parser(
        "list-rule-scenarios",
        help="List predefined rule scenarios built from .aiassistant/rules.",
    )
    _add_root_argument(list_scenarios_parser)
    list_scenarios_parser.set_defaults(func=_cmd_list_rule_scenarios)

    apply_scenario_parser = subparsers.add_parser(
        "apply-rule-scenario",
        help="Enable predefined scenario(s) in .contextile/project-rules.json.",
    )
    _add_root_argument(apply_scenario_parser)
    apply_scenario_parser.add_argument(
        "--scenario",
        action="append",
        required=True,
        help="Scenario id to enable. Can be repeated.",
    )
    apply_scenario_parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace enabled_scenarios instead of appending.",
    )
    apply_scenario_parser.set_defaults(func=_cmd_apply_rule_scenario)

    mcp_parser = subparsers.add_parser("mcp-server", help="Run Contextile MCP server.")
    _add_root_argument(mcp_parser)
    mcp_parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default="stdio",
        help="Transport mode. Default is stdio.",
    )
    mcp_parser.add_argument("--name", default="Contextile MCP", help="MCP server name.")
    mcp_parser.set_defaults(func=_cmd_mcp_server)

    return parser


def _add_root_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--root", default=".", help="Project root. Defaults to the current directory.")


def _store(args: argparse.Namespace) -> LessonStore:
    return LessonStore(lessons_path_for_root(args.root))


def _cmd_init(args: argparse.Namespace) -> int:
    created = init_workspace(args.root, force=args.force)
    if created:
        print("Created Contextile workspace files:")
        for path in created:
            print(f"- {path}")
    else:
        print("Contextile workspace already exists. Use --force to overwrite templates.")
    return 0


def _cmd_add_lesson(args: argparse.Namespace) -> int:
    store = _store(args)
    lesson = Lesson.from_dict(
        {
            "id": args.id,
            "when": args.when,
            "do": args.do,
            "avoid": args.avoid,
            "scope": args.scope,
            "tags": args.tags,
            "why": args.why,
            "updated_at": args.updated_at,
        }
    )
    store.append(lesson)
    print(f"Added lesson: {lesson.id}")
    return 0


def _cmd_search(args: argparse.Namespace) -> int:
    lessons = _store(args).list()
    results = search_lessons(lessons, args.query, tags=args.tag, files=args.file, limit=args.limit)
    if not results:
        print("No matching lessons found.")
        return 0

    for result in results:
        lesson = result.lesson
        print(f"- {lesson.id} (score={result.score:g})")
        print(f"  When: {lesson.when}")
        print(f"  Do: {lesson.do}")
        print(f"  Avoid: {lesson.avoid}")
        if lesson.tags:
            print(f"  Tags: {', '.join(lesson.tags)}")
        if result.reasons:
            print(f"  Reasons: {'; '.join(result.reasons)}")
    return 0


def _cmd_build_context(args: argparse.Namespace) -> int:
    lessons = _store(args).list()
    context = build_context(
        task=args.task,
        lessons=lessons,
        root=args.root,
        files=args.file,
        tags=args.tag,
        max_tokens=args.max_tokens,
        lesson_limit=args.lesson_limit,
        rule_limit=args.rule_limit,
        include_rules=not args.no_rules,
    )
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(context, encoding="utf-8")
        print(f"Wrote context to: {output_path}")
    else:
        print(context, end="")
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    store = _store(args)
    lessons = store.list()
    store.validate_unique_ids()
    print(f"Valid lessons file: {store.path} ({len(lessons)} lesson(s))")
    return 0


def _cmd_compact(args: argparse.Namespace) -> int:
    before, after = _store(args).compact()
    print(f"Compacted lessons: {before} -> {after}")
    return 0


def _cmd_detect_rules(args: argparse.Namespace) -> int:
    dependencies = sorted(detect_project_dependencies(args.root))
    detected_profiles = detect_project_profiles(args.root)
    active_profiles, _ = resolve_active_profiles(args.root)
    settings = load_project_rule_settings(args.root)

    print("Detected dependencies:")
    if dependencies:
        for item in dependencies:
            print(f"- {item}")
    else:
        print("- none")

    print("\nDetected profiles:")
    if detected_profiles:
        for profile, reason in sorted(detected_profiles.items()):
            print(f"- {profile}: {reason}")
    else:
        print("- none")

    print("\nActive profiles:")
    for profile in active_profiles:
        print(f"- {profile}")
    if settings.enabled_scenarios:
        print("\nEnabled scenarios:")
        for scenario in settings.enabled_scenarios:
            print(f"- {scenario}")

    if args.write:
        path = project_rules_path_for_root(args.root)
        path.parent.mkdir(parents=True, exist_ok=True)

        if path.exists():
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise LessonValidationError(f"Invalid JSON in {path}: {exc}") from exc
        else:
            raw = dict(DEFAULT_PROJECT_RULES_CONFIG)

        existing_enable = set(raw.get("enable_profiles", settings.enable_profiles))
        merged_enable = sorted(existing_enable | set(detected_profiles.keys()))
        raw["enable_profiles"] = merged_enable
        raw.setdefault("enabled_scenarios", settings.enabled_scenarios)
        path.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"\nUpdated rules config: {path}")

    return 0


def _cmd_select_rules(args: argparse.Namespace) -> int:
    selections = select_rules_for_task(
        root=args.root,
        task=args.task,
        files=args.file,
        tags=args.tag,
        limit=args.limit,
    )
    if not selections:
        print("No matching rules found.")
        return 0

    for selection in selections:
        rule = selection.rule
        summary = rule.instructions or rule.title
        print(f"- {rule.id} (score={selection.score:g})")
        print(f"  File: {rule.path.name}")
        print(f"  Mode: {rule.mode}")
        print(f"  Summary: {summary}")
        if selection.reasons:
            print(f"  Reasons: {'; '.join(selection.reasons)}")
    return 0


def _cmd_validate_rules(args: argparse.Namespace) -> int:
    error_count, errors = validate_rules(args.root)
    if error_count:
        print("Invalid rule files:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Rule files are valid.")
    return 0


def _cmd_list_rule_scenarios(args: argparse.Namespace) -> int:
    scenarios = list_rule_scenarios(args.root)
    if not scenarios:
        print("No scenarios found (check .aiassistant/rules).")
        return 0

    for scenario in scenarios:
        print(f"- {scenario.id} ({len(scenario.rule_ids)} rule(s))")
        print(f"  Profiles: {', '.join(scenario.profiles)}")
        print(f"  Description: {scenario.description}")
        print(f"  Sample rules: {', '.join(scenario.rule_ids[:5])}")
    return 0


def _cmd_apply_rule_scenario(args: argparse.Namespace) -> int:
    path, enabled = update_enabled_scenarios(
        args.root,
        args.scenario,
        replace=args.replace,
    )
    print(f"Updated scenario config: {path}")
    print(f"Enabled scenarios: {', '.join(enabled) if enabled else 'none'}")
    return 0


def _cmd_mcp_server(args: argparse.Namespace) -> int:
    from .mcp_server import run_mcp_server

    return run_mcp_server(root=args.root, transport=args.transport, server_name=args.name)


if __name__ == "__main__":
    raise SystemExit(main())
