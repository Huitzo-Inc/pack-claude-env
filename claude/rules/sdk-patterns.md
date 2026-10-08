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
    text: str = Field(..., max_length=10_000, description="Text to analyze")
    language: str = Field(default="en", max_length=8, description="Language code")

class AnalyzeResult(BaseModel):
    """What analyze-text returns."""
    summary: str = Field(..., description="One-sentence summary")
    language: str = Field(..., description="Language code the summary is written in")

@command("analyze-text", namespace="my-pack", timeout=60, queue="medium")
async def analyze_text(args: AnalyzeArgs, ctx: Context) -> AnalyzeResult:
    """Docstring becomes marketplace help text."""
    summary = await ctx.llm.complete(f"<INPUT>\n{args.text}\n</INPUT>", profile="default")
    return AnalyzeResult(summary=summary.strip(), language=args.language)
```

- `name`: kebab-case `verb-noun` (e.g. `analyze-text`, `send-report`).
- `namespace`: must match the pack's `namespace` in `huitzo.yaml`.
- First parameter: a `pydantic.BaseModel` subclass (validated from a `dict`
  automatically). Give every field its limits (`max_length`, ranges).
- Second parameter: `Context`, injected by the runtime.
- `queue`: `"fast" | "medium" | "long"` only — never `"default"` or `"auto"`.
  Default is `"medium"`. Pick `"long"` for anything that can run past ~15 minutes.
- Both `async def` and plain sync functions are supported; prefer `async def`
  for I/O-bound work; use a plain sync function only when the work is CPU-bound.
- Return a `pydantic.BaseModel` subclass. The SDK also accepts `dict`, `str`,
  `int` and `None`, but a typed return model is the default here: it is what
  lets a command be a pipeline stage, and what `huitzo pack validate --strict`
  compares with the next stage's args model.

## Stages: one step each

Work with more than one step (several model calls, a model call plus an
external effect, steps that fail separately) is a pipeline, not one long
command. Each stage is an ordinary typed command; the chain lives in
`huitzo.yaml`:

```python
class ExtractArgs(BaseModel):
    text: str = Field(..., max_length=20_000, description="Raw claim text")

class ExtractedClaim(BaseModel):
    amount: float = Field(..., ge=0, description="Claimed amount")
    category: str = Field(..., max_length=40, description="Claim category")

@command("extract-claim", namespace="claims", timeout=60)
async def extract_claim(args: ExtractArgs, ctx: Context) -> ExtractedClaim:
    """Read the amount and category out of a claim."""
    claim = await ctx.llm.complete(
        f"<INPUT>\n{args.text}\n</INPUT>", profile="default", schema=ExtractedClaim
    )
    return ExtractedClaim.model_validate(claim)   # the model's output is checked, not trusted

class AssessedClaim(ExtractedClaim):          # carries forward what `decide` needs
    risk: str = Field(..., description="low | medium | high")

@command("assess-risk", namespace="claims", timeout=10)
async def assess_risk(args: ExtractedClaim, ctx: Context) -> AssessedClaim:
    """Score the claim with fixed rules; no model call."""
    risk = "high" if args.amount > 10_000 else "low"
    return AssessedClaim(**args.model_dump(), risk=risk)
```

```yaml
pipelines:
  claim-intake:
    stages:
      - name: extract            # short verb: this is the label on the run page
        command: "claims:extract-claim"
      - name: assess
        command: "claims:assess-risk"
```

- A stage's return model is the next stage's args model, or a superset of it.
- Every model call is `ctx.llm` inside the stage that owns it. Retries and
  fallbacks stay inside that stage too: once a stage raises, later stages
  are skipped.
- A command that composes a pipeline (`ctx.pipeline`) checks its input,
  runs exactly one pipeline and makes no model call of its own.
- More than one `ctx.commands.execute` call in a command is a pipeline
  written as glue code. Nested calls are not recorded as steps.

The eight run-view authoring rules are in the `huitzo-methodology` skill.

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

**Never a model-provider host.** Do not call a model provider's API through
`ctx.http`, and do not put a provider host in `allowed_domains`. Model calls
go through `ctx.llm` only. A model call made through `ctx.http` is invisible
on the run page: no model-call mark, no usage, on any step.

```python
await ctx.http.post("https://api.openai.com/v1/chat/completions", json=body)   # ❌ model call through ctx.http
answer = await ctx.llm.complete(prompt, profile="default")                     # ✅
```

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
