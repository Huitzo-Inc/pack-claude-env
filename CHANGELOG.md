# Changelog

All notable changes to the Huitzo developer environment. Versions follow the
plugin manifest (`.claude-plugin/plugin.json`).

## 2.2.0 — 2026-10

Run-view authoring: the environment now teaches and checks the pack shape
that the run page in Huitzo Hub can show (one step per pipeline stage, with
the model calls each stage made).

### Added
- `huitzo-methodology`: a "Run-view authoring" section with eight rules, a
  "Shows on the run page?" column in the composition table, new anti-pattern
  rows and a review-checklist line.
- `sdk-patterns` rule: a typed stage example with its `pipelines:` block,
  and the rule that `ctx.http` never reaches a model-provider host.
- `testing` rule: "Pattern 4 — stage chain" (load the manifest, assert the
  stage order and refs, feed each stage's `model_dump()` into the next
  stage's args model).
- `error-handling` rule: a "Pipeline stages" section (stage failures reach
  the caller as `PipelineError`; check caller input before the pipeline;
  retries and fallbacks stay inside the stage) and rule 6, no user text in
  error messages.
- `pack-reviewer`: section 8 "Run-view authoring" and a grade line (a
  multi-step command with no stages cannot score above B).
- `pack-developer`: a "Multi-step work is a pipeline of stages" section and
  two definition-of-done items for stages and the chain test.
- `/draft-spec` (skill, questionnaire, spec template), `/draft-docs` and
  `docs-writer`: a stage table (stage, command, input model, output model,
  model calls, retries / fallback, errors) for multi-step commands.
- `huitzo-sdk`, `huitzo-manifest`, `huitzo-platform`: what the run page
  shows for `ctx.commands`, `ctx.pipeline`, a manifest pipeline and the
  pipeline endpoint; stage naming; a composing-command example.
- `post-edit` hook: two non-blocking nudges for `.py` files, a
  model-provider host in a file that uses `ctx.http`, and more than one
  `ctx.commands.execute` call in one function.
- `scripts/validate_env.py`: flags a model-provider host or a command
  example returning an untyped `dict` in the environment's own text (lines
  marked ❌ are exempt). `scripts/test_hooks.sh` covers both and the new nudges.

### Changed
- Core rule 2 is now "One command is one step, or one pipeline of steps";
  core rule 3 is now "Model calls go through `ctx.llm` only, by profile".
  The count stays at twelve.
- A typed args model **and** a typed return model are the default command
  shape in `sdk-patterns`, `pack-developer`, `/add-command` and
  `docs-writer` (previously a `dict` return was the convention).
- `/add-command` validates with `huitzo pack validate --strict`, which also
  fails on a stage ref that names no command in the pack and on a stage
  whose return model does not fit the next stage's args model.

### Fixed
- `CONSTITUTION.md` quality gates named a command that does not exist; the
  gate is `huitzo pack validate --strict`.
- `huitzo-methodology` said the platform records a run's inputs. The run
  page shows status, order, timing and model-call usage, not arguments or
  output.
- `error-handling` examples that put the caller's text into
  `ValidationError.value`.

## 2.1.1 — 2026-09

### Fixed
- `dashboard-manifest` rule: `min_sdk_version` is the Hub's mount-contract
  version (`HuitzoContext`, versioned with core `@huitzo/dashboard-sdk`), not
  the `@huitzo/dashboard-sdk-react` version. Following the old wording
  (`min_sdk_version: "7.0.0"`) made the Hub refuse to mount the dashboard with
  "Incompatible Dashboard". The rule also no longer claims a `1.0.0` default.

### Added
- `dashboard-manifest` rule: "Catalog listing" section. The Hub fills the
  catalog page from `huitzo-dashboard.json` at the bundle root (ship it via
  `public/`), not from the YAML; invalid `listing` blocks are dropped
  silently; asset type, size and SVG limits. The rule now also loads when
  editing `public/huitzo-dashboard.json`.

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
