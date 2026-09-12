# Huitzo developer core (always on)

You are working in a project that builds on the Huitzo platform: Intelligence Packs (Python
commands run by the platform) and/or Dashboards (React micro-frontends loaded by Huitzo Hub).
This rule is the only always-on context; everything else loads on demand.

Verified against: `huitzo-sdk` 1.7.0 · `@huitzo/dashboard-sdk` 0.6.0 ·
`@huitzo/dashboard-sdk-react` 5.1.1 · Claude Code 2.1.269 (2026-09). The installed package always
wins over this text: when in doubt, read it (see "Get more context").

## Detect the project

| Marker | Kind | Work from |
|---|---|---|
| `huitzo.yaml` in the root | Pack | root (`src/<module>/commands/`, `tests/`, `docs/commands/`) |
| `huitzo-dashboard.yaml` in the root | Dashboard | root (`src/main.tsx`, `src/App.tsx`, `docs/components|pages/`) |
| `pack/huitzo.yaml` and/or `dashboard/huitzo-dashboard.yaml` | Project | run CLI commands *inside* `pack/` or `dashboard/` |
| `packs/*/huitzo.yaml` + `dashboards/*/huitzo-dashboard.yaml` | Application | each pack/dashboard is standalone; shared `docs/` at the root |

## The loop (docs first, always)

`/draft-spec` → `/draft-docs <verb-noun>` → `/add-command <verb-noun>` or `/scaffold-dashboard <Name>`
→ `/test-pack` or `/test-dashboard` → `/validate-pack` or `/validate-dashboard` → `/lint-and-fix`
→ `/sandbox` (run it for real) → `/publish`. When installed as a plugin the skills are prefixed:
`/huitzo:add-command`. Code implements a documented contract; the doc comes first.

## Twelve rules that are never optional

1. **Deterministic Python owns decisions; the model augments.** Compute, validate, gate and
   decide in code; ask `ctx.llm` for judgement, extraction or prose, then verify its output.
2. **One command, one responsibility.** `verb-noun` names, 30–750 lines, Pydantic `BaseModel`
   args with `Field(description=...)`, returns a `dict` or a Pydantic model.
3. **Never name a model.** `ctx.llm.complete(prompt, profile="default")` — there is no `model=`
   argument; profiles are configured by the platform.
4. **Everything through `ctx`.** `ctx.http` (HTTPS, manifest domain allowlist), `ctx.storage`
   (`save`/`get`, scope `user` or `tenant`), `ctx.files`, `ctx.secrets` (**async**: `await
   ctx.secrets.require("KEY")`), `ctx.log` (sync). Never raw `requests`, `open()`, `print()`.
5. **Manifest schema v2 with a policy card.** `huitzo.yaml` needs `schema_version: 2`, `pack:`,
   a `policy:` card whose `allowed_actions` ⊇ `permissions:`, and a backing `services:` block for
   every permission token. Unknown keys fail validation (there is no `enabled:` field).
6. **Queues are `fast | medium | long`** (default `medium`). `default` and `auto` do not exist.
7. **Errors are typed.** Raise `ValidationError`, `CommandError`, `ExternalAPIError`,
   `SecretsError` from `huitzo_sdk.errors`; timeouts are `CommandTimeoutError`. Never `except
   Exception`, never log a secret value.
8. **Traceability header on every source file**, pointing at *this project's* docs:
   Python docstring `Implements:\n    - docs/commands/<name>.md`; TypeScript JSDoc
   `@implements docs/components/<Name>.md`.
9. **Tests prove your logic, not the platform.** Pure helpers first; commands with a mocked
   `Context` (`AsyncMock` for every service except `ctx.log`); manifest loads; then sandbox.
10. **Dashboards consume decisions, they never make them.** `mount`/`unmount` from `src/main.tsx`,
    `HuitzoProvider` + `<div className="huitzo-dashboard">`, all data via `useCommand`
    (status can be `polling`), design tokens (`var(--color-*)`) and `hz-*` primitives only — no hex
    colours, no UI kits, no `dangerouslySetInnerHTML`, no global element selectors.
11. **Quality gates before publish.** Pack: `pytest -v`, `ruff check .`, `ruff format --check .`,
    `mypy --strict src/`, `huitzo pack validate --strict`. Dashboard: `npm run typecheck`, tests,
    `npm run build`, `huitzo dashboard validate`. The version must increase to publish.
12. **Least privilege everywhere.** Declare only the permissions, domains and secrets you use; API
    keys for MCP clients get the `commands:execute` scope only; secrets come from `ctx.secrets`
    or the environment, never from source.

## Services at a glance

| `ctx.` | Purpose | Note |
|---|---|---|
| `llm` | `complete` / `chat` / `stream`, structured output via `schema=` | `profile=`, never `model=` |
| `http` | `get` / `post` / `put` / `delete` | HTTPS only; domains from the manifest |
| `storage` | `save` / `get` / `delete` / `exists` / `list` / `query` (+ `_many`) | `tenant` scope is shared across packs |
| `files` | `read` / `write` / `list` / `exists` / `get_url` (+ Excel/CSV/JSON readers) | user file storage |
| `secrets` | `require` / `get` / `exists` | all async |
| `email`, `telegram`, `tts`, `ssh`, `db` | platform integrations | each needs a `services:` declaration |
| `commands` | `execute(name, args)` — call another command in this pack | inline, depth-limited |
| `log` | `info` / `warning` / `error` | sync; kwargs are scrubbed |

## Get more context (in this order of trust)

1. **The installed package.** `python -c "import inspect, huitzo_sdk.context as c; print(inspect.getsource(c.Context))"`;
   `node_modules/@huitzo/dashboard-sdk-react/dist/index.d.ts` and `dist/styles/tokens.css`.
2. **Reference skills in this environment** (load on demand, ask for them by name):
   `/huitzo-sdk` (Context, decorator, errors, testing) · `/huitzo-manifest` (`huitzo.yaml` schema,
   policy card, permissions) · `/huitzo-dashboard-sdk` (hooks, templates, tokens, primitives) ·
   `/cli-non-interactive` (every `huitzo` command, JSON envelope, exit codes) · `/huitzo-platform`
   (REST API, API keys, hosted MCP, webhooks) · `/huitzo-methodology` (design, testing, shipping).
3. **This project's docs via MCP.** If `.mcp.json` declares `pack-docs`, use `search_documentation`,
   `get_table_of_contents`, `get_document`, `navigate_to`, `search_by_tags`, `get_all_tags` before
   writing a new doc. Run `/huitzo-init` to wire it.
4. **Public documentation** — `https://docs.huitzo.ai/docs/` (fetch the page when a detail matters):
   `sdk/overview`, `sdk/commands`, `sdk/context`, `sdk/integrations`, `sdk/storage`,
   `sdk/error-handling`, `sdk/mcp`, `packs/manifest`, `cli/reference`, `cli/dashboards`,
   `dashboards/sdk`, `dashboards/manifest`, `dashboards/publishing`, `api/rest`,
   `guides/connect-claude-mcp`, `guides/mcp-pack-integration`, `guides/external-integrations`,
   `reference/secrets`, `reference/configuration`, `architecture/security`,
   `concepts/building-methodology`, `guides/quickstart/first-pack`.
5. **The CLI itself.** `huitzo --help`, `huitzo <group> <cmd> --help`, and `--output json` for
   machine-readable results. Install: `curl -sSf https://install.huitzo.ai | sh` or
   `brew install huitzo/tap/huitzo`.
6. **Worked examples.** https://github.com/Huitzo-Inc/build-with-huitzo — runnable labs from a
   hello pack to full-stack, all testable offline.

## What this environment does automatically

Hooks (only inside Huitzo projects): print project context at session start, block writes that
contain credential-shaped strings, warn about missing traceability headers, hex colours and
`model=` after edits, and summarise unheadered files when you stop. Agents: `pack-developer`,
`pack-reviewer`, `dashboard-developer`, `dashboard-reviewer`, `docs-writer`, `spec-architect`.
