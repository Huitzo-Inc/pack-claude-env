---
paths:
  - "src/**/*.py"
  - "pack/src/**/*.py"
  - "packs/*/src/**/*.py"
---

# Error Handling

Full hierarchy with constructor kwargs: the `huitzo-sdk` skill. This rule is
the condensed, always-loaded version.

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
| Business-rule validation Pydantic didn't catch | `ValidationError(field=..., value=..., message=...)` |
| A user-configured secret is missing | `SecretsError(secret_name=..., message=...)` (or just `await ctx.secrets.require(...)`, which raises it for you) |
| An API the *user* configured failed | `ExternalAPIError(service=..., message=...)` |
| The command can't complete for a domain reason | `CommandError(message, exit_code=1)` |
| A platform service (`ctx.llm`, `ctx.http`, ...) is unwired or fails | let `IntegrationError`/its subclass propagate — don't catch and re-wrap it |

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
to fix and where, not the raw exception text.

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

   `ValidationError.value` and `HTTPError.url`/`response_body` are
   auto-redacted by the SDK when the field name looks secret-shaped — but
   that's a backstop, not a license to pass secrets into error payloads.

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
