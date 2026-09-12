---
name: sandbox
description: Run a pack against the local Huitzo sandbox (start, status, exec, stop)
argument-hint: "[start|status|stop|exec <command> [--args json]]"
disable-model-invocation: true
---

# /sandbox

> Verified against the Huitzo CLI surface as of 2026-09 (`huitzo <cmd> --help` is authoritative).

A **sandbox** is a local dev session that loads your pack's source as an
editable install and serves its commands over a local HTTP(S) endpoint — so
you can execute real commands with real arguments, and point a dashboard's
dev server at live output, before you ever publish. This is the
**sandbox → preview** rung of the loop: scaffold → develop → test →
**sandbox** → publish.

## Prerequisites

- A valid pack: `huitzo.yaml` in the current directory (run `/validate-pack` first).
- The CLI on `PATH` (`huitzo --version`).

## Start

```bash
huitzo sandbox start                  # foreground, blocks until Ctrl+C
huitzo sandbox start --background      # daemonize, returns immediately (scripts/agents)
```

| Flag | Default | Meaning |
|---|---|---|
| `--port INT` | `8080` | Port to bind. |
| `-b`, `--background` | off | Daemonize and return immediately. |
| `--no-tls` | off | Run without TLS. **Also disables auth** — localhost only. |
| `--local-keys` | off | Use real `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`-backed LLM + unrestricted HTTP instead of the sandbox's mocked backends. |
| `--token TEXT` | auto-generated | Sandbox auth token. |
| `--pidfile PATH` | `~/.huitzo/sandbox.pid` | PID file location — use a distinct one to run more than one sandbox at a time. |

`huitzo pack dev` brings up the same sandbox in the foreground plus a REPL
(and, with `--docs`, a local docs server) — use it for an interactive coding
session; use `sandbox start` when a script or agent just needs the endpoint
up.

## Status

```bash
huitzo --output json sandbox status
```

Reports running/not-running, PID, URL, command count, and a health probe. A
stale pidfile is cleaned up automatically. With nothing running: `{"ok": true,
"data": {"running": false}}`.

## Exec — run a command against it

```bash
# Against an already-running background sandbox (auto-discovered):
huitzo --output json pack exec analyze --args '{"input": "hello"}'

# One-shot: starts an ephemeral sandbox, runs, stops it — no lifecycle to manage:
huitzo --output json pack exec analyze --local --args '{"input": "hello"}'
```

`pack exec` options that matter here: `--args '<json>'` (default `{}`),
`--local` (ephemeral sandbox for this one call), `--sandbox-url` /
`--sandbox-token` (talk to an explicit sandbox instead of auto-discovering
one), `--pidfile`, `--file PATH` (repeatable, upload a file before running),
`--local-keys`, `--port`, `--no-tls`.

Discover what's available before calling it:

```bash
huitzo pack list-commands
huitzo pack describe analyze     # args schema, timeout, namespace
```

`list-commands` and `describe` take the same `--sandbox-url` /
`--sandbox-token` / `--pidfile` options as `exec`.

## How a dashboard's dev server reaches it

A scaffolded dashboard's dev server proxies its API calls to a sandbox
running on `localhost:8080` (the sandbox's default port). Start the sandbox
first, then run the dashboard's dev server — `useCommand` hooks then hit real
pack output instead of mocks. See the `/dashboard-dev` skill.

## Stop / cleanup

```bash
huitzo sandbox stop
```

Terminates the sandbox and removes its pidfile. Safe to call when nothing is
running. In a script, always pair a background start with a trap:

```bash
huitzo sandbox start --background
trap 'huitzo sandbox stop || true' EXIT
```

## JSON / agent mode

Add the **global** flag `--output json` before the subcommand
(`huitzo --output json sandbox status`) — it implies `--non-interactive` and
wraps every response in the `{ok, data|error}` envelope. See the
`/cli-non-interactive` skill for the full envelope, exit codes, and end-to-end
recipes.

## Notes

- `--no-tls` disables auth — only ever use it on `localhost`.
- Run more than one sandbox at once by giving each a distinct `--port` and
  `--pidfile`.
