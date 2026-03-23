---
description: Scaffold a new dashboard component or page with docs, CSS Module, and test file
---

# /scaffold-dashboard

Scaffold a dashboard component or page following the docs-first workflow.

## Usage

```
/scaffold-dashboard <ComponentName>
/scaffold-dashboard page <PageName>
```

If no type is specified, defaults to `component`.

## Steps

1. **Parse arguments** from `$ARGUMENTS`:
   - If first word is `page`, scaffold a page. Otherwise, scaffold a component.
   - Name should be PascalCase (e.g., `QuestionCard`, `ProjectSetup`).

2. **Read manifest** — Check `huitzo-dashboard.yaml` for namespace and pack dependencies.

3. **Check documentation exists** (docs-first enforcement):
   - Component: `docs/components/{Name}.md`
   - Page: `docs/pages/{Name}.md`
   - **If documentation doesn't exist**, draft it first using the appropriate template from the documentation rules. Ask the user the key questions:
     - What does this component/page do?
     - What props does it accept? (components) / What commands does it use? (pages)
     - What user interactions does it support?
     - What states does it have? (loading, error, empty)

4. **Create the source file**:
   - Component: `src/components/{Name}/{Name}.tsx`
   - Page: `src/pages/{Name}.tsx`
   - Include traceability header: `@implements docs/components/{Name}.md` or `@implements docs/pages/{Name}.md`
   - Include basic structure with imports, props interface, and placeholder JSX

5. **Create CSS Module** (components only):
   - `src/components/{Name}/{Name}.module.css`
   - Include a `.container` class as starting point

6. **Create test file**:
   - Component: `src/components/{Name}/{Name}.test.tsx`
   - Page: `src/pages/{Name}.test.tsx`
   - Include traceability header, basic render test, and TODO comments for interaction tests

7. **Update exports**:
   - Component: Add to `src/components/index.ts`
   - Page: Add to `src/pages/index.ts`

8. **Report** what was created and what the developer should do next:
   - Review the documentation
   - Implement the component logic
   - Write interaction tests
   - Run `npm test` to verify
