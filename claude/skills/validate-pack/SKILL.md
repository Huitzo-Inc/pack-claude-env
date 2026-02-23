---
description: Validate pack structure, manifest, entry points, traceability, and linting
disable-model-invocation: true
---

# /validate-pack

Validate the Intelligence Pack's structure and quality.

## Steps

1. **Check `huitzo.yaml` exists and is valid YAML**. Read it and verify required fields:
   - `pack.name` — present and valid (lowercase, hyphens)
   - `pack.namespace` — present and valid
   - `pack.version` — present and follows semver
   - `pack.description` — present and non-empty
   - `commands` — at least one command listed

2. **Verify commands match source files**. For each command in `huitzo.yaml`:
   - Check a corresponding Python file exists in `src/*/commands/`
   - Check the command function exists with `@command` decorator
   - Check the namespace in `@command()` matches `pack.namespace`

3. **Check traceability headers**. For each `.py` file in `src/` and `tests/`:
   - Verify the file has a module docstring
   - Verify the docstring contains `Implements:` with at least one doc reference

4. **Run linting** (if ruff is available in the venv):
   ```bash
   source venv/bin/activate && ruff check . 2>&1
   ```

5. **Run type checking** (if mypy is available in the venv):
   ```bash
   source venv/bin/activate && mypy --strict src/ 2>&1
   ```

6. **Check `pyproject.toml`** has required fields:
   - `project.name` matches pack name
   - `huitzo-sdk` is in dependencies
   - Entry points are defined under `[project.entry-points."huitzo.commands"]`

7. **Report results** as a checklist:
   ```
   Manifest (huitzo.yaml)     ✓ valid
   Command files              ✓ 3/3 match manifest
   Traceability headers       ✓ 6/6 files have headers
   Linting (ruff)             ✓ no issues
   Type checking (mypy)       ✗ 2 errors (list them)
   Package config             ✓ valid
   ```
