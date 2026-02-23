---
description: Run ruff check, ruff format, and mypy to lint and fix code
disable-model-invocation: true
---

# /lint-and-fix

Lint and fix the pack's source code.

## Steps

1. **Check the virtual environment** has ruff and mypy. If not:
   ```bash
   source venv/bin/activate && pip install ruff mypy
   ```

2. **Run ruff check with auto-fix**:
   ```bash
   source venv/bin/activate && ruff check --fix .
   ```
   Report any issues that couldn't be auto-fixed.

3. **Run ruff format**:
   ```bash
   source venv/bin/activate && ruff format .
   ```
   Report which files were reformatted.

4. **Run mypy in strict mode**:
   ```bash
   source venv/bin/activate && mypy --strict src/
   ```
   Report any type errors.

5. **Summarize results**:
   - Number of issues auto-fixed by ruff
   - Number of files reformatted
   - Number of remaining ruff issues (if any)
   - Number of mypy errors (if any)
   - For any remaining issues, suggest fixes.
