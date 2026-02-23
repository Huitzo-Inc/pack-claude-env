# Intelligence Pack Developer Constitution

> Simplified subset of the [Huitzo Constitution](https://github.com/Huitzo-Inc/huitzo/blob/main/CONSTITUTION.md) for pack developers.

---

## 1. Intelligence Must Be Real

Every Intelligence Pack must deliver measurable intelligence advantage to its users. Wrappers without value are not welcome.

**What it requires:**
- Measurable quality delta over raw model access
- At least one proprietary advantage: data, workflow integration, or domain knowledge
- Meaningful functionality that survives if the underlying model changes

**What it forbids:**
- Thin API wrappers with logos
- Prompt-only products with no proprietary layer
- Packs that add latency without adding insight

## 2. Own What You Ship

Every output has a named owner accountable for its quality and consequences.

**What it requires:**
- Tests must pass before publishing
- Traceability headers on all source files
- Post-mortems without blame but with honest attribution

**What it forbids:**
- Shipping untested code
- "It works on my machine" as justification
- Hiding behind consensus

## 3. Simplicity Is a Discipline

The best part is no part. Earn the right to add complexity only after exhausting deletion.

**What it requires:**
- Question every requirement
- Delete before adding, simplify before optimizing
- Type hints everywhere (`mypy --strict`)
- Clean linting (`ruff check .`)

**What it forbids:**
- "Just in case" features
- Over-engineering for hypothetical futures
- Legacy code kept out of sentiment

## 4. Data Belongs to the Customer

Customer data is theirs. Period.

**What it requires:**
- Use `ctx.storage` for scoped data — never raw file I/O
- Declare all data flows in your manifest
- Zero-access by default

**What it forbids:**
- Exfiltrating data beyond declared scope
- Training on customer data
- Telemetry without consent

---

## Quality Gates

Before publishing any pack:

```bash
source venv/bin/activate
pytest -v                  # Own What You Ship
ruff check .               # Simplicity
ruff format --check .      # Simplicity
mypy --strict src/         # Simplicity through types
huitzo validate            # Manifest + structure check
```

All gates must pass. No exceptions.
