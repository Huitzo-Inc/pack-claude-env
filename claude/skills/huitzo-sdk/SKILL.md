---
name: huitzo-sdk
description: >
  huitzo_sdk API: @command, ctx.* services, error hierarchy, testing
  patterns. Use when writing or testing pack commands. Not for huitzo.yaml
  (see huitzo-manifest) or dashboards (huitzo-dashboard-sdk).
argument-hint: "[topic: command, context, llm, storage, errors, testing]"
---

> Verified against huitzo-sdk 1.7.0 (2026-09).

# Huitzo SDK Reference

## Imports

```python
from huitzo_sdk import command, Context
from huitzo_sdk.errors import ValidationError, CommandError, SecretsError, ExternalAPIError
```

Always import from the top-level `huitzo_sdk` namespace. `huitzo_sdk.manifest`,
`huitzo_sdk.pipeline`, and `huitzo_sdk.identifiers` are submodules, not
re-exported at top level — import them explicitly if you need them.

## The `@command` decorator

```python
def command(
    name: str, namespace: str, *,
    version: str = "1.0.0", timeout: int = 60, retries: int = 3,
    retry_backoff: float = 1.0, retry_max_wait: int = 60,
    queue: Literal["fast", "medium", "long"] = "medium",
    output_format: str = "auto", description: str | None = None,
    streaming: bool = False,
) -> Callable[[F], F]
```

| Param | Type | Default | Notes |
|---|---|---|---|
| `name` | `str` | required | positional |
| `namespace` | `str` | required | positional |
| `version` | `str` | `"1.0.0"` | keyword-only |
| `timeout` | `int` | `60` | seconds; see queue ceilings below |
| `retries` | `int` | `3` | |
| `retry_backoff` | `float` | `1.0` | |
| `retry_max_wait` | `int` | `60` | |
| `queue` | `"fast"\|"medium"\|"long"` | `"medium"` | `"auto"` and `"default"` are not valid values |
| `output_format` | `str` | `"auto"` | |
| `description` | `str\|None` | `None` | |
| `streaming` | `bool` | `False` | marks an async-generator pipeline stage |

**Queue semantics (from the decorator's own docstring):**
- `"fast"` runs inline in the API process and returns the result directly.
- `"medium"` (default) and `"long"` dispatch to a worker; the caller gets a task receipt and polls.
- Two independent ceilings apply and the tighter one wins. `timeout` is the only thing that stops a *running* command — worker pools impose none of their own. Separately, the platform's stale-execution reaper closes the execution *record* on a per-queue threshold — roughly 10 minutes on `fast`, 20 on `medium`, 9 hours on `long` — and that closure is terminal: a command that outlives its queue's threshold is reported failed even if the worker finishes.
- Declare `"long"` for anything that can exceed ~15 minutes, not only work measured in hours.

**Sync vs async — both supported.** A coroutine function is awaited directly
under `asyncio.wait_for(fn(args, ctx), timeout=...)`. A plain sync function
runs via `asyncio.wait_for(asyncio.to_thread(fn, args, ctx), timeout=...)`.
Exceeding the timeout raises `CommandTimeoutError`, not `TimeoutError` ❌.

**`streaming=True`** requires the function to be an `async def` that `yield`s
(an async generator). Mismatches raise `ValueError` at **registration** time
(decorator application), not at call time:
- `streaming=True` on a non-async-generator function → `ValueError`.
- `streaming=False` (default) on an async-generator function → `ValueError`.
- If a streaming function declares a return annotation that isn't
  `AsyncIterator[PipeChunk[...]]` / `AsyncGenerator[PipeChunk[...], None]`, a
  `UserWarning` is emitted (annotations may be omitted; this is a warning, not
  an error).

**Args model detection:** the decorator inspects the **first parameter's type
hint**. If it is a `pydantic.BaseModel` subclass, that type is used to
`model_validate()` a plain `dict` passed at call time. An already-validated
model instance passed in (not a `dict`) is used untouched.

**Return type:** `Result = dict[str, Any] | BaseModel | str | int | None` — a
command may return a dict, a Pydantic model, a bare `str`/`int`, or `None`;
it is not limited to `dict`.

If the runtime doesn't inject a `Context`, the wrapper raises
`ConfigurationError` — "Context must be provided by the Huitzo runtime."

## Context

Identity/metadata fields: `user_id: UUID`, `tenant_id: UUID`, `session_id: UUID`
(all default to a sentinel nil UUID until the runtime injects real values),
`correlation_id: str` (a real UUID4 generated per-instance), `command_name: str`,
`namespace: str`, `command_version: str = "1.0.0"`, and
`deployment_mode: DeploymentMode = DeploymentMode.CLOUD` (`CLOUD | SELF_HOSTED | EDGE`).
`ctx.storage` raises `ConfigurationError` if `tenant_id`/`user_id` are still
the sentinel.

Every service below is a property that raises `IntegrationError` if the
runtime didn't wire it (except where noted — `pipeline`/`pipe` raise
`RuntimeError`, and `execute` always raises `IntegrationError`).

| Service | Signature |
|---|---|
| `ctx.llm` | `async complete(prompt, *, profile="default", system=None, temperature=1.0, max_tokens=None, top_p=None, stop=None, response_format=None, schema=None) -> str \| T`; `async chat(messages, *, profile=..., ...) -> str \| T`; `stream(prompt, *, profile=..., ...) -> AsyncIterator[str]` (not a coroutine — iterate with `async for`) |
| `ctx.email` | `async send(*, to, subject, body=None, html=None, cc=None, bcc=None, attachments=None) -> None`; `async send_template(*, to, template_id, template_data=None) -> None` |
| `ctx.http` | `async get/delete(url, *, headers=None, params=None, timeout=None)`; `async post/put(url, *, headers=None, params=None, json=None, data=None, files=None, timeout=None)` — all `-> Any` |
| `ctx.telegram` | `async send(*, chat_id: str, message: str, parse_mode=None) -> None`; `async send_document(*, chat_id, document: bytes, filename, caption=None)`; `async send_photo(*, chat_id, photo: bytes, caption=None)` |
| `ctx.tts` | `async synthesize(text, *, voice_id, language="en", output_format="mp3_44100_64") -> SynthesisResult`; `async synthesize_batch(segments: list[str], *, voice_id, language="en", output_format=...) -> BatchSynthesisResult`; `async voices() -> list[VoiceInfo]` |
| `ctx.files` | `async read(path) -> bytes`; `read_excel(path, *, sheet=None)`; `read_csv(path, *, delimiter=",", encoding="utf-8")`; `read_json(path)`; `async write(path, content: str\|bytes, *, binary=False)`; `async delete(path)`; `async move/rename/copy(source, dest)`; `async info(path) -> dict`; `async list(prefix="") -> list[dict]`; `async exists(path) -> bool`; `async get_url(path, *, expires=3600, method="GET") -> str` |
| `ctx.ssh` | `async run(target: str, command: str, *, timeout=30) -> SSHResult(stdout, stderr, exit_code)` |
| `ctx.db` | `async query(integration, sql, *params, timeout=30) -> list[dict]`; `async execute(integration, sql, *params, timeout=30) -> int`; `transaction(integration, *, timeout=30)` — async context manager yielding a `DBTransaction` with the same `query`/`execute` shapes |
| `ctx.storage` | `async save(key, value, *, scope="user", ttl=None, metadata=None) -> str`; `async get(key, *, scope="user", default=None) -> Any`; `async delete/exists(key, *, scope="user")`; `async list(prefix="", *, scope="user", limit=100, offset=0)`; `async save_many/get_many/delete_many(...)`; `async query(prefix="", *, scope="user", metadata=None, limit=100)`; `transaction()` |
| `ctx.commands` | `async execute(command_name, args: dict, *, timeout=None) -> Result` |
| `ctx.secrets` | **all async**: `async require(key) -> str`; `async get(key) -> str \| None`; `async exists(key) -> bool` |
| `ctx.log` | sync: `debug/info/warning/error(message: str, **kwargs)` |
| `ctx.cron` | props `schedule`, `scheduled_at`, `is_scheduled`; `async get_next_run(command_namespace=None)`, `async get_last_run(...)` -> `datetime \| None` |
| `ctx.mcp` | typed `Any` — see note below |
| `ctx.integrations` / `ctx.resolve(T)` | see note below |
| `ctx.pipeline` / `ctx.pipe` | see note below |
| `ctx.execute(pack, command, args=None, *, timeout=None)` | always raises `IntegrationError` in the bare SDK — runtime-injected only |

**`ctx.llm` — profile, never model.** Packs pass `profile=` (e.g. `"default"`
or a manifest-declared profile); the backend `ModelRouter` resolves it to a
concrete model. There is **no `model=` kwarg** on `complete`/`chat`/`stream` —
passing one raises `TypeError`. `schema=SomeBaseModel` returns a validated
instance of that model instead of `str`.

**`ctx.http` — security.** HTTPS-only (localhost exempt in dev). Built-in
SSRF guard blocks RFC-1918/loopback/link-local/reserved/multicast addresses
and cloud metadata IPs (`169.254.169.254`, `metadata.google.internal`,
`100.100.100.200`) even under a wildcard allowlist. `_allowed_domains`
supports `*.domain` suffix wildcards and a bare `*` (dev only). DNS-rebinding
is **not** fully mitigated — the SSRF check and the backend's connection are
separate resolutions (best-effort defense per the class docstring).

**`ctx.ssh` — static commands only.** `run()` rejects any shell metacharacter
(`; | & \` $ < > ( ) [ ] { } \ ! \n \r \t`) client-side and any command over
4096 bytes. `target` must be in the pack manifest's `ssh_targets.allowed` (or
`"*"`). Sanitize user input into arguments *before* building the command
string — do not try to escape metacharacters yourself.

**`ctx.db` — DDL and multi-statement gates.** DDL (`CREATE/DROP/ALTER/
TRUNCATE/RENAME/GRANT/REVOKE/COMMENT/DO/CALL`) is rejected unless the
integration's own config sets `allow_ddl=True`. Multi-statement payloads
(`;` followed by more SQL) are **always** rejected regardless of `allow_ddl`.
Defaults: 30s timeout (max 300s), 10,000-row cap.

**`ctx.storage` — scopes and the tenant footgun.** Three scopes: `"user"`
(default, per-user *and* per-pack), `"pack"` (per-pack, shared across users
in the tenant), `"tenant"` (**no pack component at all** — every pack in the
tenant shares this flat key space; a common key name like `"config"` will
silently collide with another pack's data). Prefer `"pack"` for pack-private
shared state; reserve `"tenant"` for deliberate cross-pack sharing with a
unique key prefix. Keys must match `^[a-zA-Z0-9_\-./]{1,256}$` — no `:`.

**`ctx.files.list()`** returns `list[dict]`, never `list[str]` — the backend
protocol only guarantees `dict[str, Any]` entries (exact keys are
backend-defined; do not hardcode a key name your test doesn't also assert
against the real backend). `read_json` raises `ValidationError` (not
`json.JSONDecodeError`) on malformed content — the client already caught and
wrapped it. `delete`/`move` need the `files:delete` permission in addition to
`files:write`; `copy` needs only `files:write`.

**`ctx.tts.synthesize_batch`** is a **type contract only** as of 1.7.0 — no
production backend implements it yet (raises `NotImplementedError` unless
overridden; only the demo fixture backend does). Keep chunking long scripts
manually with `synthesize()` until a backend PR lands it. Formats are limited
to `SUPPORTED_OUTPUT_FORMATS = ("mp3_44100_64", "mp3_44100_128")`; batches
cap at 500 segments / 200,000 characters.

**`ctx.log`** kwargs are scrubbed for secret-shaped field names
(`password|secret|token|api_key|credential|auth|bearer|cookie|...`) before
they reach the backend. The free-form `message` string is **not** scrubbed —
never interpolate a secret into it.

**`ctx.mcp` — be honest about this one.** It is typed `Any`; the SDK ships
**no public MCP client class or Protocol** for pack authors as of 1.7.0 —
only the `MCPError` family exists at the errors layer. Do not invent a
`call_tool(...)` shape from memory. Wire the server in the manifest's
`mcp_servers:` section and grant `mcp:call`; for the current call surface,
check https://docs.huitzo.ai/docs/sdk/mcp rather than trusting an older
skill or your own recollection.

**`ctx.integrations` / `ctx.resolve(T)`.** `ctx.integrations.<name>` returns a
proxy that runs the integration's lazy `connect` (`ensure_ready()`) then
delegates `.execute(*args, **kwargs)`. An unregistered name raises
`AttributeError` listing what *is* available — not `IntegrationError`.
`ctx.resolve(SomeIntegrationType)` looks up by class; zero or multiple
matches raise `IntegrationLifecycleError`.

**`ctx.pipeline` / `ctx.pipe` — `RuntimeError`, not `IntegrationError`.**
`ctx.pipeline.create(name, *, timeout=300) -> PipelineBuilder`
(`.add_stage(...)`, `.add_parallel(...)`, `async .execute(initial_args, *,
timeout=None)`); `async ctx.pipeline.get(pipeline_id)` / `async
.resume(pipeline_id)`. `ctx.pipe` (only inside a `streaming=True` stage) has
`.input: AsyncIterator[PipeChunk] | None`, `.pipeline_id`, `.stage_index`,
`.stage_name`, `.chunk_count`. Both raise plain `RuntimeError` — with a
message naming the wiring gap — when accessed without the right context (a
bare `Context()` for `pipeline`; a non-streaming stage for `pipe`).

**Stubs and unknowns.** `ctx.env`, `ctx.config`, `ctx.local_storage`,
`ctx.inference_backend` raise `ConfigurationError` ("not yet available in
this SDK version"). Any other unrecognized attribute raises plain
`AttributeError`.

## Error hierarchy

Real class names and constructor kwargs — never the two Python builtins these deliberately avoid shadowing:

```
HuitzoError(message, *, details=None)
├── CommandError(message, *, exit_code=1, details=None)
│   ├── CircularCommandError(*, call_stack, command)
│   ├── MaxCallDepthError(*, call_stack, command, max_depth)
│   └── CommandNotFoundError(*, command, namespace)
├── PipelineError(message, *, failed_stage_index, failed_stage_name, partial_results, original_error=None)
├── ValidationError(*, field, value, message)
├── CommandTimeoutError(*, timeout_seconds, elapsed_seconds)      # ❌ not TimeoutError (Python builtin)
├── StorageError(*, operation, key=None, message)
├── SecretsError(*, secret_name, message)
├── ExternalAPIError(*, service, message)
├── IntegrationError(*, service, message, details=None)
│   ├── LLMError(*, provider, model=None, status_code=None, message)
│   ├── CronError(*, message)
│   ├── EmailError(*, message)
│   ├── HTTPError(*, url, method, status_code=None, response_body=None, message)
│   ├── DatabaseError(*, integration="", message, details=None)
│   ├── ExtensionNotAvailable(*, name, deployment, available)
│   └── MCPError(*, message, details=None)
│       ├── MCPConnectionError(*, server, message)
│       ├── MCPToolError(*, tool, server, message)
│       ├── MCPTimeoutError(*, server, timeout_seconds, message=None)
│       └── MCPSchemaError(*, tool, message)
├── HTTPSecurityError(*, domain, allowed_domains=None, message=None)
├── SSHError(*, host="", target="", message="")
├── IntegrationLifecycleError(*, name, stage, message)
├── PackExecutionError(*, pack, command, original_error=None, message)
├── PackPermissionError(*, message)                                # ❌ not PermissionError (Python builtin)
├── ConfigurationError(*, message)
└── RateLimitError(*, retry_after, limit=None, current=None, message=None)
```

All are importable from top-level `huitzo_sdk` (e.g.
`from huitzo_sdk import CommandTimeoutError, PackPermissionError`). Every
class carries `code`, `http_status`, and `retryable` class attributes;
`IntegrationError` and its subclasses default `retryable=True`,
`CommandTimeoutError`/`SSHError`/`MCPTimeoutError`/`RateLimitError` also
default `retryable=True`; everything else defaults `False`.

## Demo mode

`HUITZO_DEMO_MODE=1|true|yes` (case-insensitive) auto-wires a fixture-backed
`ctx.tts` unconditionally. If `HUITZO_DEMO_FIXTURES_DIR` also points at an
existing directory, fixture-backed `ctx.llm` and `ctx.http` are additionally
wired (with a wildcard `"*"` HTTP allowlist and localhost allowed). Demo mode
**fails closed**: it raises `ConfigurationError` at `Context()` construction
if `HUITZO_ENV=production` is also set, rather than silently bypassing
egress controls.

## Testing

Three real patterns for a scaffolded pack (pytest, `asyncio_mode = "auto"`
— `@pytest.mark.asyncio` is optional but harmless).

**1. Pure helper — no Context at all.** Extract logic into a plain function
your command delegates to, and test that directly:

```python
def greet(name: str) -> str:
    return f"Hello, {name}!"

def test_greet() -> None:
    assert greet("Alice") == "Hello, Alice!"
```

**2. Bare `Context()` — for commands that touch no service.** A default
`Context()` has every service unset; call the decorated function directly:

```python
from huitzo_sdk import Context
from my_pack.commands.hello import hello_world

async def test_hello_world() -> None:
    result = await hello_world({}, Context())
    assert result["message"] == "Hello, World!"
```

**3. `MagicMock(spec=Context)` + `AsyncMock` for every async service.**
Every service on `Context` is awaited except `ctx.log` (sync) — mock
accordingly, or `await`ing a plain `MagicMock` raises `TypeError`:

```python
from unittest.mock import AsyncMock, MagicMock
from huitzo_sdk import Context
from huitzo_sdk.errors import SecretsError

def make_mock_ctx() -> MagicMock:
    ctx = MagicMock(spec=Context)
    ctx.llm = AsyncMock()
    ctx.http = AsyncMock()
    ctx.email = AsyncMock()
    ctx.telegram = AsyncMock()
    ctx.files = AsyncMock()
    ctx.storage = AsyncMock()
    ctx.secrets = AsyncMock()   # require/get/exists are all async
    ctx.commands = AsyncMock()
    ctx.log = MagicMock()       # sync — the one exception
    return ctx

async def test_requires_api_key() -> None:
    ctx = make_mock_ctx()
    ctx.secrets.require.side_effect = SecretsError(
        secret_name="USER_API_KEY", message="missing"
    )
    with pytest.raises(SecretsError):
        await my_command({}, ctx)

async def test_calls_llm() -> None:
    ctx = make_mock_ctx()
    ctx.secrets.require.return_value = "sk-test"
    ctx.llm.complete.return_value = "the answer"
    result = await my_command({}, ctx)
    ctx.llm.complete.assert_awaited_once()
    assert result["answer"] == "the answer"
```

There is no `huitzo_sdk.testing` module and no SDK-blessed mock-`Context`
helper — the pattern above is a community convention you build yourself,
not an imported fixture.

## Anti-patterns

| ❌ Wrong | ✅ Right |
|---|---|
| ❌ `ctx.llm.chat(model="claude-sonnet-4-6", ...)` | `ctx.llm.chat(profile="default", ...)` |
| ❌ `await ctx.storage.set("key", value)` | `await ctx.storage.save("key", value)` |
| ❌ `await ctx.telegram.send_message(chat_id=123, text="hi")` | `await ctx.telegram.send(chat_id="123", message="hi")` |
| ❌ `api_key = ctx.secrets.require("KEY")` (no await) | `api_key = await ctx.secrets.require("KEY")` |
| ❌ `@command("x", namespace="p", queue="default")` | `@command("x", namespace="p", queue="medium")` |
| ❌ `@command("x", namespace="p", queue="auto")` | `@command("x", namespace="p")` (medium is the default) |
| ❌ `except TimeoutError:` to catch a command timeout | `except CommandTimeoutError:` |
| ❌ `except PermissionError:` to catch a denied action | `except PackPermissionError:` |
| ❌ `except Exception:` around command logic | let unexpected errors propagate; catch specific SDK exceptions |
| ❌ `print(f"processing {args}")` | `ctx.log.info("processing", args=args)` |
| ❌ hardcoding `"gpt-4"` / `"claude-sonnet-4-6"` anywhere in pack code | pass `profile="default"` and declare the profile in `huitzo.yaml` |
| ❌ `open(path).read()` / `Path(path).write_text(...)` | `await ctx.files.read(path)` / `await ctx.files.write(path, content)` |
| ❌ `ctx.log.info(f"key={api_key}")` | `ctx.log.info("secret loaded", key_name="API_KEY")` (never the value) |

## Read more

- https://docs.huitzo.ai/docs/sdk/overview
- https://docs.huitzo.ai/docs/sdk/commands
- https://docs.huitzo.ai/docs/sdk/context
- https://docs.huitzo.ai/docs/sdk/integrations
- https://docs.huitzo.ai/docs/sdk/storage
- https://docs.huitzo.ai/docs/sdk/storage-backends
- https://docs.huitzo.ai/docs/sdk/error-handling
- https://docs.huitzo.ai/docs/sdk/file-storage
- https://docs.huitzo.ai/docs/sdk/ssh
- https://docs.huitzo.ai/docs/sdk/mcp
- https://docs.huitzo.ai/docs/sdk/namespaces
