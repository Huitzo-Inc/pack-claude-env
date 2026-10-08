---
paths:
  - "src/**/*.py"
  - "pack/src/**/*.py"
  - "packs/*/src/**/*.py"
---

# Error Handling

Full hierarchy with constructor kwargs: the `huitzo-sdk` skill. This rule is
the condensed, path-scoped version (the always-on core is `00-huitzo-core.md`).

## Hierarchy (real class names — never the Python builtins)

```
HuitzoError
├── CommandError
│   ├── CircularCommandError
│   ├── MaxCallDepthError
│   └── CommandNotFoundError
├── PipelineError
├── ValidationError
├── CommandTimeoutError        # ❌ not TimeoutError — that's a Python builtin
├── StorageError
├── SecretsError
├── ExternalAPIError
├── IntegrationError
│   ├── LLMError
│   ├── CronError
│   ├── EmailError
│   ├── HTTPError
│   ├── DatabaseError
│   ├── ExtensionNotAvailable
│   └── MCPError (+ MCPConnectionError, MCPToolError, MCPTimeoutError, MCPSchemaError)
├── HTTPSecurityError
├── SSHError
├── IntegrationLifecycleError
├── PackExecutionError
├── PackPermissionError        # ❌ not PermissionError — that's a Python builtin
├── ConfigurationError
└── RateLimitError
```

Import from `huitzo_sdk.errors` (or top-level `huitzo_sdk`) — never define a
parallel exception hierarchy.

## When to raise what

| Situation | Exception |
|---|---|
| Business-rule validation Pydantic didn't catch | `ValidationError(field=..., value=None, message=...)` — name the field; do not pass the user's text as `value` |
| A user-configured secret is missing | `SecretsError(secret_name=..., message=...)` (or just `await ctx.secrets.require(...)`, which raises it for you) |
| An API the *user* configured failed | `ExternalAPIError(service=..., message=...)` |
| The command can't complete for a domain reason | `CommandError(message, exit_code=1)` |
| A platform service (`ctx.llm`, `ctx.http`, ...) is unwired or fails | let `IntegrationError`/its subclass propagate — don't catch and re-wrap it (a stage with a documented fallback may catch the specific subclass; see "Pipeline stages") |

## `ExternalAPIError` pattern

```python
from huitzo_sdk.errors import ExternalAPIError

try:
    result = await external_client.call(api_key)
except AuthError as exc:
    raise ExternalAPIError(
        service="crm-provider",
        message="Invalid API key. Update it on the Integrations page.",
    ) from exc
```

Write the message for the *user* who configured the integration — name what
to fix and where, not the raw exception text. "For the user" never means
"quoting the user": a message names the field or the service and the fix,
and does not repeat what the caller typed (rule 6).

## Pipeline stages

A stage is an ordinary command, but its errors travel differently.

- **A stage failure reaches the caller as `PipelineError`,** not as the
  error the stage raised. It carries `failed_stage_index`,
  `failed_stage_name` and `partial_results` (one entry per stage that ran,
  the failing one included); the stage's own error is its `__cause__`.
- **Pipelines fail fast.** The first stage to raise ends the run and later
  stages are skipped. A retry or a fallback therefore lives inside the
  stage that owns it: catch the specific error there and return a result
  the next stage accepts. A separate fallback stage would never run.

  ```python
  try:
      label = await ctx.llm.complete(prompt, profile="default", schema=Label)
  except LLMError:
      label = classify_by_keywords(args.text)   # deterministic fallback, same return model
  ```

- **Check caller input before the pipeline when the error type matters.**
  If the caller should get a `ValidationError` for a bad field, raise it in
  the command that composes the pipeline, before the pipeline starts. That
  check makes no model call.

  ```python
  if args.policy_id not in KNOWN_POLICIES:
      raise ValidationError(
          field="policy_id", value=None, message="Unknown policy. Pick one from list-policies."
      )
  result = await pipeline.execute(args.model_dump())
  ```

- **What a stage stores is visible.** A failed stage's error message and the
  last stage's output are stored with the run and readable by the people
  the run is visible to. Stage commands can also be called directly, so
  every input field needs its full limits.

## Rules

1. **Never catch broadly.** A bare `except:` or an overly broad `except
   Exception` clause around command logic hides the real failure from the
   runtime's error reporting and retry logic.

   ```python
   try:
       result = await do_work()
   except Exception:                 # ❌ swallows everything, hides the real failure
       return {"error": "something went wrong"}

   result = await do_work()          # ✅ let unexpected errors propagate
   ```

2. **Never log secret values.** Not in a message, not in a kwarg, not in an
   error's `details`.

   ```python
   ctx.log.error(f"auth failed with key {api_key}")   # ❌ — never interpolate a secret
   ctx.log.error("auth failed", key_name="USER_API_KEY")   # ✅ — name it, don't show it
   ```

   `ValidationError.value` is redacted when the `field` name looks
   secret-shaped, and `HTTPError.url` is always redacted. `HTTPError
   .response_body` is only **truncated to 200 chars** — never redacted —
   so never put a response body you haven't vetted into an error; a token
   echoed back by a 4xx response is not scrubbed for you.

3. **Use the most specific exception.** `SecretsError` over `CommandError`
   when a secret is missing; `ExternalAPIError` over a bare `Exception`
   re-raise when the *user's* external service failed.

4. **Actionable messages.** Say what to do, not just what broke:

   ```python
   raise CommandError("Error")   # ❌ tells the user nothing
   raise CommandError("Analysis failed: input text contains no extractable entities")   # ✅
   ```

5. **Don't log and raise.** The runtime logs raised exceptions. Raise once;
   don't also call `ctx.log.error(...)` right before raising the same thing.

6. **No user text in error messages.** An error's `message` (and
   `ValidationError.value`) is stored with the run and shown to other
   people. Name the field and the fix; never interpolate an argument.

   ```python
   raise ValidationError(field="topic", value=args.topic, message=f"Bad topic: {args.topic}")   # ❌ repeats user text
   raise ValidationError(field="topic", value=None, message="Topic is empty. Enter a topic.")   # ✅
   raise ExternalAPIError(service="news", message=f"No results for {args.query}")               # ❌ repeats user text
   raise ExternalAPIError(service="news", message="The news service returned no results.")      # ✅
   ```
