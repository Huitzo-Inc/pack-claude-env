---
name: cli-non-interactive
description: >-
  Huitzo CLI reference: every developer-facing `huitzo` command, `--output json`
  envelope, exit codes, non-interactive workflows. Use when running or scripting
  the CLI. Not for SDK code → huitzo-sdk.
---

> Verified against the Huitzo CLI surface as of 2026-09 (run `huitzo --version`; flags may evolve — `huitzo <cmd> --help` is authoritative).

Reference for driving `huitzo` from scripts, CI, or an AI agent — no human at
the keyboard, output you can parse.

## Install

```bash
curl -sSf https://raw.githubusercontent.com/Huitzo-Inc/huitzo-launcher/main/install.sh | sh     # Linux / WSL
brew install Huitzo-Inc/tap/huitzo               # macOS
huitzo --version                             # verify
```

The native launcher manages its own Python environment and auto-updates. A
pack depends on `huitzo-sdk` (PyPI) at runtime — install the CLI, not the SDK,
to get `huitzo` on `PATH`. See [Installation](https://docs.huitzo.ai/docs/guides/quickstart/installation).

## Global flags — MUST come before the subcommand

Global options belong to the root `huitzo` command, not the subcommand parser:

```bash
huitzo pack publish --output json      # ❌ subcommand rejects the unknown flag
huitzo --output json pack publish      # ✅ global flags first
```

| Flag | Effect |
|---|---|
| `--output human\|json` | Output format (default `human`). `json` wraps every response in the envelope below. |
| `-n`, `--non-interactive` | Fail instead of prompting. **Implied by `--output json`.** |
| `-v`, `--verbose` | Verbose progress. |
| `-q`, `--quiet` | Suppress informational output. |
| `--config PATH` | Override the config file. |
| `--version` | Print version and exit. |

## JSON envelope

**Success** (stdout):
```json
{"ok": true, "data": { ... }}
```

**Error** (stderr):
```json
{"ok": false, "error": {"type": "...", "message": "...", "code": <int>}}
```

Several commands additionally offer their own per-command `--json` flag
(`pack new --json`, `pack validate --json`, `pack build --json`) that
**suppresses** the global envelope and prints exactly one hand-shaped stable
object instead — documented per command below. `pack publish` and
`dashboard publish` have no such flag and print human progress lines even
under `--output json`; parse the **last** `{...}` line and trust the exit code.

## Exit codes

| Code | Meaning | Retry? |
|---|---|---|
| 0 | OK | — |
| 1 | General / unclassified error | No |
| 2 | Auth error (missing/expired session) | After `huitzo login` |
| 3 | Validation error (bad input, manifest, or command-not-found) | No |
| 4 | Network error (can't reach the API) | Yes (backoff) |
| 5 | Server error (5xx) | Yes (backoff) |
| 10 | Command execution error (sandbox/pack command failed) | No |
| 130 | Interrupted (Ctrl+C) | — |

Check the exit code before parsing stdout — a `--json` command that fails
still emits an envelope, but the field shape can differ from the success case.

## Auth

```bash
huitzo login [--url URL] [--email E] [--tenant SLUG]
huitzo logout
huitzo status [--output json]
```

The password is **never** a flag. Non-interactively, export `HUITZO_PASSWORD`
before calling `login`; interactively it falls back to a hidden prompt.

```bash
export HUITZO_PASSWORD="$(pass show huitzo/dev)"
huitzo --output json login --email dev@acme.com
unset HUITZO_PASSWORD
```

For a stored-session/token env var for CI, see `huitzo login --help` — not
independently confirmed here. `huitzo status` is the smoke test: exit `2`
means re-authenticate.

## Command tree

### `huitzo pack`

| Command | Key options |
|---|---|
| `new [NAME]` | `--namespace`, `--author`, `--email`, `--description`, `--no-input` (never prompt), `--json` → `{"ok","pack","namespace","path"}` |
| `validate [--path DIR]` | `--strict`, `--check-capabilities/--no-check-capabilities`, `--json` → `{"ok","errors":[...],"warnings":[...]}` |
| `test` | `--coverage`, `-v/--verbose`, `-p/--parallel`, `-k/--filter PATTERN` |
| `build` | `-o/--output DIR`, `-f/--format wheel\|sdist`, `--json` → `{"ok","wheel":"<path\|null>","error":"<short\|null>"}` |
| `dev` | `--docs`, `--port` (default `8080`), `--repl/--no-repl`, `--no-tls`, `--local-keys`, `--log-level`, `--skip-update-check` |
| `publish` | `--skip-capability-check`, `--no-build` |
| `install <pkg.whl>` | `--sha256 DIGEST`, `-y/--yes` — **local `.whl` only**; registry-by-name install is not implemented |
| `list [--local]` | remote by default; `--local` lists installed via entry points |
| `run <@scope/pack/cmd>` / `huitzo run` | `--args '<json>'`, `--raw`; extra `--flags` pass through as pydantic args |
| `delete <name>` | `-f/--force` |
| `add-command [NAME]` | `-d/--description`, `-p/--permissions "a,b"`, `-t/--timeout`, `-q/--queue`, `-r/--retries`, `--pydantic/--no-pydantic`, `--path` |
| `sync [--path DIR]` | regenerate `pyproject.toml` from `huitzo.yaml` |
| `exec <command> [--args '<json>']` | `--sandbox-url`, `--sandbox-token`, `--local` (ephemeral), `--port`, `--no-tls`, `--local-keys`, `--pidfile`, `--file PATH` (repeatable) |
| `list-commands` / `describe <command>` | same sandbox-resolution flags as `exec` |

❌ `huitzo pack add-command --queue default` — the CLI accepts `default` as a
value but the SDK rejects it at runtime. Always pass `fast`, `medium`, or
`long` explicitly.

### `huitzo dashboard`

| Command | Key options |
|---|---|
| `new [NAME]` | `--author`, `--namespace`, `--path` |
| `dev` | runs the dashboard's own dev server |
| `build` | produces the manifest's declared entry bundle |
| `validate` | checks the manifest + build output + mount/unmount exports |
| `publish` | `--dry-run` (bundle + report, upload nothing) |
| `grant <name> <tenant_uuid>` | `--scope SCOPE`; both args positional |
| `delete <name>` | `-f/--force` |

### `huitzo sandbox` — see the `/sandbox` skill for the full lifecycle

`start [--port 8080] [--no-tls] [-b/--background] [--pidfile PATH] [--local-keys] [--token T]`,
`stop [--pidfile PATH]`, `status [--pidfile PATH]`.

### `huitzo secrets` — local-only developer store (this machine, not the deployed pack)

`set <name> [--value V] [--pack default]` (else `HUITZO_SECRET_VALUE` env, else
hidden prompt), `list [--pack default]` (names only — every value renders
`********`), `remove <name> [--pack default]`. There is no `get`/`show`/
`--reveal` for this store.

### `huitzo config`

`get <key> [--reveal]`, `set <key> [value] [--scope user|project]` (sensitive
keys always hidden-prompt), `unset <key> [--scope user|project]`, `list`,
`path [--scope user|project]`.

### `huitzo mcp`

`setup docs [-w/--write] [--stdout]` mints a scoped `sk-huitzo-*` API key and
builds a Streamable HTTP MCP config for a Huitzo-hosted **docs** server. No
flag prints the config + a revoke URL for you to add by hand; `--stdout`
prints just the JSON for piping; `--write` merges the entry into your Claude
Code MCP config (`~/.claude.json`, user scope — reachable from every project).
`docs` is currently the only supported service.

### `huitzo project`

`init <name> [--with-dashboard|--no-dashboard]` scaffolds a Project directory
holding a Pack and (optionally) a Dashboard. `add-pack` / `add-dashboard` run
from the Project root to backfill the missing half.

### `huitzo primitives`

`list`, `add <name...> [--out-dir DIR] [--skip-existing/--overwrite]`, `diff`,
`sync [-y/--yes]` — the `hz-*` dashboard primitive copy-in registry.

### `huitzo account`

`mode` (show current account mode), `developer-mode [--org-name N --org-slug S]`
(required before publishing).

### Housekeeping (brief)

`huitzo update [--to VER] [--channel NAME] [--dry-run] [--force]`,
`huitzo rollback [--to GEN_ID] [--force]`, `huitzo pin <component> <version>`,
`huitzo unpin <component>`, `huitzo lock` (show desired state). These manage
the launcher-installed CLI itself, not a pack or dashboard.

**Deliberately not covered here** (out of scope for this skill): `pack plan`,
`pack evaluate`, `runner`, `ext`, `license`, `tenant`, `branding`,
`integrations secrets`. Run `huitzo <group> --help` if you need one of these.

## Agent workflow: pack, non-interactively

```bash
set -e
huitzo --output json pack new my-pack --no-input --namespace acme
cd my-pack

huitzo --output json pack add-command analyze -d "Analyze input" -p "" -q fast
huitzo --output json pack test | jq -e '.ok'
huitzo --output json pack validate --strict | jq -e '.ok'
huitzo --output json pack build | jq -r '.wheel'
huitzo --output json --non-interactive pack publish
# publish prints human progress even in JSON mode — parse the LAST {...} line:
# huitzo --output json pack publish | tail -n1 | jq -e '.ok'
```

Run a command headlessly against a throwaway sandbox in one shot:

```bash
huitzo --output json pack exec analyze --local --args '{"input":"hello"}'
```

## Agent workflow: dashboard, non-interactively

```bash
set -e
huitzo --output json dashboard new my-dash --author "Acme"
cd my-dash
npm install
huitzo dashboard build
huitzo --output json dashboard validate | jq -e '.ok'
huitzo --output json dashboard publish --dry-run | jq -e '.ok'
huitzo --output json dashboard publish
```

Visibility and namespace are manifest fields (`huitzo.yaml` /
`huitzo-dashboard.yaml`), never CLI flags — edit the manifest before
publishing if you need something other than the default.

## Troubleshooting

| Symptom | Exit | Fix |
|---|---|---|
| Auth error | `2` | `huitzo login` (or refresh whatever CI uses for credentials) |
| Manifest/input rejected | `3` | Read `.error.message` / `.errors[]`; fix and re-run `pack validate --strict` |
| Can't reach the API | `4` | Check connectivity/DNS; retry with backoff |
| 5xx from the backend | `5` | Retry with backoff; not your input |

## Anti-patterns

| ❌ Wrong | ✅ Right |
|---|---|
| ❌ `huitzo pack publish --output json` | `huitzo --output json pack publish` |
| ❌ Parsing the human-readable table output of `pack list` | `huitzo --output json pack list` and parse `.data` |
| ❌ `huitzo pack add-command --queue default` | `--queue fast\|medium\|long` |
| ❌ `huitzo login` with `--password` or a literal on the command line | `HUITZO_PASSWORD` env var, or the hidden prompt |
| ❌ Assuming `huitzo pack install my-pack` installs from a registry | Build (`pack build`) and install the local `.whl` by path |
| ❌ Treating `huitzo secrets` as where a deployed pack's user secrets live | It's a local dev store only; the pack's `ctx.secrets` never sees it |

## Read more

- https://docs.huitzo.ai/docs/cli/overview
- https://docs.huitzo.ai/docs/cli/reference
- https://docs.huitzo.ai/docs/cli/dashboards
- https://docs.huitzo.ai/docs/guides/quickstart/installation
