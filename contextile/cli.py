from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .models import Lesson, LessonValidationError
from .renderer import build_context
from .retrieval import search_lessons
from .store import LessonStore
from .workspace import init_workspace, lessons_path_for_root


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        return args.func(args)
    except LessonValidationError as exc:
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
    init_parser.add_argument("--force", action="store_true", help="Overwrite existing Contextile files.")
    init_parser.set_defaults(func=_cmd_init)

    add_parser = subparsers.add_parser("add-lesson", help="Append a lesson to lessons.jsonl.")
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
    search_parser.add_argument("query", help="Search query or task description.")
    search_parser.add_argument("--tag", action="append", default=[], help="Tag filter/hint. Can be repeated.")
    search_parser.add_argument("--file", action="append", default=[], help="File path hint. Can be repeated.")
    search_parser.add_argument("--limit", type=int, default=5, help="Maximum number of lessons to return.")
    search_parser.set_defaults(func=_cmd_search)

    build_parser = subparsers.add_parser("build-context", help="Build compact context for an LLM.")
    build_parser.add_argument("--task", required=True, help="Current task description.")
    build_parser.add_argument("--tag", action="append", default=[], help="Tag hint. Can be repeated.")
    build_parser.add_argument("--file", action="append", default=[], help="File path hint. Can be repeated.")
    build_parser.add_argument("--max-tokens", type=int, default=800, help="Approximate token budget.")
    build_parser.add_argument("--lesson-limit", type=int, default=5, help="Maximum number of lessons to include.")
    build_parser.add_argument("--output", help="Optional file to write the generated context.")
    build_parser.set_defaults(func=_cmd_build_context)

    validate_parser = subparsers.add_parser("validate", help="Validate lessons.jsonl.")
    validate_parser.set_defaults(func=_cmd_validate)

    compact_parser = subparsers.add_parser("compact", help="Compact lessons.jsonl by removing duplicate ids.")
    compact_parser.set_defaults(func=_cmd_compact)

    return parser


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


if __name__ == "__main__":
    raise SystemExit(main())
