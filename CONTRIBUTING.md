# Contributing

This repository ships two things from one source tree: the environment the
Huitzo CLI copies into new projects, and a Claude Code plugin. Changes must keep
both working.

## Before opening a pull request

```bash
python3 scripts/validate_env.py          # structure, frontmatter, information boundary, stale tokens
python3 scripts/check_legal_headers.py   # SPDX headers on scripts (never change the identifier)
bash scripts/test_hooks.sh               # hook behaviour against synthetic Claude Code events
python3 scripts/simulate_seed.py         # what each profile seeds into a project
claude plugin validate . --strict        # marketplace + plugin manifest
claude plugin validate ./claude --strict # skills and agents frontmatter
python3 scripts/check_api_surface.py     # network: documented API facts vs published packages
python3 scripts/check_links.py           # network: every external link resolves
```

CI runs the same checks.

## Layout rules (do not break)

- `claude/` is copied verbatim into a project's `.claude/` by the CLI, filtered
  by `profiles/<profile>.json` → `files.exclude` (prefix match). Every file you
  add under `claude/` must be listed in `profiles/pack-only.json` and
  `profiles/dashboard-only.json` (included or excluded) — the validator enforces it.
- Root `CONSTITUTION.md` is copied next to `.claude/`.
- No symlinks anywhere: the CLI rejects the whole clone if it finds one.
- Plugin-only files live outside `claude/` (`.claude-plugin/`, `hooks/hooks.json`).
- `claude/settings.json` must not declare `mcpServers` — Claude Code ignores it
  there. Project MCP configuration belongs in `.mcp.json` (written by `/huitzo-init`).

## Content rules

- This is a public repository. Only public knowledge goes in: docs.huitzo.ai
  pages, the published `huitzo-sdk` / `@huitzo/dashboard-sdk*` packages, the
  `huitzo` CLI's own `--help`, and the public learning repository. No links to
  private repositories, no internal process names, no customer or pricing facts.
- Reference skills state the package version they were verified against on
  their first line. Bump it together with the content and with
  `scripts/check_api_surface.py`.
- Every "do not write this" example carries the ❌ character on its line. The
  validator's stale-token checks skip those lines and flag every other match.
- Rules carry a non-empty `paths:` frontmatter, except `00-huitzo-core.md`,
  which is the only always-on rule.
- Skills: `name` equals the folder name; description ≤ 200 characters in the
  form "What it is. Use when …. Not for …". Workflow skills set
  `disable-model-invocation: true`; reference skills do not.
- Never use the skill name `init` (it shadows Claude Code's built-in `/init`).

## Releasing

1. Bump `version` in `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`
   (they must match) and add a `CHANGELOG.md` entry.
2. If a package version moved, update `VERSIONS` in `scripts/check_api_surface.py`
   and the "Verified against" lines in `README.md` and
   `claude/rules/00-huitzo-core.md` in the same commit.
3. Merge to `main` — the CLI seeds from `main`, so `main` must always be green.
4. Tag the plugin release: `claude plugin tag .`
