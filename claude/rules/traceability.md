# Traceability Rules

## Requirement

Every source file must include a traceability header referencing the documentation it implements.

## Format

```python
"""
Module: module_name
Description: Brief description of what this module does

Implements:
    - docs/sdk/commands.md

See Also:
    - docs/sdk/context.md (for Context API usage)
"""
```

## Fields

| Field | Required | Description |
|-------|----------|-------------|
| `Module` | Yes | Module name (matches filename without extension) |
| `Description` | Yes | One-line description |
| `Implements` | Yes | List of doc paths this file implements |
| `See Also` | No | Related documentation for context |

## Common References

| Your code does... | Reference |
|-------------------|-----------|
| Defines a command | `docs/sdk/commands.md` |
| Uses Context | `docs/sdk/context.md` |
| Handles errors | `docs/sdk/error-handling.md` |
| Uses storage | `docs/sdk/storage.md` |
| Uses integrations | `docs/sdk/integrations.md` |

## Test Files

Test files also need headers:

```python
"""
Module: test_analyze
Description: Tests for the analyze command

Implements:
    - docs/sdk/commands.md
"""
```

## TypeScript / React Files

Dashboard source files use JSDoc-style traceability:

```typescript
/**
 * @module ComponentName
 * @description Brief description of what this component does
 *
 * @implements docs/components/ComponentName.md
 *
 * @see docs/pages/PageName.md (for page context)
 */
```

### Common Dashboard References

| Your code does... | Reference |
|-------------------|-----------|
| Defines a component | `docs/components/{Name}.md` |
| Defines a page | `docs/pages/{Name}.md` |
| Implements mount/unmount | `docs/README.md` |
| Uses SDK hooks | `docs/guides/sdk-usage.md` |

## Validation

```bash
# Check all files have traceability headers
# Pack:
huitzo validate

# Dashboard:
huitzo dashboard validate
```
