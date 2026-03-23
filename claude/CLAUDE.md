# Intelligence Pack & Dashboard Development

## Project Type

Detect from files present:
- `huitzo.yaml` → Intelligence Pack (Python commands)
- `huitzo-dashboard.yaml` → Dashboard (React micro-frontend in Huitzo Hub)
- `packs/` + `dashboards/` → Huitzo Application (full-stack, see `docs/guides/application-structure.md`)
- Both manifests in same dir → Full-stack project (single-project variant)

## Workflow: Documentation First

**Every feature starts with documentation. Code implements the documented contract.**

1. **Spec** (new projects) — `/draft-spec` for structured requirements gathering
2. **Document** — `/draft-docs <name>` for commands, write `docs/components/` or `docs/pages/` for dashboards
3. **Implement** — `/add-command <name>` for pack commands, `/scaffold-dashboard <name>` for dashboard components
4. **Test** — `/test-pack` or `/test-dashboard`
5. **Validate** — `/validate-pack` or `/validate-dashboard`
6. **Lint** — `/lint-and-fix`

## Documentation Server (MCP)

The `pack-docs` MCP server makes `docs/` searchable within Claude Code. Tools: `search_documentation`, `get_document`, `navigate_to`, `get_table_of_contents`, `search_by_tags`, `get_all_tags`.

### Documentation Structure

```
docs/
├── README.md                # Project overview
├── spec/                    # Specifications (from /draft-spec)
├── commands/                # Pack command docs (one per command)
│   ├── README.md
│   └── {command-name}.md
├── components/              # Dashboard component docs
│   └── {ComponentName}.md
├── pages/                   # Dashboard page docs
│   └── {PageName}.md
└── guides/
    └── getting-started.md
```

Every doc file uses YAML frontmatter: `title`, `tags`, `category`, `order`.

---

## Pack Development (Python)

### SDK Imports

```python
from huitzo_sdk import command, Context
from huitzo_sdk.errors import ValidationError, CommandError, SecretsError
```

Never import from internal SDK modules.

### Command Pattern

```python
from pydantic import BaseModel, Field
from huitzo_sdk import command, Context

class MyArgs(BaseModel):
    input: str = Field(..., description="Input text")
    limit: int = Field(default=10, ge=1, le=100)

@command("verb-noun", namespace="pack-name", timeout=60)
async def verb_noun(args: MyArgs, ctx: Context) -> dict:
    """Docstring becomes marketplace help text."""
    return {"result": "value"}
```

**Rules:** Always `async`. Pydantic `BaseModel` args with `Field` descriptions. Returns `dict`. Name format: `verb-noun` kebab-case. Namespace matches `huitzo.yaml`.

### Context Services

| Service | Access | Purpose |
|---------|--------|---------|
| LLM | `ctx.llm` | Language model calls |
| HTTP | `ctx.http` | External APIs (domain-restricted) |
| Email | `ctx.email` | Send emails |
| Storage | `ctx.storage` | Tenant-isolated key-value storage |
| Files | `ctx.files` | File storage |
| Secrets | `ctx.secrets` | User-provided secrets |
| Telegram | `ctx.telegram` | Telegram messages |

### Error Handling

Use `huitzo_sdk.errors`: `ValidationError`, `CommandError`, `SecretsError`, `ExternalAPIError`, `TimeoutError`, `StorageError`. Never catch `Exception` broadly.

### Quality Gates

```bash
pytest -v && ruff check . && ruff format --check . && mypy --strict src/ && huitzo validate
```

---

## Dashboard Development (React)

### Hub Contract

Dashboards are React micro-frontends loaded by Huitzo Hub. The contract:

```typescript
// src/main.tsx — production entry point
export function mount(container: HTMLElement, context: HuitzoContext): void;
export function unmount(container: HTMLElement): void;
```

`HuitzoContext` provides: `apiUrl`, `token`, `slug`, `sdkVersion`, `user`, `navigate()`, `navigateToHub()`, `showNotification()`, `on()`, `emit()`.

### Key Rules

- CSS Modules only (`.module.css`) — no global CSS that bleeds into Hub
- All API calls through `useCommand` hook — never raw fetch
- `ErrorBoundary` at root with `context.navigateToHub()` fallback
- No `document.body` manipulation or `window.location` changes
- Bundle all dependencies (no Vite externals)
- React 19.2, functional components, TypeScript strict mode

### Dashboard SDK Hooks

| Hook | Purpose |
|------|---------|
| `useCommand` | Execute pack commands |
| `useHuitzo` | Client, auth state, pack status |
| `useRealtime` | WebSocket subscriptions |
| `useHubNavigation` | Navigate between dashboards |
| `useHubContext` | Hub URL, slug, theme |
| `useHubActions` | Notifications, dialogs |

### Manifest

`huitzo-dashboard.yaml` defines name, namespace, version, visibility, `pack_dependencies`, and build config. See `dashboard-manifest` rule for full spec.

### Quality Gates

```bash
npm test && npx tsc --noEmit && huitzo dashboard validate
```

---

## Shared Rules

### Traceability Headers (REQUIRED on all source files)

**Python:**
```python
"""
Module: module_name
Description: Brief description

Implements:
    - docs/commands/verb-noun.md
"""
```

**TypeScript:**
```typescript
/**
 * @module ComponentName
 * @description Brief description
 * @implements docs/components/ComponentName.md
 */
```

### Code Quality

- All source files must have traceability headers
- All commands/components must have docs written FIRST
- No backwards compatibility hacks — refactor cleanly
- No hardcoded secrets or API keys
