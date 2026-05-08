from __future__ import annotations

import json
from pathlib import Path

DEFAULT_CONFIG = {
    "version": 1,
    "lessons_file": "lessons.jsonl",
    "instructions_dir": "instructions",
    "default_max_tokens": 800,
}

DEFAULT_INSTRUCTIONS = {
    "project-context.md": """# Project Context\n\nTODO: Describe the project purpose, main modules, domain terms, and important constraints.\n""",
    "architecture-rules.md": """# Architecture Rules\n\nTODO: Describe architectural boundaries, dependency rules, public contracts, and patterns to preserve.\n""",
    "code-standards.md": """# Code Standards\n\nTODO: Describe naming, formatting, typing, error handling, logging, and documentation standards.\n""",
    "validation.md": """# Validation\n\nTODO: Describe how to validate changes: tests, lint, typecheck, build, manual checks, migrations, or API checks.\n""",
}


def init_workspace(root: str | Path = ".", *, force: bool = False) -> list[Path]:
    root_path = Path(root)
    contextile_dir = root_path / ".contextile"
    instructions_dir = contextile_dir / "instructions"
    created: list[Path] = []

    contextile_dir.mkdir(parents=True, exist_ok=True)
    instructions_dir.mkdir(parents=True, exist_ok=True)

    config_path = contextile_dir / "config.json"
    if force or not config_path.exists():
        config_path.write_text(json.dumps(DEFAULT_CONFIG, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        created.append(config_path)

    lessons_path = contextile_dir / "lessons.jsonl"
    if force or not lessons_path.exists():
        lessons_path.write_text("", encoding="utf-8")
        created.append(lessons_path)

    for filename, content in DEFAULT_INSTRUCTIONS.items():
        path = instructions_dir / filename
        if force or not path.exists():
            path.write_text(content, encoding="utf-8")
            created.append(path)

    return created


def lessons_path_for_root(root: str | Path = ".") -> Path:
    return Path(root) / ".contextile" / "lessons.jsonl"
