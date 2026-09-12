---
name: huitzo-init
description: Bootstrap or repair this project's Huitzo memory layer (rules, hooks, CLAUDE.md/AGENTS.md managed blocks, CONSTITUTION.md, docs MCP entry). Use after cloning, updating, or installing the plugin.
argument-hint: "[--yes] [--profile pack-only|dashboard-only|full-stack]"
disable-model-invocation: true
---

# /huitzo-init

Bring this project's `.claude/` memory layer up to date with the Huitzo developer
environment, without ever touching a file the developer already has. Safe to run
after every clone, after the environment updates, and right after installing the
plugin. Running it twice in a row changes nothing (idempotent).

Never overwrites an existing file. Never writes `.claude/settings.json`. Never runs
`git`. The only files this skill ever creates or edits are: `.claude/rules/*.md`,
`.claude/hooks/*.sh`, `CLAUDE.md`, `AGENTS.md`, `CONSTITUTION.md`, `.mcp.json`.

## Steps

### 1. Parse arguments

`$ARGUMENTS` may contain `--yes` (skip the confirmation prompt) and/or
`--profile <pack-only|dashboard-only|full-stack>` (skip profile detection).

### 2. Locate the environment source (read-only — never modify it)

`ENV_ROOT = ${CLAUDE_PLUGIN_ROOT}` and `SKILL_DIR = ${CLAUDE_SKILL_DIR}` — Claude Code
substitutes both placeholders into this skill body before the model ever reads it, so
these two lines already hold their real values (or don't) by the time you get here.

- If `ENV_ROOT` still reads literally as a `${...}` placeholder (the substitution did
  not happen), this is the **seed channel**: the project already has its own copy of
  the environment. Source = `.claude` (the copy the CLI already placed there); the
  project's `.claude/` is the `.../.claude/skills/huitzo-init` ancestor of `SKILL_DIR`
  (strip the trailing `/skills/huitzo-init` to get it). Copying "from" `.claude/rules/`
  and `.claude/hooks/` to themselves is inherently a no-op — in this channel the useful
  work is steps 5–7, not the file copies in step 4.
- Otherwise, this is the **plugin channel**: `ENV_ROOT` is the plugin's install
  directory, source = `"$ENV_ROOT/claude"`. The project's `.claude/` is the ordinary
  `.claude/` at the project root.

### 3. Detect the profile (skip if `--profile` was given)

| Marker present | Profile |
|---|---|
| `huitzo.yaml` (root or `pack/`) and no dashboard manifest | `pack-only` |
| `huitzo-dashboard.yaml` (root or `dashboard/`) and no pack manifest | `dashboard-only` |
| Both, or `packs/`/`dashboards/` present, or nothing detected yet | `full-stack` |

### 4. Compute the plan

For each candidate file below, decide one action: **create** (destination
missing), **skip-exists** (destination already present — never touched),
**update-managed-block** (destination exists; only the block between
`<!-- huitzo:begin -->` / `<!-- huitzo:end -->` changes), or **merge**
(`.mcp.json` only).

- **Rules** — every `<source>/rules/*.md` filtered by profile, into
  `.claude/rules/<name>.md`. `00-huitzo-core.md` is always included.
  - `pack-only` drops: `hub-contract.md`, `react-patterns.md`,
    `dashboard-design.md`, `dashboard-manifest.md`.
  - `dashboard-only` drops: `sdk-patterns.md`, `error-handling.md`,
    `pack-manifest.md`. (`testing.md` applies to both — never dropped.)
  - `full-stack` drops nothing.
- **Hooks** — `<source>/hooks/*.sh` into `.claude/hooks/`, but **only in the
  seed channel**. In the plugin channel, skip the rest of these hooks entirely and
  say why: the plugin already runs them itself (via `hooks/hooks.json` →
  `${CLAUDE_PLUGIN_ROOT}/claude/hooks/*.sh`) — copying them into `.claude/` would
  just leave an inert, unused second copy. The one exception, in **every** channel
  including plugin: `docs-mcp.sh` and the `_lib.sh` it sources — copy both into
  `.claude/hooks/` when they are missing (create the directory if needed) and
  `chmod +x` them; if present they are left alone like every other file (delete
  them to receive a newer version). The
  reason is the `.mcp.json` entry below: its `command` is a plain path Claude Code
  spawns directly, and a project-scoped `.mcp.json` cannot reference
  `${CLAUDE_PLUGIN_ROOT}` (there is no "current plugin" for it to resolve against),
  so the hook these two files implement must exist under the project's own
  `.claude/hooks/` regardless of channel.
- **`CLAUDE.md`** (project root) — create it from
  `templates/CLAUDE.md.tmpl` if the file does not exist; if it exists, replace
  only the `<!-- huitzo:begin -->...<!-- huitzo:end -->` block (create the
  markers at the end of the file if they are not already present). Everything
  else in the file is untouched.
- **`AGENTS.md`** (project root) — same managed-block treatment, using
  `templates/AGENTS.md.tmpl`.
- **`CONSTITUTION.md`** (project root) — copy verbatim from
  `<ENV_ROOT>/CONSTITUTION.md` if the project does not already have one.
- **`.mcp.json`** (project root) — only if `docs/` exists in the project.
  Create the file from `templates/mcp.json.tmpl` if absent; if it exists,
  merge in the `pack-docs` key only if that key is not already present (never
  touch any other key in the file). The command is the **same string in every
  channel**: `"./.claude/hooks/docs-mcp.sh"`. Never write
  `${CLAUDE_PLUGIN_ROOT}/claude/hooks/docs-mcp.sh` here — `.mcp.json` commands
  are spawned as plain paths and Claude Code does not expand
  `${CLAUDE_PLUGIN_ROOT}` (or any variable) inside a project-scoped
  `.mcp.json`; that spelling fails with `ENOENT` plus a "Missing environment
  variables" warning. `templates/mcp.json.tmpl` already ships the working
  spelling — apply it unchanged, in both channels. `.mcp.json` env values are
  never expanded by Claude Code either, so this entry carries no `env` block —
  `docs-mcp.sh` resolves `docs/` from its own CWD instead. After writing,
  ensure `.claude/hooks/docs-mcp.sh` and `.claude/hooks/_lib.sh` (copied by the
  hooks step above, in every channel) are executable. If `docs/` does not
  exist, skip this step entirely (nothing to point at).

### 5. Print the plan, then confirm

Render the plan as a table (columns: Action, Path). Unless `--yes` was passed,
ask for confirmation before touching anything. On "no", stop here — nothing
was written.

### 6. Apply

Execute exactly the plan from step 4, in the order listed there. Re-check
"does the destination already exist" immediately before each write (never
overwrite a file that appeared between planning and applying).

### 7. Print the summary and follow-ups

Report what changed (or "nothing to do — already up to date" if every action
was `skip-exists`). Then, if `.mcp.json` gained a `pack-docs` entry in this
run, print exactly these two follow-ups:

1. Install the docs server in the project's Python environment:
   `pip install "your-docs-mcp==1.1.2" "mcp<2"`
2. Approve the new project MCP server the next time Claude Code starts in
   this project (it will prompt once for `pack-docs`).
