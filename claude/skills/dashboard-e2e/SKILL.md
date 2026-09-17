---
name: dashboard-e2e
description: End-to-end dashboard verification — mount, render, unmount, and assert clean teardown against the real module contract.
disable-model-invocation: true
---

# /dashboard-e2e

Verify a dashboard against the **Hub module contract** before publishing:
exercise the real `mount`/`unmount` exports the way Hub calls them, confirm
the dashboard renders with a `HuitzoMountContext`, and assert it tears down
with no leaked React roots, timers, or listeners.

This sits after unit tests in the loop: scaffold → develop → test → **e2e**
→ validate → publish. `/test-dashboard` covers component-level units; this
skill verifies the whole module the way Hub loads it. The contract itself is
defined in `hub-contract.md` (and `react-patterns.md` for the surrounding
React patterns) — this skill checks against those, not against Hub's own
internal loading pipeline.

## What "the contract" means

`src/main.tsx` exports exactly:

```typescript
export function mount(container: HTMLElement, context: HuitzoMountContext): void;
export function unmount(container: HTMLElement): void;
```

`mount` creates a React root in `container`, wraps the app in
`HuitzoProvider` + the `.huitzo-dashboard` class, and renders; `unmount`
tears that root down. The e2e check drives this lifecycle directly.

## A. Headless lifecycle test (Vitest + jsdom — fast, runs in CI)

Import the real module contract, not a component:

```typescript
// pseudocode — e2e lifecycle of the Hub module contract
import { describe, it, expect } from 'vitest';
import { mount, unmount } from '../src/main';
import type { HuitzoMountContext } from '@huitzo/dashboard-sdk-react';

const mockContext: HuitzoMountContext = {
  apiUrl: 'http://localhost:8000',
  getToken: () => 'test-token',
  slug: 'test',
  sdkVersion: '5.1.1',
  user: { id: '1', email: 'a@b.com', roles: ['admin'], tenantId: 't1' },
  navigate: () => {}, navigateToHub: () => {}, navigateToDashboard: () => {},
  showNotification: () => {}, on: () => () => {}, emit: () => {},
};

describe('Hub module contract (e2e)', () => {
  it('mounts, renders, and unmounts cleanly', () => {
    const container = document.createElement('div');
    document.body.appendChild(container);

    mount(container, mockContext);
    expect(container.querySelector('.huitzo-dashboard')).not.toBeNull();

    unmount(container);
    expect(container.innerHTML).toBe('');
  });
});
```

## Assertion list

- [ ] `mount(container, context)` renders — `container.querySelector('.huitzo-dashboard')` is non-null.
- [ ] No console errors/warnings during mount (React key warnings, act() warnings, hook-outside-provider errors).
- [ ] `unmount(container)` empties the container (`container.innerHTML === ''`).
- [ ] No leaked `setInterval`/`setTimeout` — spy on `clearInterval`/`clearTimeout` and assert every timer the dashboard started was cleared.
- [ ] No leaked event listener — spy on `removeEventListener` (and, if the dashboard calls `context.on()` directly rather than through a hook, confirm the returned unsubscribe function fires in `unmount`).
- [ ] A second `mount()` after `unmount()` on a fresh container still works (no stale module-level state).
- [ ] (If the dashboard reads `theme`/`locale`/`currency` from context) mounting with them present and with them omitted both render without throwing — these fields are optional.

## B. Real-browser preview (Playwright — closer to Hub)

For full-fidelity verification in a real browser:

1. **Build:** `huitzo dashboard build` → `dist/main.js`.
2. **Serve a preview harness** that imports `dist/main.js`, calls `mount`
   with a `HuitzoMountContext`, and lets you trigger `unmount` by navigating
   away — the dev server's `src/dev.tsx` harness (see `/dashboard-dev`) is
   the local stand-in.
3. **Drive it headless** with Playwright: navigate to the preview, wait for
   first meaningful render, interact, then trigger teardown.
4. **Assert clean teardown:** no console errors, the mount node is empty
   after unmount, no detached React roots remain.

Point the preview's commands at a running sandbox (see `/dashboard-dev` for
how to repoint the dev proxy) so this run hits real command output instead
of mocks.

If a Playwright driver is available in this environment, prefer it for the
browser steps; otherwise the headless Vitest flow (A) is sufficient for CI.

## Steps

1. **Confirm the contract** — `src/main.tsx` exports `mount`/`unmount`
   exactly, wrapped in `HuitzoProvider` + `.huitzo-dashboard`.
2. **Run unit tests first** — `/test-dashboard` should be green.
3. **Run the lifecycle test (A)** — mount with a mock context, assert
   render, unmount, assert clean teardown against the assertion list above.
4. **(Optional) Real-browser preview (B)** — build, serve, drive headless,
   assert clean teardown + no console errors.
5. **Report:** rendered ✓ / unmounted-clean ✓ / no leaks ✓, or each failure
   with the offending selector, timer, or listener.

## Notes

- This is verification, not scaffolding — it does not modify source.
- Both themes matter — re-run with `data-theme="light"` on `<html>` (what the
  dev server's theme toggle flips, see `/dashboard-dev`) to confirm the
  dashboard renders intentionally in light mode (see `dashboard-design.md`).
- Run this before publishing to catch lifecycle leaks that would otherwise
  surface as navigation bugs inside Hub.
