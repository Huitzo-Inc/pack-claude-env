---
name: scaffold-dashboard
description: Scaffold a new dashboard component or page with docs, styles, a test file, and a traceability header.
argument-hint: "[page] <Name>"
disable-model-invocation: true
---

# /scaffold-dashboard

Scaffold a dashboard component or page following the docs-first workflow.

## Usage

```
/scaffold-dashboard <ComponentName>
/scaffold-dashboard page <PageName>
```

If no type is given, default to `component`. `Name` should be PascalCase
(e.g. `QuestionCard`, `ProjectSetup`).

## Steps

1. **Parse arguments** from `$ARGUMENTS`. If the first word is `page`,
   scaffold a page; otherwise a component.

2. **Read the manifest** — check `huitzo-dashboard.yaml` for `namespace` and
   `pack_dependencies` so the component's command calls target the right
   commands.

3. **Docs-first gate**:
   - Component: `docs/components/{Name}.md`
   - Page: `docs/pages/{Name}.md`
   - If missing, draft it first (or ask the user to). Cover: what it does,
     what props it takes / what commands it calls, what user interactions it
     supports, and what states it has (loading, error, empty, success).

4. **Pick an implementation strategy** before writing code:
   - **`Dashboard` template** (`@huitzo/dashboard-sdk-react`) — the page is
     "run one command, render its result" (metrics, a table, a list, a
     notice). Least code, consistent chrome via `TemplateFrame`.
   - **`Form` template** — the page collects structured input and submits it
     to a command. Supports `text`/`email`/`password`/`textarea`/`number`/
     `select` fields (no `file` field).
   - **Hand-rolled `App.tsx` + hooks** — anything with custom layout,
     multiple independent commands on one screen, or a design the templates'
     frame doesn't fit. Use `useCommand` directly.
   See the `huitzo-dashboard-sdk` skill for exact template props.

5. **Create the source file**:
   - Component: `src/components/{Name}/{Name}.tsx`
   - Page: `src/pages/{Name}.tsx`
   - Traceability header:
     ```typescript
     /**
      * Module: {Name}
      * Description: <what it does>
      *
      * @implements docs/components/{Name}.md
      */
     ```
     (`docs/pages/{Name}.md` for a page.)
   - Include the props/args interface and placeholder JSX; if it calls a
     command, use `useCommand` (or `useTemplateCommand` inside a template).

6. **Create styles**:
   - Component: `src/components/{Name}/{Name}.module.css` (CSS Modules), or
     plain CSS scoped under `.huitzo-dashboard` if this project follows that
     convention instead — never a bare global selector either way. See
     `dashboard-design.md` for tokens and `hz-*` primitives before writing
     any custom rule.

7. **Create the test file**:
   - Component: `src/components/{Name}/{Name}.test.tsx`
   - Page: `src/pages/{Name}.test.tsx`
   - Traceability header, a render test wrapped in `HuitzoProvider` (see
     `react-patterns.md` for the mock context), and TODO comments for
     interaction tests. If the project has no test tooling yet, see
     `/test-dashboard` for the minimal Vitest setup first.

8. **Update exports** — add to `src/components/index.ts` or
   `src/pages/index.ts` if the project keeps one.

9. **Report** what was created and next steps: review the doc, implement the
   remaining logic, write interaction tests, run `/test-dashboard`.
