---
name: sandbox
description: Run a pack against the local Huitzo sandbox (start, status, exec, stop)
argument-hint: "[start|status|stop|exec <command>]"
disable-model-invocation: true
---

# /sandbox

Drive the local Huitzo sandbox so you can run this pack's commands the way the
Hub runtime will, before publishing. The sandbox loads your pack's source as an
editable install and serves its commands over a local HTTP endpoint.

This is the **sandbox → preview** rung of the loop: scaffold → develop → test →
**sandbox** → publish.

## When to use

- Run a real command end-to-end (with args) against your packaged pack.
- Verify a command's args schema before wiring a dashboard page to it.
- Drive a dashboard's `useCommand` hooks against live local command output
  instead of mocks (`npm run dev` proxies to the running sandbox).

## Prerequisites

- A valid pack — `huitzo.yaml` in the current directory. Run `/validate-pack` first.
- The CLI installed and on `PATH` (`huitzo --version`).

## Lifecycle (real CLI surface)

All flags below are exactly what `huitzo sandbox` accepts — do not invent others.

### Start

```bash
# Foreground (blocks until Ctrl+C) — good for an interactive session:
huitzo sandbox start

# Background daemon — good for scripts/agents; returns immediately:
huitzo sandbox start --background
```

`start` options:

| Flag | Default | Meaning |
|---|---|---|
| `--port INT` | `8080` | Port to bind. |
| `--background` / `-b` | off | Daemonize and return immediately. |
| `--no-tls` | off | Run without TLS. **Also disables auth** — local use only. |
| `--local-keys` | off | Use real LLM/HTTP/files via `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` instead of mocks. |
| `--token TEXT` | auto | Sandbox auth token (auto-generated if omitted). |
| `--pidfile TEXT` | `~/.huitzo/sandbox.pid` | PID file location (use a distinct one to run more than one sandbox). |

On start, the CLI writes a **sidecar JSON** next to the pidfile at
`<pidfile>.json` (default `~/.huitzo/sandbox.json`) with this exact shape:

```json
{"url": "https://localhost:8080", "token": "<auth-token>", "commands": 3, "pid": 12345}
```

The sidecar is written `0o600` (owner-only) and holds the auth token in
plaintext — treat it as a secret and never commit it. `huitzo pack exec` /
`list-commands` / `describe` auto-discover the URL + token from this sidecar, so
you usually don't pass `--sandbox-url` / `--sandbox-token` yourself.

### Status

```bash
huitzo sandbox status
```

Reports running/not-running plus PID, URL, command count, and a `/health` probe.
The JSON envelope is:

```json
{"ok": true, "data": {"running": true, "pid": 12345, "url": "https://localhost:8080", "commands": 3, "healthy": true}}
```

When nothing is running it returns `{"ok": true, "data": {"running": false}}`.
Stale pidfiles are cleaned up automatically and reported with `"stale": true`.

### Execute a command against the sandbox

Use `huitzo pack exec` (it resolves the sandbox from the sidecar):

```bash
# Against an already-running background sandbox (sidecar auto-discovered):
huitzo pack exec hello --args '{"name": "World"}'

# Or one-shot: start an ephemeral sandbox, run, then stop — no manual lifecycle:
huitzo pack exec analyze --local --args '{"text": "..."}'
```

Related discovery commands (same sidecar resolution):

- `huitzo pack list-commands` — enumerate the commands the sandbox is serving.
- `huitzo pack describe <command>` — print a command's args schema, timeout, and namespace.

`pack exec` options that matter here: `--args` (JSON, default `{}`), `--local`
(ephemeral sandbox), `--sandbox-url` / `--sandbox-token` (explicit, instead of
the sidecar), `--file` (upload a file before execution, repeatable),
`--local-keys`, `--port`, `--no-tls`.

### Stop

```bash
huitzo sandbox stop
```

Sends `SIGTERM` (escalates to `SIGKILL` after ~5s) and removes the pidfile +
sidecar. Safe to call when nothing is running. In a script, always pair a
background start with a trap:

```bash
huitzo sandbox start --background
trap 'huitzo sandbox stop || true' EXIT
```

## Steps

1. **Validate first.** Run `/validate-pack` (or `huitzo pack validate`). The
   sandbox installs your pack editable on start; a broken manifest fails there.
2. **Start it.** Foreground for an interactive session, `--background` for
   scripts. Read the sidecar `{url, token}` if you need the endpoint directly.
3. **Exercise commands.** Use `huitzo pack exec <command> --args '{...}'`. Use
   `list-commands` / `describe` to discover names and schemas.
4. **(Dashboard authors)** Point the dashboard dev server at the running
   sandbox so `useCommand` hooks hit real output — see `/dashboard-dev`.
5. **Stop it.** `huitzo sandbox stop` (or rely on the `trap` in scripts).

## JSON / agent mode

For scripting or AI-agent use, add the **global** flag `--output json` BEFORE the
subcommand (`huitzo --output json sandbox status`). It wraps every response in
the `{ok, data|error}` envelope and implies `--non-interactive`. See
`/cli-non-interactive` for the envelope shape, exit codes, and end-to-end
recipes.

## Notes

- `--no-tls` disables auth — only ever use it on `localhost`.
- To run more than one sandbox at once, give each a distinct `--port` and
  `--pidfile` (the sidecar path is derived from the pidfile).
