---
name: huitzo-platform
description: >
  Huitzo platform surface: REST API, keys, task polling, hosted MCP, MCP inside
  packs, webhooks, secrets. Use when calling the platform from outside a pack
  or wiring MCP. Not pack code -> huitzo-sdk.
argument-hint: "[topic: rest, auth, mcp, webhooks, secrets]"
---

> Verified against docs.huitzo.ai (2026-09).

# Huitzo Platform Reference

The **outside-the-pack** surface: calling Huitzo over HTTP, connecting an MCP
client to it, or calling other MCP servers from inside a pack. For the
`@command`/`Context` API pack code is written against, see `huitzo-sdk`.

## Base URL

```
Cloud:       https://huitzo.ai/api/v1
Self-hosted: http://your-server:8080/api/v1
```

MCP is not under `/api/v1` — it is `POST /mcp` (cloud: `https://huitzo.ai/mcp`),
kept short because it goes into connector config files.

## Authentication

| Credential | Format | Use for | Lifetime |
|---|---|---|---|
| JWT access token | `POST /api/v1/auth/login` → `accessToken` | Hub, CLI login | Short; refresh via `POST /api/v1/auth/refresh` |
| API key | `sk-huitzo-<64 hex chars>` | Server-to-server, CI, MCP connectors | Long-lived, revocable |

Every request carries `Authorization: Bearer <token-or-key>`. Create keys
under **Settings → API Keys** in the Hub, or `POST /api/v1/account/api-keys`
with a `scopes` list. **Allowed scopes:** `commands:execute` (run commands —
the only scope an MCP client needs) and `files:read`. Grant the narrowest
scope the caller needs: a connector config sits in a client's settings for
months. Keys are shown once at creation; list/get returns metadata only.

## Response envelope

Success wraps the payload in `data`:

```json
{ "data": { "...": "..." }, "meta": { "request_id": "...", "timestamp": "..." } }
```

Errors follow one shape everywhere:

```json
{
  "success": false,
  "error": {
    "type": "ValidationError",
    "message": "human-readable",
    "code": "VALIDATION_FAILED",
    "details": { "...": "..." },
    "correlation_id": "...",
    "timestamp": "..."
  }
}
```

| Code | HTTP | Meaning |
|---|---|---|
| `VALIDATION_FAILED` | 400 | Invalid input |
| `AUTHENTICATION_FAILED` | 401 | Invalid/missing token |
| `INSUFFICIENT_CREDITS` | 402 | See below |
| `PERMISSION_DENIED` | 403 | Missing permission/scope |
| `NOT_FOUND` | 404 | No such resource |
| `RATE_LIMITED` | 429 | See Rate limiting |
| `INTERNAL_ERROR` | 500 | Unexpected server error |
| `SERVICE_UNAVAILABLE` | 503 | See pack-load-busy below |

### 402 — insufficient credits

A preflight reservation was refused *before* any provider work started — no
charge occurred. The error carries `code: "INSUFFICIENT_CREDITS"` plus
`required` / `available` (integers, wallet-specific — never hardcode amounts)
and `wallet_id` / `auto_reload_state`. REST nests these under `error.details`;
SSE and MCP (no HTTP status line to carry a 402) spread the same fields flat
into the error payload instead. A task polled via `GET /api/v1/tasks/{id}`
that failed this way carries only a plain message, not the structured shape —
prefer the inline/SSE/MCP surfaces when the caller needs to branch on it.

### 403 / 503 — LLM authorization refusals

An LLM call can be refused before any provider request, for reasons a top-up
cannot fix — branch on `error.details.code`, not the HTTP status:

| `code` | Status | Retryable |
|---|---|---|
| `MODEL_NOT_REGISTERED` | 403 | no |
| `MODEL_NOT_ALLOWED` | 403 | no |
| `CREDENTIAL_PROVENANCE_UNKNOWN` | 403 | no |
| `RESERVATION_UNAVAILABLE` | 503 | yes |
| `REGISTRY_SNAPSHOT_EXPIRED` | 503 | yes |

### 503 — pack load busy

`PACK_LOAD_BUSY`: a different build of the same pack is still executing in
this process. Carries `Retry-After: 5` — safe to retry.

## Commands

```http
GET  /api/v1/commands?namespace=&search=&page=&limit=
GET  /api/v1/commands/{namespace}/{name}
POST /api/v1/commands/{namespace}/{name}
```

`POST` executes. What comes back depends on the command's declared queue:
**`fast`** runs inline (result in the same response); **`medium`/`long`**
dispatch to a worker and return `202` with a dispatch envelope, never the
result:

```json
{ "data": { "task_id": "uuid", "queue": "medium", "status": "queued", "correlation_id": "uuid" } }
```

Poll `GET /api/v1/tasks/{task_id}` until `status` is terminal (`success` |
`failure` | `timeout` | `revoked`). Never assume a synchronous result for a
`medium`/`long` command — check the response shape, not the command name.

## Pipelines

```http
POST /api/v1/pipelines/{scope}/{pack}/{name}/execute
```

Runs a pipeline declared in the pack's manifest. A fast pipeline returns the
full result inline; medium/long dispatches and returns a `task_id` to poll
like a command. See `huitzo-methodology` for when to reach for a pipeline
instead of a single command.

## Rate limiting

```http
X-RateLimit-Limit: <n>
X-RateLimit-Remaining: <n>
X-RateLimit-Reset: <epoch-seconds>
Retry-After: <seconds>          # 429 only
```

Limits are billed per endpoint class (auth, read, write, command execution)
and vary by account tier — see
[reference/rate-limiting](https://docs.huitzo.ai/docs/reference/rate-limiting)
for current numbers rather than hardcoding them. On `429`, back off using
`Retry-After`; don't guess a delay.

## Webhooks

```
# pseudocode — illustrative shape
POST /api/v1/webhooks
{ "url": "https://your-app.com/webhooks/huitzo", "events": ["command.executed", "task.completed"] }
```

Documented events: `command.executed`, `task.completed`, `task.failed`,
`pack.installed`, `pack.uninstalled`. Payload: `{"id", "type", "timestamp",
"data"}`. Verify the signature before trusting a delivery:

```python
# pseudocode
import hmac, hashlib

def verify(payload: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)
```

## Hosted MCP endpoint

Connect any Streamable-HTTP MCP client (Claude.ai, Claude Desktop, Cursor,
VS Code, Claude Code) directly to your tenant's commands.

| | |
|---|---|
| Endpoint | `https://huitzo.ai/mcp` (self-hosted: `https://<your-host>/mcp`) |
| Transport | Streamable HTTP |
| Auth | `Authorization: Bearer sk-huitzo-...` — API key only, JWT/cookie rejected |
| Required scope | `commands:execute` |

**Tool naming** — namespaces map deterministically, round-trippable:

```
@scope/pack/command  <->  scope__pack__command
```

One reserved tool outside that mapping: **`huitzo_task_poll`**. An MCP
client cannot make a raw HTTP call, so for a `medium`/`long` command
`tools/call` returns a pending envelope instead of blocking:

```json
{ "pending": true, "task_id": "celery-...", "queue": "medium",
  "message": "Call 'huitzo_task_poll' with task_id='celery-...' for the result." }
```

Call `huitzo_task_poll` with that `task_id` — never `GET /api/v1/tasks/{id}`,
which isn't reachable from inside an MCP session.

**Scope of access** — a connected client sees every public pack command, every
command in your tenant's private packs, and anything shared with your tenant
via an organization grant. It cannot see another tenant's private commands,
bypass a pack's declared permissions, or run with elevated privileges — an
API-key call runs at the same privilege as any other API-key call.

### Client configs

**Claude.ai:** Settings → Connectors → Add custom connector → URL
`https://huitzo.ai/mcp`, auth Bearer token, paste your `sk-huitzo-...` key.

**Claude Desktop / Cursor / VS Code** — add to the client's `mcpServers` JSON:

```json
{ "huitzo": { "type": "streamable-http", "url": "https://huitzo.ai/mcp",
  "headers": { "Authorization": "Bearer sk-huitzo-..." } } }
```

**Claude Code** (project `.mcp.json` — prefer env expansion over a literal key):

```json
{ "mcpServers": { "huitzo": { "type": "http", "url": "https://huitzo.ai/mcp",
  "headers": { "Authorization": "Bearer ${HUITZO_API_KEY}" } } } }
```

**CLI shortcut:** logged in via the Huitzo CLI, `huitzo mcp setup docs`
writes an equivalent MCP entry for you (`--stdout` prints instead of writing).

## MCP servers inside a pack

The direction above is Huitzo *serving* MCP. A pack can also *consume*
external MCP servers via `ctx.mcp` — pure protocol translation, no LLM
involved. Declare them in `huitzo.yaml`:

```yaml
# huitzo.yaml
mcp_servers:
  - name: github
    type: stdio
    command: ["uvx", "mcp-server-github==1.2.3"]   # pin the version
    env:
      GITHUB_TOKEN: "${secrets.GITHUB_TOKEN}"

commands:
  - name: "create-issue"
    permissions: ["mcp:call"]
```

- `type: stdio` spawns a subprocess; `type: http` points at a remote server
  (`url` + `headers`). Keep a pack under ~10 servers — each stdio server is
  its own subprocess.
- `mcp:call` gates any command that touches `ctx.mcp`. Secrets for the
  *server itself* (e.g. `GITHUB_TOKEN`) are ordinary Tier-3 user secrets,
  interpolated with `${secrets.NAME}`.
- **Discover tools from inside a command** — there is no CLI for this
  (`huitzo mcp` has only `setup docs`; see `cli-non-interactive`):

  ```python
  # pseudocode — https://docs.huitzo.ai/docs/sdk/mcp
  tools = await ctx.mcp.list_tools(server)   # server: str | None = None
  schema = await ctx.mcp.get_tool_schema(server, tool)
  info = ctx.mcp.servers                     # dict[str, MCPServerInfo]
  ```
- **Testing:** mock `ctx.mcp.call()` — `AsyncMock(return_value=...)` —
  rather than spawning a real server. `ctx.mcp` is typed `Any` in the SDK
  wheel (no public MCP client class/Protocol to import), so treat all of the
  above as the documented contract from https://docs.huitzo.ai/docs/sdk/mcp,
  not an importable SDK type — that page also has the exact `ctx.mcp.call
  (server, tool, arguments, timeout=None)` signature and the
  `MCPConnectionError` / `MCPToolError` / `MCPTimeoutError` /
  `MCPSchemaError` hierarchy (not `huitzo-sdk`, which deliberately declines
  to state one).

## Secrets model

Three tiers, different owners:

| Tier | Owner | Access |
|---|---|---|
| Platform | Platform admin | No SDK accessor — consumed internally by `ctx.llm` / `ctx.email` / `ctx.tts` / `ctx.telegram` |
| Pack config | Pack developer | `ctx.config` — not yet available in this SDK version |
| User | End user | `await ctx.secrets.require(...)` / `.get(...)` / `.exists(...)` |

A user configures a Tier-3 secret themselves, in the Hub (Settings →
Connections → Manage integrations) — never at install time, never collected
by the platform on a pack's behalf. **Bring Your Own Key:** a tenant's own
LLM provider key always takes precedence over the platform's; `ctx.llm`
resolves this automatically. Secrets are encrypted at rest, never logged
(masked in structured output), and rotate without reinstalling the pack.

**This is an API-surface contract, not a sandbox today.** "No SDK accessor"
describes the shape of the SDK, not an enforced runtime boundary — pack
commands run in-process and share the host's environment on most execution
paths. Treat installing an untrusted pack as granting it your deployment's
platform credentials, and vet marketplace packs accordingly.

## Calling Huitzo from an external app

```python
# pseudocode — minimal async client (always set a timeout)
import httpx

async def execute(command: str, args: dict, api_key: str) -> dict:
    async with httpx.AsyncClient(base_url="https://huitzo.ai/api/v1",
        headers={"Authorization": f"Bearer {api_key}"}, timeout=30.0) as c:
        resp = await c.post(f"/commands/{command}", json=args)
        resp.raise_for_status()
        return resp.json()["data"]
```

```typescript
// pseudocode — minimal fetch wrapper
async function execute(command: string, args: object, apiKey: string) {
  const res = await fetch(`https://huitzo.ai/api/v1/commands/${command}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
    body: JSON.stringify(args),
  });
  return (await res.json()).data;
}
```

```bash
# pseudocode
curl -X POST https://huitzo.ai/api/v1/commands/@acme/claims/process \
  -H "Authorization: Bearer $HUITZO_API_KEY" -H "Content-Type: application/json" \
  -d '{"claimId": "CLM-12345"}'
```

## Tenant isolation

PostgreSQL Row-Level Security enforces isolation at the database level — a
pack never writes a `WHERE tenant_id = ?` filter itself; storage, files, and
logs are all scoped to `tenant_id` automatically, and REST, MCP, and the CLI
share the same RLS path, so the threat model is identical across all three.

## Self-hosting

Everything above works identically self-hosted at your own base URL,
including the MCP endpoint (`https://<your-host>/mcp`). See
[guides/self-hosting/deployment](https://docs.huitzo.ai/docs/guides/self-hosting/deployment)
and [guides/self-hosting/QUICK_START](https://docs.huitzo.ai/docs/guides/self-hosting/QUICK_START).

## Anti-patterns

| ❌ Don't | ✅ Do instead |
|---|---|
| ❌ Call raw HTTP from a dashboard component | Use `@huitzo/dashboard-sdk-react` hooks (`useCommand`) |
| ❌ Hardcode an API key in source (`"sk-huitzo-..."`) | Read it from an environment variable / secret store |
| ❌ Grant an MCP connector a broad scope "to be safe" | Grant exactly `commands:execute` |
| ❌ Poll `GET /api/v1/tasks/{id}` from inside an MCP client | Call the `huitzo_task_poll` tool instead |
| ❌ Assume every command returns its result inline | Check for the `task_id`/`queue`/`status` dispatch shape first |

## Read more

- [api/rest](https://docs.huitzo.ai/docs/api/rest)
- [guides/connect-claude-mcp](https://docs.huitzo.ai/docs/guides/connect-claude-mcp)
- [guides/mcp-pack-integration](https://docs.huitzo.ai/docs/guides/mcp-pack-integration)
- [guides/external-integrations](https://docs.huitzo.ai/docs/guides/external-integrations)
- [reference/secrets](https://docs.huitzo.ai/docs/reference/secrets)
- [reference/rate-limiting](https://docs.huitzo.ai/docs/reference/rate-limiting)
- [architecture/security](https://docs.huitzo.ai/docs/architecture/security)
- [guides/self-hosting/deployment](https://docs.huitzo.ai/docs/guides/self-hosting/deployment)
