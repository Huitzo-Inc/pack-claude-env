# Error Handling Rules

## Exception Hierarchy

All SDK exceptions inherit from `HuitzoError`:

```
HuitzoError (base)
├── CommandError          — General command failure
├── ValidationError       — Input validation failed
├── TimeoutError          — Command exceeded timeout
├── StorageError          — Storage operation failed
├── SecretsError          — User secret missing or inaccessible
├── ExternalAPIError      — User-configured external API failed
├── IntegrationError      — Platform service failed (base)
│   ├── LLMError          — LLM provider error
│   ├── EmailError        — Email sending error
│   └── HTTPError         — HTTP request error
├── HTTPSecurityError     — Request to disallowed domain
├── PackExecutionError    — Cross-pack call failed
├── PermissionError       — Insufficient permissions
├── ConfigurationError    — Invalid configuration
└── RateLimitError        — Rate limit exceeded
```

## When to Use Each Exception

### ValidationError — User gave bad input

```python
from huitzo_sdk.errors import ValidationError

if len(args.text) > 10000:
    raise ValidationError(
        field="text",
        value=args.text[:50] + "...",
        message="Text exceeds maximum length of 10,000 characters",
    )
```

Use when: Pydantic doesn't catch the validation (business logic rules, cross-field validation).

### CommandError — General failure

```python
from huitzo_sdk.errors import CommandError

if not results:
    raise CommandError("Analysis produced no results", exit_code=1)
```

Use when: The command cannot complete for a reason that doesn't fit other categories.

### SecretsError — Missing required secret

```python
from huitzo_sdk.errors import SecretsError

api_key = await ctx.secrets.get("OPENAI_API_KEY")
if not api_key:
    raise SecretsError(
        secret_name="OPENAI_API_KEY",
        message="OpenAI API key is required. Add it in your Huitzo dashboard.",
    )
```

Use when: A user-configured secret is missing or invalid.

### ExternalAPIError — User's external API failed

```python
from huitzo_sdk.errors import ExternalAPIError

try:
    response = await ctx.http.get(f"https://api.example.com/data")
except Exception as e:
    raise ExternalAPIError(
        service="example-api",
        message=f"Failed to fetch data: {e}",
    )
```

Use when: An API the user configured (not Huitzo platform services) fails.

### StorageError — Storage operation failed

```python
from huitzo_sdk.errors import StorageError

try:
    await ctx.storage.set("results", data)
except Exception as e:
    raise StorageError(
        operation="set",
        key="results",
        message=f"Failed to store results: {e}",
    )
```

## Retryable vs Non-Retryable

| Exception | Retryable | Why |
|-----------|-----------|-----|
| `ValidationError` | No | User input won't change on retry |
| `CommandError` | No | Logic error, not transient |
| `TimeoutError` | **Yes** | May succeed with more time |
| `StorageError` | No | Usually indicates a real problem |
| `SecretsError` | No | Secret won't appear on retry |
| `ExternalAPIError` | No | User must fix their API config |
| `IntegrationError` | **Yes** | Platform services may recover |
| `LLMError` | **Yes** | LLM providers have transient failures |
| `RateLimitError` | **Yes** | Will succeed after cooldown |

The runtime uses the `retryable` flag on each exception to decide whether to retry.

## Rules

1. **Import from `huitzo_sdk.errors`** — never define your own exception hierarchy
2. **Never catch `Exception` broadly** — let the runtime handle unexpected errors
3. **Include actionable messages** — tell the user what to do, not just what went wrong
4. **Don't log and raise** — the runtime handles logging. Just raise.
5. **Use the most specific exception** — `SecretsError` over `CommandError` when a secret is missing

## Anti-Patterns

```python
# BAD: Catching everything
try:
    result = await do_work()
except Exception:
    return {"error": "something went wrong"}

# GOOD: Let it propagate
result = await do_work()  # Runtime catches unexpected errors

# BAD: Generic error
raise CommandError("Error")

# GOOD: Actionable message
raise CommandError("Analysis failed: input text contains no extractable entities")

# BAD: Custom exceptions
class MyPackError(Exception): ...

# GOOD: Use SDK exceptions
raise CommandError("...")
```
