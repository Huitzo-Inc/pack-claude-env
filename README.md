# Claude Code Environment for Intelligence Packs

Pre-configured [Claude Code](https://docs.anthropic.com/en/docs/claude-code) environment for developing Intelligence Packs on the Huitzo platform.

Gives you SDK-aware skills, specialized agents, coding rules, and project instructions out of the box.

## Automatic Setup

When creating a new pack with the Huitzo CLI:

```bash
huitzo pack new my-pack
```

You'll be prompted:

```
Would you like to set up a Claude Code environment? [y/N]:
```

Say **yes** and the CLI handles everything.

## Manual Setup

If you have an existing pack or prefer manual installation:

```bash
cd your-pack/

# Clone this repo
git clone --depth 1 https://github.com/Huitzo-Inc/pack-claude-env.git /tmp/pack-claude-env

# Copy the Claude Code environment
cp -r /tmp/pack-claude-env/claude/ .claude/
cp /tmp/pack-claude-env/CONSTITUTION.md ./CONSTITUTION.md

# Clean up
rm -rf /tmp/pack-claude-env
```

## What You Get

### Skills

| Skill | Description |
|-------|-------------|
| `/add-command <name>` | Scaffold a new command with args model, function, test, and manifest entry |
| `/test-pack` | Run pack tests with venv activation |
| `/validate-pack` | Validate manifest, entry points, traceability, and linting |
| `/lint-and-fix` | Run ruff check + format and mypy |

### Agents

| Agent | Description |
|-------|-------------|
| `pack-developer` | Specialized for writing commands — knows SDK patterns, Context API, error handling |
| `pack-reviewer` | Code reviewer — checks SDK adherence, test coverage, traceability |

### Rules

| Rule | Content |
|------|---------|
| `sdk-patterns` | `@command` decorator, Context services, imports, return types |
| `testing` | pytest-asyncio setup, mock Context, Pydantic validation testing |
| `error-handling` | Exception hierarchy, when to use each type, raise patterns |
| `traceability` | Header format, `Implements:` references, validation |

### CLAUDE.md

Project-level instructions with build/test/lint commands, SDK conventions, and code quality gates.

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
