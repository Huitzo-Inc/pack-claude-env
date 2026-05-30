---
name: cli-non-interactive
description: >
  Drive the `huitzo` CLI programmatically — from scripts, CI, or as an AI agent.
  Reference for the global `--output json` and `--non-interactive` flags, the
  `{ok, data|error}` envelope, exit codes, authentication, and headless
  pack/dashboard/sandbox workflows (scaffold → test → sandbox → publish).
argument-hint: "[command or workflow to automate]"
---

# Huitzo CLI — Non-Interactive & Agent Reference

How to run `huitzo` without a human at the keyboard: scripted publishes, CI
gates, and AI agents that scaffold, test, sandbox, and ship packs and
dashboards. Every flag and JSON field below is grounded in the real CLI surface.

---

## Global flags — **MUST come BEFORE the subcommand**

These are options on the top-level `huitzo` callback. The subcommand parser does
not know them, so they must precede the subcommand:

```bash
# WRONG — the subcommand rejects the global flag:
huitzo pack publish --output json        # → "No such option: --output"

# RIGHT — global flags first, then subcommand:
huitzo --output json --non-interactive pack publish
```

| Flag | Effect |
|---|---|
| `--output {human,json}` | Output format (default `human`). `json` wraps every response in the `{ok, data\|error}` envelope. |
| `--non-interactive` / `-n` | Fail instead of prompting. **`--output json` already implies this.** |
| `--verbose` / `-v` | Verbose progress (stderr). |
| `--quiet` / `-q` | Suppress informational output. |
| `--config PATH` | Override the config file. |
| `--version` | Print version and exit. |

---

## The JSON envelope

With `--output json`, every command emits one of these (verified shape):

**Success**
```json
{"ok": true, "data": { ... }}
```

**Failure**
```json
{"ok": false, "error": {"type": "...", "message": "...", "code": <int>}}
```

The `data` payload differs per command — see each skill (`/sandbox`, `/publish`)
and `huitzo <cmd> --help` for the fields. **Caveat:** `pack publish` and
`dashboard publish` print human-format progress lines on stdout even in JSON
mode. For those, parse the **last** `{...}` line, not the whole stream, and lean
on the exit code.

---

## Exit codes

Check the exit code BEFORE parsing stdout. Verified codes the CLI raises:

| Code | Meaning | Retryable? |
|---|---|---|
| 0 | Success | — |
| 1 | General / unclassified error | No |
| 2 | Authentication error (token expired/invalid) | After re-auth |
| 3 | Validation error or command-not-found (bad input/manifest) | No |
| 4 | Network error (can't reach the API) | Yes (backoff) |
| 5 | Server error (5xx) | Yes (backoff) |
| 10 | Pack command runtime error | No |
| 130 | SIGINT (Ctrl+C) | — |

---

## Authentication

Token is stored at `~/.huitzo/token`. Options for headless use:

| Method | When |
|---|---|
| `huitzo login` | Local dev — interactive OAuth (opens a browser). |
| `HUITZO_AUTH_TOKEN=<jwt>` env var | CI / scripts — bypasses the persistent token file. |
| `huitzo logout` | Remove the local token (idempotent). |

Smoke-test auth + server at the start of a script:

```bash
huitzo --output json status
# exit 2 → token expired/invalid: re-auth and retry.
```

---

## Command map (what to drive non-interactively)

Group commands under `huitzo pack ...`, `huitzo dashboard ...`,
`huitzo sandbox ...`. Use `huitzo --help` and `huitzo <subcommand> --help` as
the always-current source of truth.

### `pack`
`new`, `validate` (`--strict`), `test`, `build` (`--output`/`-o`, `--format`/`-f`),
`dev`, `publish` (`--skip-capability-check`), `install`, `list`, `run`, `delete`
(`--force`/`-f`), `add-command`, `sync`, **`exec`**, **`list-commands`**,
**`describe`**. The last three resolve a running sandbox automatically — see
`/sandbox`.

### `dashboard`
`new` (`--author`), `dev`, `build`, `validate`, `publish` (`--dry-run`), `grant`
(positional `<slug> <tenant-uuid>`), `delete` (`--force`/`-f`). Stubbed (exit 1,
backend not implemented): `revoke`, `share`. See `/publish`.

### `sandbox`
`start` (`--port`, `--background`/`-b`, `--no-tls`, `--local-keys`, `--token`,
`--pidfile`), `status`, `stop`. The sidecar at `<pidfile>.json` carries
`{url, token, commands, pid}`. See `/sandbox`.

### Other useful surfaces
- `huitzo status` — auth + server health smoke test.
- `huitzo secrets set|list|remove [--pack <pack>]` — per-pack user secrets (values masked).
- `huitzo config get|set|list|path` — CLI config.
- `huitzo mcp setup docs [--write|--stdout]` — generate the MCP config that makes
  the Huitzo **docs** server searchable in Claude Code. `--write` merges it into
  `~/.claude.json`; `--stdout` prints the JSON for you to place yourself. **Only
  the `docs` service is supported today** — there is no general sandbox MCP target.

---

## End-to-end recipes

### Run a pack command headlessly (one-shot, self-managed sandbox)

```bash
set -e
huitzo --output json pack exec my-command \
  --local --args '{"input": "hello"}'
# --local starts an ephemeral sandbox, runs the command, then stops it.
```

### Run against a long-lived background sandbox

```bash
set -e
huitzo --output json --non-interactive sandbox start --background --no-tls
trap 'huitzo sandbox stop || true' EXIT

huitzo --output json pack exec my-command --args '{"input": "hello"}'
# pack exec auto-discovers {url, token} from ~/.huitzo/sandbox.json
```

### Validate + publish a private pack

```bash
set -e
cd <pack-dir>
# visibility/namespace live in huitzo.yaml — no CLI flag exists
huitzo --output json --non-interactive pack validate --strict
huitzo --output json --non-interactive pack publish
# publish prints progress lines even in JSON mode — parse the LAST {...} line.
```

### Validate + publish a private dashboard

```bash
set -e
cd <dashboard-dir>
[ -d node_modules ] || npm install
huitzo dashboard build                                   # produces dist/main.js
huitzo --output json --non-interactive dashboard validate
huitzo --output json --non-interactive dashboard publish --dry-run   # smoke
huitzo --output json --non-interactive dashboard publish
```

### Detect token expiry and re-auth

```bash
huitzo --output json status
if [ "$?" -eq 2 ]; then
  HUITZO_AUTH_TOKEN="$NEW_TOKEN" huitzo --output json status
fi
```

---

## Gotchas

1. **Global flags precede the subcommand.** `huitzo --output json pack publish`, not `huitzo pack publish --output json`.
2. **`--output json` implies `--non-interactive`** — it never prompts.
3. **`publish` prints human progress even in JSON mode.** Parse the last `{...}` line; trust the exit code.
4. **Visibility & namespace are manifest-only** — edit `huitzo.yaml` / `huitzo-dashboard.yaml`, there is no `--visibility`/`--namespace` flag.
5. **`dashboard publish` requires `dist/`** — run `huitzo dashboard build` first.
6. **`pyproject.toml` is auto-generated** from `huitzo.yaml`; never hand-edit (run `huitzo pack sync`).
7. **`--no-tls` disables auth** — localhost only.
8. **`dashboard revoke` / `dashboard share` are stubs** (exit 1) — don't depend on them yet.

## Related skills

- `/sandbox` — sandbox lifecycle + `pack exec`.
- `/publish` — pack & dashboard publishing details.
- `/dashboard-e2e` — headless dashboard mount/render/unmount verification.
