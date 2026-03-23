---
description: Run dashboard tests with Vitest
disable-model-invocation: true
---

# /test-dashboard

Run the dashboard test suite.

## Steps

1. **Check `node_modules/`** exists. If not, tell the user:
   ```bash
   npm install
   ```

2. **Check test configuration** — verify `vitest` is in `package.json` devDependencies or `vite.config.ts` has test config.

3. **Run tests**:
   ```bash
   npm test 2>&1
   ```

4. **If tests fail**, analyze the output:
   - **Import errors** — Dependencies not installed. Suggest `npm install`.
   - **Module not found** — Check file paths and exports.
   - **React Testing Library errors** — Check `@testing-library/react` is installed.
   - **Mock errors** — Check `vi.mock()` calls match import paths.
   - **Actual test failures** — Report each failure with file, test name, and error.

5. **Report results**:
   - Total tests run
   - Passed / Failed / Skipped counts
   - List of failures with file and test name
   - Suggest fixes for common issues
