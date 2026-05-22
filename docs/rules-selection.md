# Rules Selection (Built-in + Project Rules)

This guide explains how Contextile selects and applies rules from:

- built-in defaults bundled with Contextile;
- optional project rules in `.aiassistant/rules`.

## Overview

Contextile combines:

- static project instructions (`.contextile/instructions/*.md`);
- durable lessons (`.contextile/lessons.jsonl`);
- rule files selected by context (built-in catalog + `.aiassistant/rules/*.md`).

Rule selection is used by:

- `contextile select-rules`
- `contextile build-context` (enabled by default)
- MCP tool `select_rules_tool`

## Rule file format

Each rule is a Markdown file with optional frontmatter. Project custom rules should live in `.aiassistant/rules`.

```md
---
id: sqlalchemy-mapping
apply: by model decision
instructions: Apply when editing SQLAlchemy ORM models.
profiles: [python, sqlalchemy]
tags: [orm, persistence]
match_deps: [sqlalchemy, alembic]
match_files: ["**/models/*.py", "**/repositories/*.py"]
always: false
priority: 80
mode: advisory
---

# SQLAlchemy Mapping

Use SQLAlchemy 2.0 style mapping (`Mapped[T]`, `mapped_column`, `DeclarativeBase`).
```

Supported frontmatter keys:

- `id` (string): stable identifier. If omitted, file stem is used.
- `apply` (string): optional apply hint.
- `instructions` (string): short summary used in selection output.
- `profiles` (list|string): profile hints (`python`, `pytest`, `sqlalchemy`, `docs`, etc.).
- `tags` (list|string): extra searchable tags.
- `match_deps` (list|string): dependency hints to match detected stack.
- `match_files` (list|string): file globs to match current file hints.
- `always` (bool): include as baseline rule.
- `priority` (int): tie-breaker relevance.
- `mode` (string): `advisory` or `required`.

## Project rules config

Contextile stores project-level rule settings in `.contextile/project-rules.json`.

```json
{
  "version": 1,
  "rules_dir": ".aiassistant/rules",
  "base_profiles": ["python", "tests"],
  "enable_profiles": [],
  "disable_profiles": [],
  "enabled_scenarios": [],
  "force_rules": [],
  "disable_rules": []
}
```

Behavior:

- `base_profiles`: always active unless disabled.
- `enable_profiles`: manual opt-in profiles.
- `disable_profiles`: explicit profile opt-out.
- `enabled_scenarios`: activate predefined grouped rule scenarios.
- `force_rules`: always include specific rule ids.
- `disable_rules`: never include specific rule ids.

When a project rule and a built-in rule share the same `id`, the project rule takes precedence.

## Predefined scenarios

Contextile includes predefined scenario groups, resolved from the effective catalog (built-in + project rules):

- `python-core`
- `pytest-tests`
- `fastapi-api`
- `sqlalchemy-orm`
- `docs-architecture`
- `python-backend-full`

List scenarios in a project:

```bash
contextile --root . list-rule-scenarios
```

Enable one or more scenarios:

```bash
contextile --root . apply-rule-scenario --scenario python-core
contextile --root . apply-rule-scenario --scenario pytest-tests --scenario sqlalchemy-orm
```

Replace current enabled scenarios:

```bash
contextile --root . apply-rule-scenario --scenario python-backend-full --replace
```

## Profile and dependency detection

`contextile detect-rules` detects profiles from project signals:

- dependencies in `pyproject.toml` and `requirements*.txt`;
- directory presence (`tests/`, `docs/`);
- common files (`alembic.ini`).

Use `contextile detect-rules --write` to merge detected profiles into `enable_profiles`.

## Selection flow

When selecting rules for a task, Contextile considers:

- task text;
- `--file` hints;
- `--tag` hints;
- active profiles;
- detected dependencies;
- rule metadata (`always`, `mode`, `priority`, `match_*`).

The top results are returned by `contextile select-rules` and included in `build-context` as `## Relevant Rules`.

When `build-context` includes rules, rule bodies are not token-truncated. Token budget is applied to non-rule sections only.

## CLI examples

```bash
contextile --root . validate-rules
contextile --root . detect-rules
contextile --root . detect-rules --write
contextile --root . list-rule-scenarios
contextile --root . apply-rule-scenario --scenario python-core
contextile --root . select-rules --task "Refactor SQLAlchemy models" --file src/models/order.py --limit 5
```

## Build context with rules

```bash
contextile --root . build-context \
  --task "Refactor SQLAlchemy models" \
  --file src/models/order.py \
  --tag orm \
  --rule-limit 6
```

Disable automatic rule selection when needed:

```bash
contextile --root . build-context --task "..." --no-rules
```

## Recommended workflow

For a new project:

1. `contextile init`
2. (Optional) Add project-specific rules in `.aiassistant/rules`.
3. Run `contextile detect-rules --write`.
4. Validate with `contextile validate-rules`.

For an existing project:

1. Add or move existing conventions into `.aiassistant/rules`.
2. Run `contextile detect-rules --write`.
3. Fine-tune `project-rules.json` (`force_rules`, `disable_rules`).
4. Verify selection with `contextile select-rules`.
