---
name: test-dashboard
description: Run the dashboard test suite (Vitest), or set it up if the project has none yet.
disable-model-invocation: true
---

# /test-dashboard

Run the dashboard's tests, or bootstrap testing if it doesn't have any yet.

## Steps

1. **Check `node_modules/`** exists. If not, tell the user to run
   `npm install` first.

2. **Check whether a test setup exists** — look for a `"test"` script in
   `package.json` and a Vitest config (`vitest.config.ts`, or `test:` inside
   `vite.config.ts`). The CLI's default dashboard scaffold ships **no test
   script and no Vitest dependency** — `dev`/`build`/`typecheck`/`preview`
   only. Don't assume tests exist; check.

3. **If there's no test setup, add the minimal one**:

   ```bash
   npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom
   ```

   Add to `package.json`:
   ```json
   "scripts": { "test": "vitest run" }
   ```

   Add a Vitest config with the `jsdom` environment (e.g. in
   `vite.config.ts`, a `test: { environment: 'jsdom', globals: true }`
   block, or a separate `vitest.config.ts` if you'd rather not touch the
   build config). See `react-patterns.md` for the `HuitzoProvider` +
   mock-context pattern every test that touches an SDK hook needs.

4. **Run the tests**:

   ```bash
   npm test 2>&1
   ```

5. **If tests fail**, diagnose by category:
   - **Import errors** — dependencies not installed; suggest `npm install`.
   - **Module not found** — check file paths and exports.
   - **"must be used within <HuitzoProvider>"** — the test renders a
     component that calls an SDK hook without wrapping it in
     `HuitzoProvider` + a mock context (see `react-patterns.md`).
   - **React Testing Library errors** — confirm `@testing-library/react` and
     `@testing-library/jest-dom` are installed and imported.
   - **Mock mismatches** — `vi.mock()` calls must spread the real module
     (`importOriginal`) so `HuitzoProvider` and other hooks survive; check
     the mocked `useCommand` return matches the current five-state shape
     (`idle | loading | polling | success | error`, plus `isPolling`).
   - **Genuine assertion failures** — report file, test name, and the
     diff/error.

6. **Also run type checking** — the scaffold's `typecheck` script exists by
   default even when tests don't:

   ```bash
   npm run typecheck
   ```

7. **Report results**: total run / passed / failed / skipped, each failure
   with file + test name, and the `typecheck` outcome.
