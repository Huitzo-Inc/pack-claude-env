# Intelligence Pack Development

## Build / Test / Lint

```bash
# Activate virtual environment
source venv/bin/activate

# Run tests
pytest -v

# Lint and format
ruff check .
ruff format .

# Type checking
mypy --strict src/

# Validate pack structure
huitzo validate
```

## SDK Import Convention

```python
from huitzo_sdk import command, Context
from huitzo_sdk.errors import ValidationError, CommandError, SecretsError
```

Never import from internal SDK modules (e.g., `huitzo_sdk.command`). Always use the top-level `huitzo_sdk` namespace.

## Command Pattern

```python
from pydantic import BaseModel
from huitzo_sdk import command, Context

class MyArgs(BaseModel):
    """Pydantic model for argument validation."""
    name: str
    count: int = 1

@command("action-noun", namespace="my-pack", timeout=60)
async def action_noun(args: MyArgs, ctx: Context) -> dict:
    """Docstring becomes help text in the marketplace."""
    return {"result": "value", "count": args.count}
```

**Key rules:**
- Commands are always `async`
- First param is a Pydantic `BaseModel` subclass (validated automatically)
- Second param is `Context` (injected by runtime)
- Return type is `dict` (serialized as JSON to the caller)
- Name format: `"verb-noun"` (kebab-case)
- Namespace matches your pack name

## Context Services

The `ctx` object provides platform services at runtime:

| Service | Access | Description |
|---------|--------|-------------|
| LLM | `ctx.llm` | Call language models |
| Email | `ctx.email` | Send emails |
| HTTP | `ctx.http` | Make HTTP requests (domain-restricted) |
| Telegram | `ctx.telegram` | Send Telegram messages |
| Files | `ctx.files` | File storage operations |

These are injected by the Huitzo backend. In tests, mock them.

## Manifest (huitzo.yaml)

Every command in `src/*/commands/` must be listed in `huitzo.yaml`:

```yaml
pack:
  name: my-pack
  namespace: my-namespace
  version: 0.0.0
  description: What this pack does
  visibility: private
  author: Your Name

commands:
  - name: action-noun
    description: What this command does
    enabled: true
```

## Error Handling

Use structured exceptions from `huitzo_sdk.errors`:

| Exception | When to use |
|-----------|-------------|
| `ValidationError` | User input is invalid |
| `CommandError` | General command failure |
| `SecretsError` | Required secret is missing |
| `ExternalAPIError` | User-configured external API failed |
| `TimeoutError` | Operation exceeded timeout |
| `StorageError` | Storage operation failed |

Never catch `Exception` broadly. Let the runtime handle unexpected errors.

## Traceability Headers

Every source file must reference the documentation it implements:

```python
"""
Module: module_name
Description: Brief description

Implements:
    - docs/sdk/commands.md
"""
```

## File Organization

```
my-pack/
├── src/my_pack/
│   ├── __init__.py
│   └── commands/
│       ├── __init__.py      # Export all commands
│       └── my_command.py    # One file per command
├── tests/
│   ├── conftest.py
│   └── test_my_command.py   # One test file per command
├── huitzo.yaml              # Pack manifest
├── pyproject.toml
└── CONSTITUTION.md
```

## Code Quality

- All code must pass `ruff check .` and `ruff format --check .`
- All code must pass `mypy --strict src/`
- All commands must have corresponding tests
- No backwards compatibility hacks — refactor cleanly
