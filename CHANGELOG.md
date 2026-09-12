# Changelog

All notable changes to the Huitzo developer environment. Versions follow the
plugin manifest (`.claude-plugin/plugin.json`).

## 2.0.0 — 2026-09

### Added
- Installable as a Claude Code plugin: this repository is now a marketplace
  (`/plugin marketplace add Huitzo-Inc/pack-claude-env`) that ships the
  `huitzo` plugin (`/plugin install huitzo@huitzo`).
- Six on-demand reference skills verified against the published packages:
  `huitzo-sdk`, `huitzo-manifest`, `huitzo-dashboard-sdk`, `cli-non-interactive`
  (rewritten), `huitzo-platform`, `huitzo-methodology`.
- `huitzo-init` skill: bootstraps or repairs a project (rules, managed
  `CLAUDE.md`/`AGENTS.md` blocks, `CONSTITUTION.md`, project-docs MCP wiring)
  without overwriting existing files.
- Always-on core rule `claude/rules/00-huitzo-core.md`; a `pack-manifest` rule.
- Hooks: session context, secrets scan (blocking), traceability/design nudges,
  pre-stop summary. Hooks only act inside Huitzo projects.
- `claude/hooks/docs-mcp.sh` launcher for the project docs MCP server.
- Validation: `scripts/validate_env.py` (structure, frontmatter, information
  boundary, stale API tokens), `scripts/check_api_surface.py` (asserts every
  documented API fact against `huitzo-sdk` and `@huitzo/dashboard-sdk-react`),
  `scripts/check_links.py`, `scripts/simulate_seed.py`, `scripts/test_hooks.sh`,
  and a GitHub Actions workflow running all of them plus `claude plugin validate`.

### Changed
- Every skill, rule and agent rewritten against `huitzo-sdk` 1.7.0,
  `@huitzo/dashboard-sdk` 0.6.0 and `@huitzo/dashboard-sdk-react` 5.1.1
  (manifest schema v2 with the required policy card, `profile=` for
  `ctx.llm`, async `ctx.secrets`, `CommandTimeoutError`/`PackPermissionError`,
  `useCommand` polling status, Templates, exact `hz-*` primitives).
- Agents carry `name`/`description`/`tools` frontmatter; developer agents
  preload one reference skill each; reviewers are read-only.
- `settings.json` no longer declares MCP servers (Claude Code reads MCP
  configuration from `.mcp.json`); it now carries hooks and a permission
  allowlist for the quality-gate commands.
- Profiles updated for the new file set.

### Removed
- Stale API claims (`ctx.storage.set`, `ctx.telegram.send_message`,
  `model=` on `ctx.llm`, `enabled:` in `huitzo.yaml`, `hz-arch`, 4.1.x hooks).
- Links to private repositories.

## 1.x

Seed environment copied by `huitzo pack new` / `huitzo dashboard new`
(skills, agents, rules, CONSTITUTION.md, legal headers).
