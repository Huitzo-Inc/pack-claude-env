# Pack Claude Environment — AI Development Instructions

> **Single source of truth for AI tools working in this repository.**
> This is a submodule of the [Huitzo monorepo](https://github.com/Huitzo-Inc/huitzo).

## What This Repository Is

A pre-configured [Claude Code](https://docs.anthropic.com/en/docs/claude-code) environment for developing Intelligence Packs and Dashboards on the Huitzo platform. It provides SDK-aware skills, specialized agents, coding rules, and project instructions — for both Python pack commands and React dashboard micro-frontends.

This repository is **not** a runnable application. It is a seed environment that gets copied into new Huitzo projects by the CLI (`huitzo pack new`, `huitzo dashboard new`).

## Repository Structure

```
claude/
├── CLAUDE.md           # Main AI instructions (this file's sibling)
├── settings.json       # Claude Code settings
├── agents/             # Specialized agent definitions
│   ├── pack-developer.md
│   ├── pack-reviewer.md
│   ├── dashboard-developer.md
│   ├── dashboard-reviewer.md
│   ├── docs-writer.md
│   └── spec-architect.md
├── rules/              # Path-scoped coding rules
│   ├── sdk-patterns.md
│   ├── react-patterns.md
│   ├── dashboard-design.md
│   ├── dashboard-manifest.md
│   ├── hub-contract.md
│   ├── error-handling.md
│   ├── documentation.md
│   ├── testing.md
│   └── traceability.md
├── skills/             # Reusable skill definitions
│   ├── add-command/
│   ├── draft-spec/
│   ├── draft-docs/
│   ├── scaffold-dashboard/
│   ├── test-pack/
│   ├── test-dashboard/
│   ├── validate-pack/
│   ├── validate-dashboard/
│   ├── lint-and-fix/
│   ├── publish/
│   ├── sandbox/
│   ├── dashboard-dev/
│   ├── dashboard-e2e/
│   └── cli-non-interactive/
profiles/               # Profile definitions (pack-only, dashboard-only, full-stack)
scripts/                # Utility scripts
CONSTITUTION.md         # Pack developer constitution (simplified subset of Huitzo Constitution)
```

## Profiles

Three profiles control which agents, rules, and skills are active:

| Profile | Use Case | Includes |
|---------|----------|----------|
| **pack-only** | Python Intelligence Pack development | Pack agents + skills + Python rules |
| **dashboard-only** | React dashboard development | Dashboard agents + skills + React rules |
| **full-stack** | Pack + Dashboard together (default) | Everything |

Profile definitions are in `profiles/`. The `claude/CLAUDE.md` is the same for all profiles — path-scoped rules ensure only relevant rules load based on the files being edited.

## Docs-First Workflow

This environment enforces a **docs-first** workflow. The order matters — docs are the source of truth, code implements them:

1. **Spec** (`/draft-spec my-project`) — Structured requirements gathering (7 phases)
2. **Document** (`/draft-docs analyze-text`) — Write command/component documentation
3. **Implement** (`/add-command analyze-text` or `/scaffold-dashboard AnalyzeView`) — Code implements docs
4. **Test** (`/test-pack` or `/test-dashboard`) — Validate documented behavior
5. **Validate** (`/validate-pack` or `/validate-dashboard`) — Structure and quality checks
6. **Lint** (`/lint-and-fix`) — Auto-fix code style

## Quality Gates (from CONSTITUTION.md)

Before publishing any pack:

```bash
source venv/bin/activate
pytest -v                  # Own What You Ship
ruff check .               # Simplicity
ruff format --check .      # Simplicity
mypy --strict src/         # Simplicity through types
huitzo validate            # Manifest + structure check
```

All gates must pass. No exceptions.

## What NOT to Do

- **Don't modify `claude/CLAUDE.md` directly in this repo** — it is the seed that gets copied into projects. Changes here affect every new project. If a rule is project-specific, it belongs in the project's own `.claude/` after seeding.
- **Don't add project-specific agents or skills here** — this is the generic seed. Project-specific additions go in the project's `.claude/` directory.
- **Don't remove the docs-first workflow** — the spec→docs→implement→test→validate→lint order is the contract between the environment and the CLI's validation. Skipping steps produces artifacts that fail `huitzo validate`.
- **Don't add runtime dependencies** — this environment is configuration, not code. It should not require `pip install` or `npm install` to function.
