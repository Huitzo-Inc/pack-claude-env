# Traceability Rules

## Requirement

Every source file must include a traceability header referencing the documentation it implements. The referenced docs live **inside your project** (`docs/commands/`, `docs/components/`, `docs/pages/`) — not in the Huitzo monorepo. Each command/component you write has a matching doc that defines its contract (the docs-first workflow), and the source file points back at it.

## Format

```python
"""
Module: analyze_text
Description: Brief description of what this module does

Implements:
    - docs/commands/analyze-text.md

See Also:
    - docs/commands/README.md (for shared conventions)
"""
```

Match the doc path to the command name: `commands/analyze_text.py` implements `docs/commands/analyze-text.md`.

## Fields

| Field | Required | Description |
|-------|----------|-------------|
| `Module` | Yes | Module name (matches filename without extension) |
| `Description` | Yes | One-line description |
| `Implements` | Yes | List of project-local doc paths this file implements |
| `See Also` | No | Related documentation for context |

## Common References

All references point at docs **in your project**, mirroring your command/component layout:

| Your code does... | Reference |
|-------------------|-----------|
| Defines a command | `docs/commands/{command-name}.md` |
| Shared command conventions | `docs/commands/README.md` |
| Defines a dashboard component | `docs/components/{Name}.md` |
| Defines a dashboard page | `docs/pages/{Name}.md` |

## Test Files

Test files also need headers, pointing at the same doc the command they test implements:

```python
"""
Module: test_analyze
Description: Tests for the analyze command

Implements:
    - docs/commands/analyze-text.md
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
