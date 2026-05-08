# Contextile

Contextile is a Python toolkit for managing, retrieving, and compacting AI project instructions, lessons learned, and contextual rules for LLM workflows.

The MVP focuses on a small local workflow:

- initialize a `.contextile/` workspace;
- store durable lessons in JSONL;
- validate lesson records;
- search relevant lessons for a task;
- build a compact Markdown context block for an LLM.

MCP support is planned as a thin optional layer on top of the core library.

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
  --max-tokens 800
```

## Validate records

```bash
contextile validate
```

## Compact records

```bash
contextile compact
```

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
