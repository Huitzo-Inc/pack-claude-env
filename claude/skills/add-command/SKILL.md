---
name: add-command
description: Scaffold a new pack command — docs, args and return models, function, test, manifest entry, and the stage entry when it is a pipeline stage.
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
   huitzo pack add-command {name} --description "..."
   ```

   Never pass `--queue default` — the flag offers it, but the manifest schema
   rejects `queue: "default"` ❌ (and `auto` ❌). Omit `--queue` for the `medium`
   default, or pass `fast`/`medium`/`long` explicitly.

   Then open the generated file and make it match the shape in step 5: a
   typed args model **and** a typed return model. If the scaffold returns a
   bare `dict`, replace it with a return model.

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
       # TODO: fields per the documented contract, each with its limits
       input: str = Field(..., max_length=10_000, description="Input value")


   class {ResultClass}(BaseModel):
       """What {name} returns."""
       # TODO: fields per the documented contract
       result: str = Field(..., description="Result value")


   @command("{name}", namespace="{namespace}")
   async def {command_func}(args: {ArgsClass}, ctx: Context) -> {ResultClass}:
       """{one-line summary, from the doc}."""
       # TODO: implement per docs/commands/{command_file}.md
       return {ResultClass}(result=args.input)
   ```

   A typed args model and a typed return model are the default shape. Model
   calls go through `ctx.llm` only; never call a model-provider host through
   `ctx.http`.

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

6. **If the doc has a stage table, the command is one stage of a pipeline.**
   One command is one step. Do not put the other steps in this command, and
   do not chain them with `ctx.commands.execute` (nested calls are not
   recorded as steps on the run page). Scaffold one command per stage, then
   declare the chain in `huitzo.yaml`:

   ```yaml
   pipelines:
     {pipeline-name}:
       description: "{one-line summary of the whole flow}"
       stages:
         - name: extract            # short verb — the label on the run page
           command: "{namespace}:extract-claim"
         - name: assess
           command: "{namespace}:assess-risk"
         - name: decide
           command: "{namespace}:decide-route"
   ```

   - Each stage's return model is the next stage's args model, or carries
     every field that model requires.
   - Every model call is `ctx.llm` inside the stage that owns it; retries
     and fallbacks stay inside that stage.
   - Add the stage-chain test from the `testing` rule to `tests/`.

7. **Sync and validate:**

   ```bash
   huitzo pack sync                # regenerate pyproject.toml from huitzo.yaml
   huitzo pack validate --strict   # or /validate-pack if the CLI isn't available
   ```

   The strict form also fails on a stage ref that names no command in the
   pack and on a stage whose return model does not fit the next stage's args
   model.

8. **Summarize** what was created and what's still TODO (args and return
   fields, command body, test assertions, stage entry and chain test) against
   the doc's contract.
