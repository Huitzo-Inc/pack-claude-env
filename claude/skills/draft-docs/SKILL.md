---
description: Draft documentation for a new command before implementation (docs-first workflow)
disable-model-invocation: true
---

# /draft-docs

Draft documentation for a new command. This is the first step in the docs-first workflow — documentation defines the contract, implementation follows.

## Steps

1. **Parse the command name from `$ARGUMENTS`**. The name should be in `verb-noun` kebab-case format (e.g., `analyze-text`, `generate-report`). If no name is provided, ask the user.

2. **Read `huitzo.yaml`** to get the pack namespace and understand existing commands.

3. **Read `docs/commands/README.md`** to understand the existing documentation structure and any conventions used.

4. **Use the MCP documentation tools** to check for related existing documentation:
   - Use `search_documentation` to find related docs
   - Use `get_table_of_contents` to see the full structure

5. **Ask the user key questions** about the new command:
   - What problem does it solve?
   - What are the main arguments?
   - What does it return?
   - What context services does it need (LLM, HTTP, email, etc.)?
   - Any external APIs or secrets required?

6. **Create the command documentation** at `docs/commands/{command-name}.md` using this template:

```markdown
---
title: {Command Name}
tags: [command, {relevant-tags}]
category: commands
order: {next-order-number}
---

# {command-name}

{Brief description}.

## Overview

{Detailed description of what this command does, why it exists, and the problem it solves.}

## Arguments

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| ... | ... | ... | ... | ... |

### Validation Rules

- {argument}: {validation rule}

## Returns

\`\`\`json
{
  "field": "type — description"
}
\`\`\`

## Errors

| Error | Condition | User Action |
|-------|-----------|-------------|
| ... | ... | ... |

## Examples

### Basic usage
Input: `{...}`
Output: `{...}`

## Context Services Used

- `ctx.{service}` — {what it's used for}
```

7. **Update `docs/commands/README.md`** to include the new command in the list.

8. **Print a summary** of what was documented and remind the user that implementation comes next:
   ```
   Documentation drafted for {command-name}:
     docs/commands/{command-name}.md

   Next steps:
     1. Review the documentation
     2. Use /add-command {command-name} to scaffold the implementation
     3. Implement the business logic based on the documentation
   ```
