# Claude Code Environment for Intelligence Packs & Dashboards

Pre-configured [Claude Code](https://docs.anthropic.com/en/docs/claude-code) environment for developing Intelligence Packs and Dashboards on the Huitzo platform.

Provides SDK-aware skills, specialized agents, coding rules, a documentation server, and project instructions out of the box — for both Python pack commands and React dashboard micro-frontends.

## Setup

### Automatic (via CLI)

```bash
# Pack development
huitzo pack new my-pack
# → "Would you like to set up a Claude Code environment? [y/N]:" → yes

# Dashboard development
huitzo dashboard new my-dashboard
# → Same prompt
```

### Manual

```bash
cd your-project/

# Clone this repo
git clone --depth 1 https://github.com/Huitzo-Inc/pack-claude-env.git /tmp/pack-claude-env

# Copy the environment (full-stack profile)
cp -r /tmp/pack-claude-env/claude/ .claude/
cp /tmp/pack-claude-env/CONSTITUTION.md ./CONSTITUTION.md

# Install the documentation server (for pack docs MCP)
pip install your-docs-mcp

# Create docs structure
mkdir -p docs/commands docs/components docs/pages docs/guides docs/spec

# Clean up
rm -rf /tmp/pack-claude-env
```

## Huitzo Applications (Full-Stack)

For projects that combine packs and dashboards, use the **Huitzo Application** structure — a single repo with `packs/` and `dashboards/` directories, shared docs at the root. See [`docs/guides/application-structure.md`](https://github.com/Huitzo-Inc/huitzo/blob/main/docs/guides/application-structure.md) for the complete guide.

```
my-app/
├── .claude/                    # This environment (full-stack profile)
├── CONSTITUTION.md
├── docs/spec/                  # Application-level specs
├── packs/my-pack/              # Each pack is standalone
└── dashboards/my-dashboard/    # Each dashboard is standalone
```

## Profiles

Choose a profile based on your project type:

| Profile | Use Case | Includes |
|---------|----------|----------|
| **pack-only** | Python Intelligence Pack development | Pack agents + skills + Python rules |
| **dashboard-only** | React dashboard development | Dashboard agents + skills + React rules |
| **full-stack** | Pack + Dashboard together (default) | Everything |

Profile definitions are in `profiles/`. The `CLAUDE.md` is the same for all profiles — path-scoped rules ensure only relevant rules load based on the files being edited.

## Workflow: Documentation First

This environment enforces a **docs-first** workflow:

1. **Spec** (`/draft-spec my-project`) — Structured requirements gathering (7 phases)
2. **Document** (`/draft-docs analyze-text`) — Write command/component documentation
3. **Implement** (`/add-command analyze-text` or `/scaffold-dashboard AnalyzeView`) — Code implements docs
4. **Test** (`/test-pack` or `/test-dashboard`) — Validate documented behavior
5. **Validate** (`/validate-pack` or `/validate-dashboard`) — Structure and quality checks
6. **Lint** (`/lint-and-fix`) — Auto-fix code style

## What You Get

### Skills

| Skill | Scope | Description |
|-------|-------|-------------|
| `/draft-spec <name>` | Both | 7-phase requirements gathering and specification |
| `/draft-docs <name>` | Pack | Draft documentation for a command (docs-first) |
| `/add-command <name>` | Pack | Scaffold command with args, function, test, manifest |
| `/test-pack` | Pack | Run pytest with venv activation |
| `/validate-pack` | Pack | Validate manifest, traceability, linting |
| `/scaffold-dashboard <name>` | Dashboard | Scaffold component/page with docs, CSS Module, test |
| `/test-dashboard` | Dashboard | Run Vitest |
| `/validate-dashboard` | Dashboard | Validate manifest, Hub contract, CSS isolation |
| `/dashboard-dev` | Dashboard | Start Vite dev server |
| `/lint-and-fix` | Both | Auto-fix: ruff + mypy (pack), tsc + eslint (dashboard) |

### Agents

| Agent | Scope | Description |
|-------|-------|-------------|
| `docs-writer` | Both | Documentation specialist — drafts docs with MCP integration |
| `pack-developer` | Pack | Command implementation — enforces docs-first, knows SDK |
| `pack-reviewer` | Pack | Code reviewer — documentation, SDK adherence, tests |
| `dashboard-developer` | Dashboard | Component/page implementation — Hub contract, hooks |
| `dashboard-reviewer` | Dashboard | Dashboard reviewer — contract, accessibility, CSS isolation |
| `spec-architect` | Both | Requirements gathering — 7-phase structured specification |

### Rules

| Rule | Scope | Content |
|------|-------|---------|
| `documentation` | Both | Docs-first workflow, templates for commands and components |
| `traceability` | Both | Python and TypeScript traceability header formats |
| `testing` | Both | pytest-asyncio (pack) + Vitest (dashboard) patterns |
| `sdk-patterns` | Pack | `@command` decorator, Context services, imports |
| `error-handling` | Pack | SDK exception hierarchy and usage |
| `hub-contract` | Dashboard | mount/unmount, HuitzoContext, CSS isolation |
| `react-patterns` | Dashboard | React 19.2, hooks, accessibility, TypeScript |
| `dashboard-manifest` | Dashboard | huitzo-dashboard.yaml validation rules |

### MCP Documentation Server

Configured in `.claude/settings.json` — serves your `docs/` directory via [your-docs-mcp](https://github.com/esola-thomas/your-docs-mcp). Provides search, navigation, and structured access from within Claude Code.

### CONSTITUTION.md

Developer constitution with 5 principles:
1. Intelligence Must Be Real
2. Own What You Ship
3. Simplicity Is a Discipline
4. Data Belongs to the Customer
5. Display What Is True (dashboards)

## Quality Gates

### Pack

```bash
source venv/bin/activate
pytest -v                  # Tests pass
ruff check .               # Linting
ruff format --check .      # Formatting
mypy --strict src/         # Type checking
huitzo validate            # Manifest + structure
```

### Dashboard

```bash
npm test                          # Vitest
npx tsc --noEmit                  # Type checking
huitzo dashboard validate         # Manifest + bundle + contract
```

## Updating

```bash
cd your-project/
git clone --depth 1 https://github.com/Huitzo-Inc/pack-claude-env.git /tmp/pack-claude-env
cp -r /tmp/pack-claude-env/claude/ .claude/
cp /tmp/pack-claude-env/CONSTITUTION.md ./CONSTITUTION.md
rm -rf /tmp/pack-claude-env
```

## License

MIT
