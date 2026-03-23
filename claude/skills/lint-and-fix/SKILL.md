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

5. **Dashboard linting** (if `huitzo-dashboard.yaml` exists):

   Run TypeScript type checking:
   ```bash
   npx tsc --noEmit 2>&1
   ```
   Report any type errors.

   Run ESLint (if configured):
   ```bash
   npx eslint src/ 2>&1
   ```
   Report any lint issues.

6. **Summarize results**:
   - Number of issues auto-fixed by ruff (pack)
   - Number of files reformatted (pack)
   - Number of remaining ruff issues (pack)
   - Number of mypy errors (pack)
   - Number of TypeScript errors (dashboard)
   - Number of ESLint issues (dashboard)
   - For any remaining issues, suggest fixes.
