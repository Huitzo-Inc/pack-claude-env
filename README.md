# Huitzo developer environment for Claude Code

Everything an AI coding agent needs to build **Intelligence Packs** (Python commands run by the
Huitzo platform) and **Dashboards** (React micro-frontends loaded by Huitzo Hub): verified API
references for the SDK, manifest, CLI, platform API and dashboard SDK; docs-first workflow skills;
developer and reviewer agents; safety hooks; and a project-docs MCP server. It installs as a
[Claude Code](https://code.claude.com/docs/en/overview) plugin or is seeded into new projects by
the `huitzo` CLI.

Verified against `huitzo-sdk` 1.7.0 · `@huitzo/dashboard-sdk` 0.6.0 ·
`@huitzo/dashboard-sdk-react` 5.1.1 · Claude Code 2.1.269 (path-scoped rules need 2.1.84 or later).

## Install

### As a plugin (recommended)

```text
/plugin marketplace add Huitzo-Inc/pack-claude-env
/plugin install huitzo@huitzo
```

Then, inside a pack, dashboard or project directory:

```text
/huitzo:huitzo-init
```

`huitzo-init` shows a plan and asks before writing. It adds the path-scoped rules to
`.claude/rules/`, a managed block to `CLAUDE.md` and `AGENTS.md`, `CONSTITUTION.md`, and — when the
project has a `docs/` directory — the `pack-docs` MCP server entry in `.mcp.json`. It never
overwrites existing files and never touches `settings.json`. Skills are available as
`/huitzo:<skill>`; agents and hooks are active as soon as the plugin is enabled.

### With the Huitzo CLI (seed)

```bash
huitzo pack new my-pack          # → "Would you like to set up a Claude Code environment?" → yes
huitzo dashboard new my-dash     # same prompt
huitzo project init my-project   # seeded silently (pack + dashboard)
```

The CLI copies `claude/` into the project's `.claude/` (filtered by profile) and `CONSTITUTION.md`
next to it. Skills are available as `/<skill>`. Run `/huitzo-init` once to wire the project docs
MCP server.

Install the CLI: `curl -sSf https://raw.githubusercontent.com/Huitzo-Inc/huitzo-launcher/main/install.sh | sh` (Linux/WSL) or
`brew install Huitzo-Inc/tap/huitzo` (macOS). Docs: <https://docs.huitzo.ai/docs/cli/overview>.

Pick one channel per project. Both together work but hooks would run twice.

## What you get

### Always-on core

`.claude/rules/00-huitzo-core.md` (about 100 lines) is the only always-loaded context: project detection,
the docs-first loop, twelve non-negotiable rules, the `ctx` services table, and where to get more
context (installed package → reference skills → project docs MCP → docs.huitzo.ai → CLI `--help` →
worked examples). Everything else loads on demand.

### Reference skills (load when needed, or open like a manual)

| Skill | Verified against | Covers |
|---|---|---|
| `huitzo-sdk` | huitzo-sdk 1.7.0 | `@command`, every `ctx.*` service with exact signatures, errors, testing patterns |
| `huitzo-manifest` | huitzo-sdk 1.7.0 | `huitzo.yaml` schema v2, policy card, the 14 permission tokens, services, pipelines |
| `huitzo-dashboard-sdk` | dashboard-sdk-react 5.1.1 | mount contract, `HuitzoMountContext`, all hooks, Templates, tokens and `hz-*` primitives |
| `cli-non-interactive` | CLI surface 2026-09 | every developer-facing `huitzo` command, JSON envelope, exit codes, agent recipes |
| `huitzo-platform` | docs.huitzo.ai | REST API, API keys, task polling, hosted MCP, MCP inside packs, webhooks, secrets model |
| `huitzo-methodology` | docs.huitzo.ai | deterministic-first design, command sizing, composition, testing pyramid, shipping |

### Workflow skills

| Skill | Scope | Does |
|---|---|---|
| `/draft-spec <name>` | both | 7-phase requirements gathering → `docs/spec/` |
| `/draft-docs <verb-noun>` | pack | write the command contract before code |
| `/add-command <verb-noun>` | pack | scaffold command, args model, test, manifest entry (uses `huitzo pack add-command` when available) |
| `/test-pack`, `/validate-pack`, `/lint-and-fix` | pack | pytest, `huitzo pack validate --strict`, ruff/mypy |
| `/scaffold-dashboard [page] <Name>` | dashboard | component/page with docs, styles, test |
| `/test-dashboard`, `/validate-dashboard`, `/dashboard-dev`, `/dashboard-e2e` | dashboard | tests, `huitzo dashboard validate`, dev server, mount→unmount check |
| `/sandbox`, `/publish` | both | run commands against the local sandbox; ship a pack or dashboard |
| `/huitzo-init` | both | bootstrap or repair the environment in a project |

### Agents

`pack-developer` and `dashboard-developer` (preload their reference skill), `pack-reviewer` and
`dashboard-reviewer` (read-only, checklist-driven, graded findings), `docs-writer`, `spec-architect`.

### Rules (path-scoped)

`sdk-patterns`, `error-handling`, `testing`, `pack-manifest`, `traceability`, `documentation`,
`hub-contract`, `react-patterns`, `dashboard-design`, `dashboard-manifest` — each loads only when a
matching file is edited.

### Hooks (only inside Huitzo projects)

Session context at start; a blocking secrets scan on writes (API keys, tokens, private keys);
non-blocking nudges after edits (missing traceability header, hex colours in dashboards,
`model=` on `ctx.llm`, `dangerouslySetInnerHTML`, ruff findings); a summary of unheadered files when
you stop. Outside a Huitzo project every hook exits immediately. The secrets scan skips JWT-shaped
and generic `sk-…` examples in prose files (`.md`, `.mdx`, `.rst`, `.txt`) and honours
`HUITZO_SECRETS_SCAN=warn` (report, never block) or `=off`. The seeded permission allowlist in
`.claude/settings.json` only applies once you trust the workspace in Claude Code; it covers read-only
inspection and the quality-gate commands — note that `Bash(pytest*)` runs the project's own test code,
so remove it if you open checkouts you do not trust.

### Project docs MCP server

`pack-docs` serves the project's own `docs/` to Claude Code via
[`your-docs-mcp`](https://pypi.org/project/your-docs-mcp/) (tools: `search_documentation`,
`get_document`, `navigate_to`, `get_table_of_contents`, `search_by_tags`, `get_all_tags`). The
launcher `.claude/hooks/docs-mcp.sh` looks for the server in the project's virtualenv, then on
`PATH`. Install it into the project environment with:

```bash
pip install "your-docs-mcp==1.1.2" "mcp<2"    # 1.1.2 needs the mcp 1.x SDK
```

Claude Code reads MCP configuration from `.mcp.json`, not from `.claude/settings.json`; `/huitzo-init`
writes the entry when `docs/` exists. This project-local server is different from the Hub-hosted
documentation server that `huitzo mcp setup docs` configures in your user-level Claude settings: one
serves your own `docs/`, the other serves the platform documentation.

## Profiles

| Profile | Use case | Seeds |
|---|---|---|
| `full-stack` (default) | pack + dashboard | everything |
| `pack-only` | Python pack | pack agents, rules and skills + shared skills |
| `dashboard-only` | React dashboard | dashboard agents, rules and skills + shared skills |

`profiles/*.json` `files.exclude` lists drive the CLI's filtering. The plugin always carries the
full set; on-demand loading keeps the always-on context the same size in every profile.

## Validation

```bash
python3 scripts/validate_env.py          # structure, frontmatter, information boundary, stale API tokens
python3 scripts/check_api_surface.py     # documented API facts vs the published packages (network)
python3 scripts/check_links.py           # every external link resolves (network)
python3 scripts/simulate_seed.py         # what each profile seeds into a project
bash scripts/test_hooks.sh               # hook behaviour against synthetic Claude Code events
claude plugin validate . --strict        # marketplace manifest (+ nested plugin manifest)
claude plugin validate ./.claude-plugin/plugin.json --strict
claude plugin validate ./claude --strict # skills and agents frontmatter
```

CI runs the same checks on every pull request. See `CONTRIBUTING.md`.

## Updating an existing project

Plugin channel: `/plugin update huitzo`, then `/huitzo:huitzo-init` to refresh the managed blocks
and rules (existing files are never overwritten; delete a rule file to receive the new version).
Seed channel: re-run `/huitzo-init`, or copy `claude/` from a fresh clone of this repository over
`.claude/`.

## Learn by doing

<https://github.com/Huitzo-Inc/build-with-huitzo> — runnable labs from a hello pack to a full-stack
application, all testable offline.

## License

Source-available under the **Huitzo Source-Available License** — see [LICENSE](LICENSE). The
contents are public for transparency and to support Intelligence Pack development on the Huitzo
platform; copying, modification and redistribution require written permission from Huitzo Inc.

"Huitzo" and the Huitzo logo are trademarks of Huitzo Inc. — see [TRADEMARKS.md](TRADEMARKS.md).
