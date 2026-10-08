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

4. **Ask the user the six key questions** (skip any already answered):
   - What problem does this command solve?
   - What are its main arguments?
   - What does it return?
   - What `ctx.*` services does it need (LLM, HTTP, email, files, ...)?
   - Any external APIs or user secrets required?
   - Is the work one step or several? Several steps (more than one model
     call, a model call plus an external effect, steps that fail separately)
     means a pipeline: the doc gets a **Stages** table, and each stage
     command gets its own doc.

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

   Write the Returns block as the fields of the return model (the
   implementation returns a typed model, not a free-form dict). Errors name
   the field and the fix; no error message repeats user text.

   **Multi-step commands add a Stages section** between Returns and Errors.
   This table is what the run page is read against — it shows one step per
   stage, labelled with the stage name, with the model calls that stage made:

   ```markdown
   ## Stages

   Pipeline: `{pipeline-name}` (declared under `pipelines:` in `huitzo.yaml`).

   | Stage | Command | Input model | Output model | Model calls | Retries / fallback | Errors |
   |-------|---------|-------------|--------------|-------------|--------------------|--------|
   | `extract` | `extract-claim` | `ExtractArgs` | `ExtractedClaim` | 1, always | none | `LLMError` propagates |
   | `assess` | `assess-risk` | `ExtractedClaim` | `AssessedClaim` | none (fixed rules) | none | — |
   | `decide` | `decide-route` | `AssessedClaim` | `RoutedClaim` | 1, only when risk is `medium` | falls back to `manual-review` if the model call fails | — |

   Checked before the pipeline starts: `policy_id` exists (`ValidationError`).
   ```

   Rules for the table: stage names are short verbs; a stage is a unit with
   its own failure mode, external effect or model call; each output model
   carries everything later stages need; the "Model calls" column says when
   a stage calls a model and when it does not, so a run with no model-call
   mark on that step can be interpreted; retries and fallbacks belong to the
   stage that owns them. A stage failure reaches the caller as
   `PipelineError`, so list under the table any caller input that is checked
   before the pipeline starts and the error it raises.

6. **Update `docs/commands/README.md`** (create it if it doesn't exist) to
   list the new command.

7. **Summarize and hand off:**

   ```
   Documentation drafted for {name}: docs/commands/{name}.md

   Next: /add-command {name} to scaffold the implementation.
   ```
