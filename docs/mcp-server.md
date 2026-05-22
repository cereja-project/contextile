# MCP Server

Contextile provides an MCP server as a thin layer over the core library APIs.

## Install

Install MCP extras:

```bash
pip install -e ".[mcp]"
```

If MCP dependencies are missing, `contextile mcp-server` returns a clear error.

## Run server

Using the main CLI:

```bash
contextile --root . mcp-server
```

Using the dedicated entrypoint:

```bash
contextile-mcp --root .
```

Run with streamable HTTP transport:

```bash
contextile --root . mcp-server --transport streamable-http
```

Options:

- `--root`: default project root used by tools.
- `--name`: server name shown to MCP clients.
- `--transport`: `stdio` (default) or `streamable-http`.

## Exposed MCP tools

### `build_context_tool`

Build compact context for a task.

Inputs:

- `task` (required)
- `root`
- `files`
- `tags`
- `max_tokens`
  - budget for non-rule sections; selected rules are always included in full.
- `lesson_limit`
- `rule_limit`
- `include_rules`

Output fields:

- `context`
- `estimated_tokens`
- `root`

### `build_agents_md_tool`

Build an AGENTS.md draft using detected profiles/dependencies, selected rules, lessons, and project instructions.

Inputs:

- `root`
- `task`
- `files`
- `tags`
- `rule_limit`
- `lesson_limit`
- `output_path` (default: `AGENTS.md`)
- `write` (default: `true`)
- `overwrite` (default: `false`)

Output fields:

- `root`
- `path`
- `written`
- `estimated_tokens`
- `content`

### `add_lesson_tool`

Persist a lesson to `.contextile/lessons.jsonl`.

Inputs:

- `id` (required)
- `when` (required)
- `do` (required)
- `avoid` (required)
- `root`
- `scope`
- `tags`
- `why`
- `updated_at`

Output fields:

- `path`
- `lesson`

### `search_lessons_tool`

Search lessons in `.contextile/lessons.jsonl`.

Inputs:

- `query` (required)
- `root`
- `tags`
- `files`
- `limit`

Output fields:

- `count`
- `results[]` with `id`, `score`, `when`, `do`, `avoid`, `scope`, `tags`, `reasons`

### `select_rules_tool`

Select relevant rules from the effective catalog (built-in defaults + `.aiassistant/rules` overrides).

Inputs:

- `task` (required)
- `root`
- `files`
- `tags`
- `limit`

Output fields:

- `count`
- `results[]` with `id`, `path`, `mode`, `priority`, `profiles`, `tags`, `instructions`, `score`, `reasons`

### `detect_rules_tool`

Detect active profiles and dependencies for rule selection.

Input:

- `root`

Output fields:

- `dependencies`
- `detected_profiles`
- `active_profiles`
- `settings`

### `validate_rules_tool`

Validate rule files in the effective catalog (built-in defaults + `.aiassistant/rules`).

Input:

- `root`

Output fields:

- `valid`
- `error_count`
- `errors`

### `list_rule_scenarios_tool`

List predefined scenario groups mapped to the effective rule catalog.

Input:

- `root`

Output fields:

- `count`
- `scenarios[]` with `id`, `description`, `profiles`, `rule_count`, `rule_ids`

### `apply_rule_scenario_tool`

Enable scenarios in `.contextile/project-rules.json`.

Inputs:

- `root`
- `scenarios` (list of scenario ids)
- `replace` (bool)

Output fields:

- `path`
- `enabled_scenarios`

## Client wiring (generic)

Your MCP client configuration should launch one of:

- `contextile-mcp --root /path/to/project`
- `python -m contextile.mcp_server --root /path/to/project`

Use `stdio` unless your client requires HTTP transport.

## Operational notes

- Keep `--root` pointed to the target project. `.aiassistant/rules` is optional.
- For multi-project usage, register one server entry per project root.
- Validate rule files before usage: `contextile --root . validate-rules`.
