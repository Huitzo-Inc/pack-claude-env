# Claude Code Environment for Intelligence Packs

Pre-configured [Claude Code](https://docs.anthropic.com/en/docs/claude-code) environment for developing Intelligence Packs on the Huitzo platform.

Gives you SDK-aware skills, specialized agents, coding rules, a documentation server, and project instructions out of the box.

## Automatic Setup

When creating a new pack with the Huitzo CLI:

```bash
huitzo pack new my-pack
```

You'll be prompted:

```
Would you like to set up a Claude Code environment? [y/N]:
```

Say **yes** and the CLI handles everything — including installing the documentation server.

## Manual Setup

If you have an existing pack or prefer manual installation:

```bash
cd your-pack/

# Clone this repo
git clone --depth 1 https://github.com/Huitzo-Inc/pack-claude-env.git /tmp/pack-claude-env

# Copy the Claude Code environment
cp -r /tmp/pack-claude-env/claude/ .claude/
cp /tmp/pack-claude-env/CONSTITUTION.md ./CONSTITUTION.md

# Install the documentation server
pip install your-docs-mcp

# Create docs structure (if not exists)
mkdir -p docs/commands docs/guides

# Clean up
rm -rf /tmp/pack-claude-env
```

## Documentation-First Workflow

This environment enforces a **docs-first** workflow:

1. **Draft docs** (`/draft-docs analyze-text`) — Write the command documentation first
2. **Review** — Documentation defines the contract
3. **Implement** (`/add-command analyze-text`) — Code implements the documented behavior
4. **Test** — Tests validate the documented behavior
5. **Validate** (`/validate-pack`) — Everything is consistent

The `docs-writer` agent and `/draft-docs` skill help you write structured documentation. The `pack-developer` agent enforces docs-first — it won't implement a command without documentation.

## What You Get

### Skills

| Skill | Description |
|-------|-------------|
| `/draft-docs <name>` | Draft documentation for a new command (docs-first workflow) |
| `/add-command <name>` | Scaffold a new command with args model, function, test, and manifest entry |
| `/test-pack` | Run pack tests with venv activation |
| `/validate-pack` | Validate manifest, entry points, traceability, and linting |
| `/lint-and-fix` | Run ruff check + format and mypy |

### Agents

| Agent | Description |
|-------|-------------|
| `docs-writer` | Documentation specialist — drafts command docs with structured format and MCP integration |
| `pack-developer` | Specialized for writing commands — enforces docs-first, knows SDK patterns |
| `pack-reviewer` | Code reviewer — checks documentation completeness, SDK adherence, test coverage |

### Rules

| Rule | Content |
|------|---------|
| `documentation` | Docs-first workflow, MCP server usage, documentation structure and templates |
| `sdk-patterns` | `@command` decorator, Context services, imports, return types |
| `testing` | pytest-asyncio setup, mock Context, Pydantic validation testing |
| `error-handling` | Exception hierarchy, when to use each type, raise patterns |
| `traceability` | Header format, `Implements:` references, validation |

### MCP Documentation Server

Configured in `.claude/settings.json` — serves your `docs/` directory via [your-docs-mcp](https://github.com/esola-thomas/your-docs-mcp). Provides search, navigation, and structured access to your pack's documentation from within Claude Code.

### CLAUDE.md

Project-level instructions with docs-first workflow, build/test/lint commands, SDK conventions, and code quality gates.

### CONSTITUTION.md

Simplified developer constitution: write real intelligence, own what you ship, keep it simple, respect customer data.

## Updating

To update an existing pack's Claude Code environment:

```bash
cd your-pack/
git clone --depth 1 https://github.com/Huitzo-Inc/pack-claude-env.git /tmp/pack-claude-env
cp -r /tmp/pack-claude-env/claude/ .claude/
cp /tmp/pack-claude-env/CONSTITUTION.md ./CONSTITUTION.md
rm -rf /tmp/pack-claude-env
```

## License

MIT
