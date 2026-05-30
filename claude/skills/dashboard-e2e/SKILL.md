---
name: dashboard-e2e
description: End-to-end dashboard verification — mount → render → unmount → assert clean teardown
disable-model-invocation: true
---

# /dashboard-e2e

Verify a dashboard end-to-end against the **Hub module contract** before
publishing: exercise the real `mount` / `unmount` entry points the Hub calls,
confirm the dashboard renders with a `HuitzoContext`, and assert it tears down
cleanly with no leaked React roots, timers, or listeners.

This is the verification step on the **local → preview** part of the loop:
scaffold → develop → test → **e2e** → sandbox → publish. `/test-dashboard`
covers component-level unit tests; this skill verifies the whole module the way
Hub loads it.

> Reference: the in-repo source of truth for the module contract is
> `claude/rules/hub-contract.md` (with `claude/rules/react-patterns.md`); the
> Huitzo platform's `docs/dashboards/loading.md` (external, not shipped in this
> scaffold) is the canonical runtime-loading-pipeline doc. The rules in
> `claude/rules/hub-contract.md` and `claude/rules/react-patterns.md` define the
> contract this skill checks.

## What "the contract" means

`src/main.tsx` MUST export exactly two functions (see `hub-contract.md`):

```typescript
export function mount(container: HTMLElement, context: HuitzoContext): void;
export function unmount(container: HTMLElement): void;
```

- `mount` creates a React root in `container`, wraps the app in `HuitzoProvider`
  + the `huitzo-dashboard` class, and renders.
- `unmount` cleans up that root.

The e2e check drives this lifecycle directly — that is what Hub does on
navigate-in / navigate-away.

## Two complementary flows

### A. Headless lifecycle test (Vitest + jsdom — fast, runs in CI)

Conceptual shape — model it on the existing Vitest + React Testing Library setup
in `react-patterns.md`. Import the real module contract, not a component:

```typescript
// pseudocode — e2e lifecycle of the Hub module contract
import { describe, it, expect, vi } from 'vitest';
import { mount, unmount } from '../src/main';

const mockContext = {
  apiUrl: 'http://localhost:8000',
  getToken: () => 'test-token',
  slug: 'test',
  // ...the fields your dashboard reads from HuitzoContext
};

describe('Hub module contract (e2e)', () => {
  it('mounts, renders, and unmounts cleanly', async () => {
    const container = document.createElement('div');
    document.body.appendChild(container);

    mount(container, mockContext);
    // assert: rendered (e.g., the root content / an eyebrow heading is present)
    expect(container.querySelector('.huitzo-dashboard')).not.toBeNull();

    unmount(container);
    // assert clean teardown: React root removed, container emptied
    expect(container.innerHTML).toBe('');
  });
});
```

Assert clean teardown: after `unmount`, the container is empty, no React
warnings are logged, and any timers/subscriptions the dashboard started are
cleared. A common failure is a leaked `setInterval` or an un-removed event
listener that keeps firing after `unmount` — fail the test if a spied
`clearInterval` / `removeEventListener` was never called.

### B. Real-browser preview (Playwright-style — closer to Hub)

For full-fidelity verification in a real browser, drive the dashboard's preview
in a headless browser. Conceptually:

1. **Build the module:** `huitzo dashboard build` → `dist/main.js`.
2. **Serve a preview harness** that imports `dist/main.js`, calls `mount` with a
   `HuitzoContext`, and lets you navigate away to trigger `unmount` (the dev
   server's `src/dev.tsx` harness is the local stand-in — see `/dashboard-dev`).
3. **Drive it headless** (Playwright): navigate to the preview, wait for the
   first meaningful render, interact, then trigger teardown.
4. **Assert clean teardown:** no console errors, the mount node is empty after
   unmount, and no detached React roots remain.

Point the preview's `useCommand` hooks at a running local sandbox so the e2e run
hits real command output instead of mocks — see `/sandbox`.

If a Playwright MCP / driver is available in this environment, prefer it for the
browser steps; otherwise the headless Vitest flow (A) is sufficient for CI.

## Steps

1. **Confirm the contract.** `src/main.tsx` exports `mount` and `unmount`
   exactly; the app is wrapped in `HuitzoProvider` + `huitzo-dashboard`.
2. **Run unit tests first.** `/test-dashboard` (component-level) should be green.
3. **Run the lifecycle test (A).** Mount with a mock `HuitzoContext`, assert it
   renders, unmount, assert the container is empty and nothing leaked.
4. **(Optional) Real-browser preview (B).** Build, serve the preview harness,
   drive it headless, and assert clean teardown + no console errors.
5. **Report:** rendered ✓ / unmounted-clean ✓ / no leaks ✓, and any failures
   with the offending selector, timer, or listener.

## Notes

- This is verification, not scaffolding — it does not modify source.
- Both themes matter: re-run with `data-theme="light"` on the wrapper to confirm
  the dashboard renders intentionally in light mode (see `dashboard-design.md`).
- Run this before `/publish` to catch lifecycle leaks the Hub would surface as
  navigation bugs.
