---
paths:
  - "src/**/*.py"
  - "tests/**/*.py"
---

# SDK Patterns

## Imports

Always import from the top-level `huitzo_sdk` namespace:

```python
from huitzo_sdk import command, Context
from huitzo_sdk.errors import ValidationError, CommandError
```

Never import from internal modules like `huitzo_sdk.command` or `huitzo_sdk.context`.

## The @command Decorator

```python
@command("verb-noun", namespace="pack-name", timeout=60)
async def verb_noun(args: ArgsModel, ctx: Context) -> dict:
    """Docstring becomes help text."""
    return {"key": "value"}
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str` | required | Command name in `verb-noun` kebab-case |
| `namespace` | `str` | required | Must match pack name in `huitzo.yaml` |
| `version` | `str` | `"1.0.0"` | Semantic version of this command |
| `timeout` | `int` | `60` | Max execution time in seconds |
| `retries` | `int` | `3` | Number of retry attempts on failure |
| `retry_backoff` | `float` | `1.0` | Backoff multiplier between retries |
| `retry_max_wait` | `int` | `60` | Maximum wait between retries in seconds |
| `queue` | `str` | `"default"` | Worker queue for execution |
| `output_format` | `str` | `"auto"` | Output format hint |
| `description` | `str\|None` | `None` | Override docstring description |

### Function Signature Rules

1. **Always async** — commands are `async def`
2. **First parameter**: Pydantic `BaseModel` subclass for validated args
3. **Second parameter**: `Context` — injected by runtime
4. **Return type**: `dict` — serialized as JSON

## Pydantic Args Models

Define a `BaseModel` subclass for each command's arguments:

```python
from pydantic import BaseModel, Field

class AnalyzeArgs(BaseModel):
    """Arguments for the analyze command."""
    text: str = Field(..., description="Text to analyze")
    language: str = Field(default="en", description="Language code")
    max_tokens: int = Field(default=1000, ge=1, le=10000)
```

- Use `Field(...)` for required args (no default)
- Use `Field(default=...)` for optional args
- Add `description` to every field — it appears in marketplace docs
- Use Pydantic validators (`ge`, `le`, `pattern`, etc.) for input constraints

## Context Services

The `ctx` object provides platform services injected at runtime:

```python
# LLM — call language models
response = await ctx.llm.chat(
    model="claude-sonnet-4-20250514",
    messages=[{"role": "user", "content": "Hello"}],
)

# HTTP — make requests (domain must be declared in manifest)
data = await ctx.http.get("https://api.example.com/data")

# Email — send emails
await ctx.email.send(to="user@example.com", subject="Report", body=body)

# Telegram — send messages
await ctx.telegram.send_message(chat_id=123, text="Alert!")

# Files — file storage
await ctx.files.upload(path="reports/output.pdf", content=pdf_bytes)
```

**In tests, these are not available.** Mock them (see testing rules).

## Return Values

Commands return a `dict` that gets serialized as JSON:

```python
# Good — structured, predictable
return {"analysis": result, "confidence": 0.95, "tokens_used": 150}

# Bad — unstructured
return {"output": "some string that could be anything"}
```

- Use consistent key names across commands
- Include metadata when useful (tokens used, processing time, confidence)
- Keep response payloads reasonably sized

## Class-Based Commands

For commands with lifecycle hooks, use `HuitzoCommand`:

```python
from huitzo_sdk import HuitzoCommand, Context

class MyCommand(HuitzoCommand):
    name = "process-data"
    namespace = "my-pack"
    timeout = 120

    async def execute(self, args: ProcessArgs, ctx: Context) -> dict:
        return {"result": "done"}

    def on_start(self, args):
        """Called when command starts."""

    def on_complete(self, result):
        """Called after successful completion."""

    def on_error(self, error):
        """Called on failure."""
```

Use class-based commands only when you need lifecycle hooks. For most cases, the `@command` decorator is simpler and preferred.

## Command Registration

`huitzo.yaml` is the **single source of truth** for command registration. Every command must include an `entry_point` field:

```yaml
commands:
  - name: analyze-text
    description: Analyze text content
    entry_point: "my_pack.commands.analyze_text:analyze_text"
    enabled: true
```

The `entry_point` format is `module.path:function_name` using Python identifiers (underscores, not hyphens).

**Do NOT edit `pyproject.toml` directly.** It is auto-generated from `huitzo.yaml`:
- `huitzo pack build` and `huitzo pack dev` regenerate it automatically
- `huitzo pack sync` regenerates it on demand
