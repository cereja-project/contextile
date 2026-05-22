---
id: 42-doc-agents-md
apply: by model decision
instructions: Apply when creating or updating AGENTS.md for a repository.
profiles: [docs]
tags: [agents, documentation, onboarding, workflow]
match_files: ["AGENTS.md"]
mode: required
priority: 92
---

# AGENTS.md Authoring Rule

Use AGENTS.md as an execution guide for coding agents working in this repository.

## Required sections

- Project overview and repository root context.
- Setup commands needed to run the project locally.
- Validation commands (tests, lint, typecheck, build) with clear command lines.
- Working constraints and non-negotiable engineering rules.
- Notes about architecture boundaries and public contracts.

## Writing quality

- Keep instructions concrete, imperative, and short.
- Prefer command examples that can be executed as-is.
- Avoid generic advice without repository-specific impact.
- Do not include marketing language or non-operational content.

## Maintenance rules

- Update AGENTS.md whenever tooling, workflows, or validation steps change.
- Keep command examples aligned with the actual project environment.
- Preserve domain terminology already established by the codebase and docs.
