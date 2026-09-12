---
name: add-command
description: Scaffold a new pack command — docs, args model, function, test, and manifest entry.
argument-hint: "<verb-noun>"
disable-model-invocation: true
---

# /add-command

Scaffold a new command for this Intelligence Pack. Docs-first: a command's
documented contract must exist before its implementation.

## Steps

1. **Parse the command name from `$ARGUMENTS`** — `verb-noun` kebab-case
   (e.g. `analyze-text`). Ask the user if it's missing.

2. **Docs-first gate.** Check `docs/commands/{name}.md`:
   - Exists → read it. It is the implementation contract.
   - Missing → stop and run `/draft-docs {name}` first (or ask the user to),
     then come back to this skill. Do not scaffold a command with no
     documented contract.

3. **Read `huitzo.yaml`** for `pack.namespace` and the `src/*/commands/`
   layout.

4. **Prefer the real CLI, when `huitzo` is on PATH:**

   ```bash
   huitzo pack add-command {name} --description "..." --pydantic
   ```

   Never pass `--queue default` — the flag offers it, but the manifest schema
   rejects `queue: "default"` ❌ (and `auto` ❌). Omit `--queue` for the `medium`
   default, or pass `fast`/`medium`/`long` explicitly.

5. **Manual fallback** (no CLI, or CLI unavailable) — produce the same files
   the CLI would:

   `src/{module_name}/commands/{command_file}.py`:

   ```python
   """
   Module: {command_file}
   Description: {one-line summary, from the doc}

   Implements:
       - docs/commands/{command_file}.md#{name}
   """

   from pydantic import BaseModel, Field

   from huitzo_sdk import Context, command


   class {ArgsClass}(BaseModel):
       """Arguments for {name}."""
       # TODO: fields per the documented contract
       input: str = Field(..., description="Input value")


   @command("{name}", namespace="{namespace}")
   async def {command_func}(args: {ArgsClass}, ctx: Context) -> dict:
       """{one-line summary, from the doc}."""
       # TODO: implement per docs/commands/{command_file}.md
       return {"result": args.input}
   ```

   `tests/test_{command_file}.py` — follow the pack's existing test pattern
   (a bare `Context()` for pure-logic tests, or a hand-built mock `Context`
   for a test that exercises a `ctx.*` service — see the `huitzo-sdk` skill
   for what each service needs mocked and which ones are async).

   `huitzo.yaml` — add under `commands:`:

   ```yaml
     - name: {name}
       description: "{one-line summary}"
       entry_point: "{module_name}.commands.{command_file}:{command_func}"
   ```

   Add `timeout`/`queue` only if the command needs a non-default value, and
   make sure they match the `@command` decorator exactly. **Never add
   `enabled:`** — the field doesn't exist; an unknown key fails the whole
   manifest load. If the command needs a new permission (e.g. `http:request`),
   add it to both `permissions:` and `policy.allowed_actions`, plus its
   backing `services.*` block — see the `pack-manifest` rule.

6. **Sync and validate:**

   ```bash
   huitzo pack sync       # regenerate pyproject.toml from huitzo.yaml
   huitzo pack validate   # or /validate-pack if the CLI isn't available
   ```

7. **Summarize** what was created and what's still TODO (args fields, command
   body, test assertions) against the doc's contract.
