# Contextile MVP Scope

## Goal

Create a dependency-free Python library and CLI that can manage durable AI project lessons and build a compact context block for LLM workflows.

## In scope

- `.contextile/` workspace initialization.
- JSONL lesson storage.
- Lesson validation.
- Keyword/tag/file-hint retrieval.
- Markdown context rendering.
- Approximate token budget control.
- Basic unit tests using `unittest`.

## Out of scope for MVP

- Embeddings.
- SQLite/FTS index.
- MCP server.
- Git hooks.
- Automatic summarization.
- Background indexing.
- Remote sync.

## MVP commands

```bash
contextile init
contextile add-lesson
contextile search "api validation"
contextile build-context --task "Refactor API validation for reports"
contextile validate
contextile compact
```

## Next iteration

1. Add `update-lesson` and `remove-lesson`.
2. Add better ranking with SQLite FTS.
3. Add a token counter adapter.
4. Add `contextile[mcp]` server exposing `search_lessons` and `build_context`.
5. Add integration tests for CLI commands.
