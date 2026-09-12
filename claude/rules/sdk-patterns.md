---
paths:
  - "src/**/*.py"
  - "pack/src/**/*.py"
  - "packs/*/src/**/*.py"
---

# SDK Patterns

Full reference (exact signatures, every service, testing, anti-patterns): the
`huitzo-sdk` skill. This rule is the condensed, path-scoped version for
writing command code (the always-on core is `00-huitzo-core.md`) — it must
never contradict that skill.

## Imports

```python
from huitzo_sdk import command, Context
from huitzo_sdk.errors import ValidationError, CommandError, SecretsError, ExternalAPIError
```

Import only from the top-level `huitzo_sdk` namespace (and `huitzo_sdk.errors`).
Never import from internal modules like `huitzo_sdk.command` or `huitzo_sdk.context`.

## Command shape

```python
from pydantic import BaseModel, Field
from huitzo_sdk import Context, command

class AnalyzeArgs(BaseModel):
    """Arguments for the analyze-text command."""
    text: str = Field(..., description="Text to analyze")
    language: str = Field(default="en", description="Language code")

@command("analyze-text", namespace="my-pack", timeout=60, queue="medium")
async def analyze_text(args: AnalyzeArgs, ctx: Context) -> dict:
    """Docstring becomes marketplace help text."""
    return {"result": "value"}
```

- `name`: kebab-case `verb-noun` (e.g. `analyze-text`, `send-report`).
- `namespace`: must match the pack's `namespace` in `huitzo.yaml`.
- First parameter: a `pydantic.BaseModel` subclass (validated from a `dict`
  automatically) — or a plain `dict` if the command takes no structured args.
- Second parameter: `Context`, injected by the runtime.
- `queue`: `"fast" | "medium" | "long"` only — never `"default"` or `"auto"`.
  Default is `"medium"`. Pick `"long"` for anything that can run past ~15 minutes.
- Both `async def` and plain sync functions are supported; prefer `async def`
  for I/O-bound work; use a plain sync function only when the work is CPU-bound.
- Return `dict`, a Pydantic model, `str`, `int`, or `None` — pick one shape
  per command and keep it consistent across versions.

## Service one-liners

```python
response = await ctx.llm.complete(prompt, profile="default")          # never model=
data = await ctx.http.get("https://api.example.com/data")             # domain must be in huitzo.yaml
await ctx.email.send(to="user@example.com", subject="Report", body=body)
await ctx.telegram.send(chat_id="123", message="Alert!")
await ctx.files.write("reports/output.json", json.dumps(report))
report = await ctx.files.read_json("reports/output.json")
result = await ctx.ssh.run("gpu-cluster", "uptime")                     # static commands only
rows = await ctx.db.query("analytics-db", "SELECT * FROM t WHERE id = %s", record_id)
api_key = await ctx.secrets.require("USER_API_KEY")                    # always await
ctx.log.info("processing started", record_id=record_id)                # sync, kwargs scrubbed
```

Every service used here needs a matching `permissions:` token and a
`services:` declaration in `huitzo.yaml` — see the `huitzo-manifest` skill.

## Storage scopes

`ctx.storage` always needs a default and an explicit scope choice:

```python
data = await ctx.storage.get("key", default={})
await ctx.storage.save("key", data, scope="pack")   # "user" (default) | "pack" | "tenant"
```

- `"user"` — per-user, per-pack (default, safest).
- `"pack"` — shared across users in the tenant, still pack-isolated.
- `"tenant"` — **no pack component**; every pack in the tenant shares this
  key space. Use only for deliberate cross-pack sharing with a unique key
  prefix; never for a generic key like `"config"`.

Keys must match `^[a-zA-Z0-9_\-./]{1,256}$` — no `:`.

## HTTP allowlist

`ctx.http` only reaches domains declared in `huitzo.yaml`'s
`services.http.allowed_domains` (plus `*.suffix` wildcards). HTTPS is
required. Don't try to work around a blocked domain — add it to the manifest
instead of routing through a proxy or IP literal.

## Secrets

```python
from huitzo_sdk.errors import SecretsError, ExternalAPIError

api_key = await ctx.secrets.require("USER_API_KEY")   # raises SecretsError if missing
premium_key = await ctx.secrets.get("PREMIUM_KEY")     # returns None if missing
```

`require`/`get`/`exists` are **all async** — always `await` them. Never log a
secret value, including in an error message or an `f-string` passed to
`ctx.log`.

## Logging

Use `ctx.log.debug/info/warning/error(message, **kwargs)` — never `print()`.
Pass variable data as keyword fields (scrubbed automatically for
secret-shaped names), not interpolated into `message` (never scrubbed):

```python
ctx.log.info("fetched record", record_id=record_id, source="crm")   # good
```

## No model names

Never write a model name (`"gpt-4"`, `"claude-sonnet-4-6"`, etc.) anywhere in
pack code. Always pass `profile=` to `ctx.llm.complete`/`.chat`/`.stream` and
declare the profile in `huitzo.yaml`'s `services.llm`. The backend resolves
`profile` to a concrete model — that resolution is not the pack's concern.

## Traceability header

Every command file needs a header pointing at this project's own docs, not
the SDK's:

```python
"""
Module: analyze_text
Description: Analyzes input text and returns structured findings.

Implements:
    - docs/commands/analyze-text.md#analyze-text
"""
```

The referenced doc must exist under this project's `docs/commands/` before
the command is committed — docs first, code implements them.
