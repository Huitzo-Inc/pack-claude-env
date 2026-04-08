---
description: Scaffold a new command with args model, function, test, and manifest entry
disable-model-invocation: true
---

# /add-command

Scaffold a new command for this Intelligence Pack.

## Steps

1. **Parse the command name from `$ARGUMENTS`**. The name should be in `verb-noun` kebab-case format (e.g., `analyze-text`, `generate-report`). If no name is provided, ask the user.

2. **Convert the command name** to a Python-safe identifier: replace hyphens with underscores (e.g., `analyze-text` → `analyze_text`).

3. **Identify the pack structure** by reading `huitzo.yaml` to get the namespace, and finding the `src/*/commands/` directory.

4. **Create the command file** at `src/{module_name}/commands/{command_identifier}.py`:

```python
"""
Module: {command_identifier}
Description: {command_name} command

Implements:
    - docs/sdk/commands.md
"""

from pydantic import BaseModel, Field

from huitzo_sdk import Context, command


class {ArgsClassName}(BaseModel):
    """Arguments for {command_name}."""
    # TODO: Define your arguments here
    input: str = Field(..., description="Input value")


@command("{command-name}", namespace="{namespace}")
async def {function_name}(args: {ArgsClassName}, ctx: Context) -> dict:
    """TODO: Describe what this command does."""
    # TODO: Implement command logic
    return {{"result": args.input}}
```

5. **Update the commands `__init__.py`** to export the new command function.

6. **Create a test file** at `tests/test_{command_identifier}.py`:

```python
"""
Module: test_{command_identifier}
Description: Tests for {command_name}

Implements:
    - docs/sdk/commands.md
"""

import pytest

from {module_name}.commands.{command_identifier} import {function_name}, {ArgsClassName}


class Test{CommandClassName}:
    """Tests for {function_name}."""

    @pytest.mark.asyncio
    async def test_basic(self):
        """Test basic execution."""
        args = {ArgsClassName}(input="test")
        result = await {function_name}(args)
        assert "result" in result

    def test_args_validation(self):
        """Test argument validation."""
        from pydantic import ValidationError
        # TODO: Test validation rules
        args = {ArgsClassName}(input="valid")
        assert args.input == "valid"
```

7. **Update `huitzo.yaml`** to add the new command entry under `commands:`. The `entry_point` field is REQUIRED and tells the runtime where to find the command function:

```yaml
  - name: {command-name}
    description: TODO - describe this command
    entry_point: "{module_name}.commands.{command_identifier}:{function_name}"
    enabled: true
```

Key naming rules for `entry_point`:
- Uses underscores for both the module path and the function name (e.g., `"claims_v1.commands.save_visit:save_visit"`)
- Never use hyphens in the Python module path or function name — they are invalid Python identifiers

**Do NOT edit `pyproject.toml` directly.** It is auto-generated from `huitzo.yaml`. Entry points are regenerated automatically on `huitzo pack build` and `huitzo pack dev`, or manually via `huitzo pack sync`.

9. **Run a quick validation** to make sure everything compiles:

```bash
source venv/bin/activate && python -c "from {module_name}.commands.{command_identifier} import {function_name}"
```

10. **Print a summary** of what was created and what the developer should do next (implement the command logic, define args, write tests).
