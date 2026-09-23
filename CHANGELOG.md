# Changelog

All notable changes to the Huitzo developer environment. Versions follow the
plugin manifest (`.claude-plugin/plugin.json`).

## 2.1.0 — 2026-09

### Changed
- `huitzo-dashboard-sdk` and the dashboard rules are verified against
  `@huitzo/dashboard-sdk-react` 7.0.0, `@huitzo/dashboard-sdk` 0.7.0 and
  `@huitzo/dashboard-primitives` 0.2.4.
- Token handling: `HuitzoProvider` reads the token through a per-request
  `getToken` accessor and never copies it at mount; standalone core clients
  should pass `getToken` to `HuitzoClient`. In accessor mode `auth.refresh()`
  and `auth.logout()` reject.
- `useCommand`: documents the `poll` option (`CommandPollOptions`) for commands
  that run longer than the 5 minute default budget, and that `execute()` now
  resolves with the result (`Promise<T | undefined>`, never rejects).
- `Form` template: the submit button renders inside the form after the last
  field (`.hz-form__actions`).
- `hz-form` primitive: `onSubmit` accepts `useCommand`'s `execute` as-is.
- Mock contexts and E2E examples use `sdkVersion: '7.0.0'`.
- `scripts/check_api_surface.py` now also checks the core package's exports.

### Added
- Anti-patterns: hand-rolled `client.tasks.poll` loops, and assigning
  `execute` to a `Promise<void>` slot.

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
