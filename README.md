# Contextile

Contextile is a Python toolkit for managing, retrieving, and compacting AI project instructions, lessons learned, and contextual rules for LLM workflows.

Documentation guides:

- [Rules selection](docs/rules-selection.md)
- [MCP server](docs/mcp-server.md)

The MVP focuses on a small local workflow:

- initialize a `.contextile/` workspace;
- store durable lessons in JSONL;
- validate lesson records;
- search relevant lessons for a task;
- build a compact Markdown context block for an LLM;
- run a thin MCP server layer on top of the same core functions.

## Install locally

```bash
pip install -e .
```

## Initialize a project

```bash
contextile init
```

This creates:

```text
.contextile/
  config.json
  lessons.jsonl
  project-rules.json
  instructions/
    project-context.md
    architecture-rules.md
    code-standards.md
    validation.md
```

## Add a lesson

```bash
contextile add-lesson \
  --id preserve-domain-terms \
  --when "Editing existing domain terms in code, docs, routes, schemas, enums, or API contracts." \
  --do "Preserve domain terms exactly as used in the project." \
  --avoid "Do not translate established domain terms." \
  --scope "Code, docs, API, DB, routes, enums, UI." \
  --tags domain,terminology,api,routes,enums
```

## Search lessons

```bash
contextile search "api validation reports" --limit 5
```

## Build compact context

```bash
contextile build-context \
  --task "Refactor API validation for reports" \
  --file src/schemas/par/relatorio.py \
  --tag api \
  --tag validation \
  --rule-limit 6 \
  --max-tokens 800
```

By default, `build-context` selects relevant rules from:

- bundled default rule catalog (ships with Contextile);
- optional project overrides/extensions in `.aiassistant/rules`.

Selection uses:

- project profiles from `.contextile/project-rules.json`;
- detected stack/dependencies (`pyproject.toml`, `requirements*.txt`, directories);
- task text, file hints, and tags.

When rules are selected, they are always included in full (not token-truncated). `--max-tokens` applies to non-rule sections.

Use `--no-rules` to disable rule selection for a call.

## Validate records

```bash
contextile validate
```

## Compact records

```bash
contextile compact
```

## Detect and manage rule profiles

```bash
contextile detect-rules
contextile detect-rules --write
contextile list-rule-scenarios
contextile apply-rule-scenario --scenario python-core
contextile apply-rule-scenario --scenario fastapi-api
contextile select-rules --task "add sqlalchemy pagination" --file src/repositories/orders.py
contextile validate-rules
```

`detect-rules --write` updates `.contextile/project-rules.json` (`enable_profiles`) so existing projects can adopt rule selection quickly.
`apply-rule-scenario` updates `enabled_scenarios` using predefined scenario groups from the bundled catalog plus any project rules.

## Run MCP server

Install MCP extra:

```bash
pip install -e ".[mcp]"
```

Run over stdio (default):

```bash
contextile mcp-server --root .
```

or:

```bash
contextile-mcp --root .
```

Run over HTTP transport:

```bash
contextile mcp-server --root . --transport streamable-http
```

Available MCP tools:

- `build_context_tool`
- `build_agents_md_tool`
- `add_lesson_tool`
- `search_lessons_tool`
- `select_rules_tool`
- `detect_rules_tool`
- `validate_rules_tool`
- `list_rule_scenarios_tool`
- `apply_rule_scenario_tool`

## Lesson JSONL schema

Each line in `.contextile/lessons.jsonl` is one lesson:

```json
{"id":"preserve-domain-terms","when":"Editing existing domain terms.","do":"Preserve terms exactly as used.","avoid":"Do not translate established terms.","scope":"Code, docs, API, DB, routes, enums, UI.","tags":["domain","terms","api"]}
```

Required fields:

- `id`
- `when`
- `do`
- `avoid`

Recommended fields:

- `scope`
- `tags`
- `why`
- `updated_at`
