---
name: draft-docs
description: Draft a command's documentation before implementation (docs-first workflow).
argument-hint: "<verb-noun>"
disable-model-invocation: true
---

# /draft-docs

Write the documented contract for a command *before* any code exists.
Documentation defines the contract; implementation (`/add-command`) follows it.

## Steps

1. **Parse the command name from `$ARGUMENTS`** — `verb-noun` kebab-case. Ask
   the user if it's missing.

2. **Read `huitzo.yaml`** for the pack's namespace and existing commands, and
   `docs/commands/README.md` (if present) for documentation conventions
   already in use.

3. **Check for overlap before writing anything new.** If a project docs MCP
   server is configured (tools like `search_documentation` and
   `get_table_of_contents`), use it to check whether an existing doc already
   covers this behavior. If those tools aren't available, `grep`/read
   `docs/commands/` directly.

4. **Ask the user the five key questions** (skip any already answered):
   - What problem does this command solve?
   - What are its main arguments?
   - What does it return?
   - What `ctx.*` services does it need (LLM, HTTP, email, files, ...)?
   - Any external APIs or user secrets required?

5. **Write `docs/commands/{name}.md`:**

   ```markdown
   ---
   title: {name}
   tags: [command]
   category: commands
   ---

   # {name}

   {One-line summary.}

   ## Arguments

   | Argument | Type | Required | Default | Description |
   |----------|------|----------|---------|-------------|
   | ... | ... | ... | ... | ... |

   ## Returns

   \`\`\`json
   {
     "field": "type — description"
   }
   \`\`\`

   ## Errors

   | Error | Condition | User action |
   |-------|-----------|-------------|
   | ... | ... | ... |

   ## Examples

   ### Basic usage
   Input: `{...}`
   Output: `{...}`
   ```

6. **Update `docs/commands/README.md`** (create it if it doesn't exist) to
   list the new command.

7. **Summarize and hand off:**

   ```
   Documentation drafted for {name}: docs/commands/{name}.md

   Next: /add-command {name} to scaffold the implementation.
   ```
