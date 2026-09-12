# pack-claude-env — instructions for AI tools working on THIS repository

This repository is the Huitzo developer environment for Claude Code. It is public. It ships two
ways from one source tree:

1. **Seed** — the Huitzo CLI (`huitzo pack new`, `huitzo dashboard new`, `huitzo project init`)
   clones `main` and copies `claude/` into a project's `.claude/`, filtered by
   `profiles/<profile>.json`, plus the root `CONSTITUTION.md`.
2. **Plugin** — `.claude-plugin/marketplace.json` + `.claude-plugin/plugin.json` expose the same
   `claude/skills/`, `claude/agents/` and `hooks/hooks.json` as the `huitzo` plugin.

It is configuration, not an application: markdown, JSON and small shell/Python scripts only.

## Layout

```
.claude-plugin/        plugin.json, marketplace.json (plugin channel only)
hooks/hooks.json       plugin hook wiring → ${CLAUDE_PLUGIN_ROOT}/claude/hooks/*.sh
claude/                THE seed (copied verbatim into projects)
  CLAUDE.md            thin pointer (the CLI may overwrite it in Projects)
  settings.json        seed hooks + permission allowlist (never mcpServers)
  rules/               00-huitzo-core.md (always on) + path-scoped rules
  skills/              workflow skills + reference skills + huitzo-init
  agents/              developer / reviewer / docs / spec agents
  hooks/               shared hook scripts + docs-mcp.sh launcher
profiles/              pack-only, dashboard-only, full-stack (exclude lists drive the CLI)
scripts/               validators (see CONTRIBUTING.md)
CONSTITUTION.md        developer principles copied next to .claude/
```

## Rules for edits here

- Read `CONTRIBUTING.md` first; run every validator listed there before a PR.
- Only public knowledge: docs.huitzo.ai, the published `huitzo-sdk` and `@huitzo/dashboard-sdk*`
  packages, `huitzo --help`, https://github.com/Huitzo-Inc/build-with-huitzo. No private repository
  links, no internal process names, no company facts.
- Every file added under `claude/` must be listed in `profiles/pack-only.json` and
  `profiles/dashboard-only.json` (included or excluded). No symlinks anywhere.
- Reference skills say which package version they were verified against; keep that in sync with
  `scripts/check_api_surface.py`.
- Wrong-example lines carry ❌; correct examples never do.
- Never name a skill `init`; never change an SPDX identifier.
