# Huitzo project — Claude Code instructions

This project builds on the Huitzo platform (Intelligence Packs in Python and/or Dashboards in
React). The Huitzo developer environment lives in `.claude/`:

- `.claude/rules/00-huitzo-core.md` — the always-on core: project detection, the docs-first loop,
  the twelve non-negotiable rules, the `ctx` services table, and where to get more context.
  **Read it first.** Other rules load automatically when you edit matching files.
- `.claude/skills/` — workflow skills (`/draft-spec`, `/draft-docs`, `/add-command`,
  `/scaffold-dashboard`, `/test-pack`, `/test-dashboard`, `/validate-pack`, `/validate-dashboard`,
  `/lint-and-fix`, `/sandbox`, `/publish`, `/dashboard-dev`, `/dashboard-e2e`, `/huitzo-init`) and
  reference skills (`/huitzo-sdk`, `/huitzo-manifest`, `/huitzo-dashboard-sdk`,
  `/cli-non-interactive`, `/huitzo-platform`, `/huitzo-methodology`).
- `.claude/agents/` — `pack-developer`, `pack-reviewer`, `dashboard-developer`,
  `dashboard-reviewer`, `docs-writer`, `spec-architect`.
- `.claude/hooks/` — session context, secrets scan, traceability nudges (active only in Huitzo
  projects) and `docs-mcp.sh`, the launcher for this project's documentation MCP server.

Project-specific instructions belong below this line or in `CLAUDE.local.md`; the environment
files above are replaced when the environment is updated. Run `/huitzo-init` after cloning to
wire the project docs MCP server and refresh the managed blocks.

Public documentation: https://docs.huitzo.ai/docs/
