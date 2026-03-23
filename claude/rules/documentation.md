# Documentation Rules

## Documentation-First Principle

**Documentation is written BEFORE code. Always.**

The workflow is:
1. Draft documentation for the command in `docs/commands/{command-name}.md`
2. Review the documentation (is the contract clear? are arguments well-defined?)
3. Scaffold the command with `/add-command`
4. Implement the business logic based on the documented contract
5. Write tests that validate the documented behavior

If you're asked to implement a command that doesn't have documentation yet, write the documentation first.

## Documentation MCP Server

The pack includes a `your-docs-mcp` server configured to serve the `docs/` directory. Claude Code uses it automatically via `.claude/settings.json`.

Available MCP tools:
- `search_documentation` — Search docs by keyword
- `get_document` — Get a specific document by URI
- `navigate_to` — Navigate the documentation hierarchy
- `get_table_of_contents` — Get the full doc tree
- `search_by_tags` — Filter by tags
- `get_all_tags` — List all tags

## Documentation Structure

```
docs/
├── README.md              # Pack overview
├── commands/
│   ├── README.md          # Commands index
│   └── {command-name}.md  # One doc per command
└── guides/
    ├── README.md          # Guides index
    └── getting-started.md # Usage guide
```

## Required Frontmatter

Every documentation file needs YAML frontmatter:

```yaml
---
title: Human-Readable Title
tags: [command, relevant-category]
category: commands  # or guides
order: 1            # display order within category
---
```

## Command Documentation Template

Every command MUST have documentation at `docs/commands/{command-name}.md` containing:

1. **Overview** — What and why
2. **Arguments** — Table with type, required flag, default, description
3. **Validation Rules** — Business logic validation beyond type checking
4. **Returns** — JSON structure with field descriptions
5. **Errors** — Error types, conditions, and user actions
6. **Examples** — Real input/output pairs
7. **Context Services Used** — Which `ctx.*` services and why

## Traceability Connection

Source files reference documentation they implement:

```python
"""
Module: analyze_text
Description: Analyzes text using LLM

Implements:
    - docs/commands/analyze-text.md
"""
```

The documentation IS the spec. The code implements the spec.

## Dashboard Documentation

Dashboards follow the same docs-first principle. Document components and pages BEFORE implementing them.

### Documentation Structure (Dashboard)

```
docs/
├── README.md                # Dashboard overview
├── components/
│   ├── README.md            # Components index
│   └── {ComponentName}.md   # One doc per component
├── pages/
│   ├── README.md            # Pages index
│   └── {PageName}.md        # One doc per page
└── guides/
    └── getting-started.md
```

### Component Documentation Template

```markdown
---
title: ComponentName
tags: [component, category]
category: components
order: N
---

# ComponentName

Brief description.

## Props

| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `title` | string | yes | — | Display title |
| `onSubmit` | () => void | no | — | Submit callback |

## Commands Used

- `@scope/pack/command-name` — Purpose of this command in this component

## User Interactions

- Click "Submit" — Executes the command and displays result
- Press Escape — Closes the dialog

## States

- **Loading** — Shows spinner while command executes
- **Error** — Shows error message with retry button
- **Empty** — Shows placeholder when no data

## Accessibility

- Submit button is keyboard-focusable
- Error messages announced to screen readers
```

### Page Documentation Template

```markdown
---
title: PageName
tags: [page, category]
category: pages
order: N
---

# PageName

Brief description of what this page does.

## Purpose

Why this page exists and what user task it supports.

## Layout

Description of the page layout and key sections.

## Commands Used

- `@scope/pack/command-a` — Used for...
- `@scope/pack/command-b` — Used for...

## Navigation

- From: Hub home tile or sidebar
- To: Links to other pages/dashboards
```

## Quality Checklist

### Pack
- [ ] Every command has a doc in `docs/commands/`
- [ ] All docs have valid YAML frontmatter
- [ ] Arguments table is complete (type, required, default, description)
- [ ] Return value structure is documented as JSON with descriptions
- [ ] At least one concrete example with real input/output
- [ ] Error conditions documented with user-facing actions
- [ ] `docs/commands/README.md` lists all commands

### Dashboard
- [ ] Every page has a doc in `docs/pages/`
- [ ] Every reusable component has a doc in `docs/components/`
- [ ] Props are documented with types and descriptions
- [ ] Commands used are listed
- [ ] User interactions are documented
- [ ] Loading/error/empty states are described
