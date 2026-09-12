---
name: lint-and-fix
description: Auto-fix lint/format/type issues for a pack (ruff, mypy) or dashboard (typecheck, lint).
disable-model-invocation: true
---

# /lint-and-fix

Lint and fix source code. Never touch legal-header or SPDX lines while
"fixing" anything — those are a legal decision, not a style one.

## Pack (Python) — if `huitzo.yaml` exists

1. Confirm `ruff` and `mypy` are available in the active environment
   (`venv/`/`.venv/`, or via `uv run`). If not, tell the user to
   `pip install -e ".[dev]"` first.

2. **Auto-fix and format:**

   ```bash
   ruff check --fix .
   ruff format .
   ```

   Report anything `ruff check` couldn't auto-fix, and which files
   `ruff format` rewrote.

3. **Type check** (informational — mypy has no auto-fix):

   ```bash
   mypy --strict src/
   ```

   Report each error; don't attempt to guess-fix type errors without
   understanding the underlying issue.

## Dashboard (TypeScript/React) — if `huitzo-dashboard.yaml` exists

1. **Type check** — always available in a scaffolded dashboard:

   ```bash
   npm run typecheck
   ```

2. **Lint** — check `package.json` first; don't assume a linter is
   configured. Look for a `lint` script and for a Biome (`biome.json`) or
   ESLint (`.eslintrc*`, `eslint.config.*`) config file before running
   anything:

   ```bash
   npm run lint     # only if package.json defines this script
   ```

   If neither a `lint` script nor a Biome/ESLint config exists, say so rather
   than inventing a command — skip this step instead of guessing at flags.

## Summarize

- Pack: issues auto-fixed, files reformatted, remaining ruff issues, mypy
  error count.
- Dashboard: TypeScript error count, lint issue count (or "no linter
  configured").
- For anything left unresolved, name the file and suggest the fix — don't
  just say "there are errors."
