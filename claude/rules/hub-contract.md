---
paths:
  - "src/main.tsx"
  - "src/dev.tsx"
  - "dashboard/src/main.tsx"
  - "dashboards/*/src/main.tsx"
---

# Hub Contract Rules

Huitzo Hub loads a dashboard as an isolated React micro-frontend via dynamic
`import()`. `src/main.tsx` is the production entry point Hub calls; `src/dev.tsx`
is the local dev-only stand-in that exercises the same contract against a mock
context. Full reference: the `huitzo-dashboard-sdk` skill.

## Module contract

`src/main.tsx` MUST export exactly these two named functions — nothing else
about the file's shape matters to Hub:

```typescript
export function mount(container: HTMLElement, context: HuitzoMountContext): void;
export function unmount(container: HTMLElement): void;
```

- Hub calls `mount()` when the user navigates to your dashboard, `unmount()`
  when they navigate away.
- `mount` MUST create its own React root in `container` — never assume one
  exists, never touch anything outside `container`.
- `unmount` MUST tear that root down (`root.unmount()`) and null out the
  reference so a stray `mount()` after `unmount()` cannot render into a dead
  root.

## Mandatory: HuitzoProvider + `.huitzo-dashboard` wrapper

```typescript
import { createRoot, type Root } from 'react-dom/client';
import { HuitzoProvider, type HuitzoMountContext } from '@huitzo/dashboard-sdk-react';
import '@huitzo/dashboard-sdk-react/styles';
import App from './App';

let root: Root | null = null;

export function mount(container: HTMLElement, context: HuitzoMountContext): void {
  root = createRoot(container);
  root.render(
    <HuitzoProvider context={context}>
      <div className="huitzo-dashboard">
        <App />
      </div>
    </HuitzoProvider>,
  );
}

export function unmount(_container: HTMLElement): void {
  root?.unmount();
  root = null;
}
```

1. **`HuitzoProvider` wraps the tree.** Every SDK hook (`useCommand`,
   `useHubContext`, `useHubNavigation`, ...) throws if rendered outside it.
   It also owns the token lifecycle — it calls `context.getToken()` for you
   and re-syncs on rotation; do not call `getToken()` yourself outside your
   own request code.
2. **`<div className="huitzo-dashboard">` wraps the app.** Brand tokens and
   `hz-*` primitives resolve only under this class; theme switching
   (dark/light) depends on it too.

## `HuitzoMountContext`

A plain JS object, not a React context — this is only what Hub hands to
`mount()`; you consume it through `HuitzoProvider` and the hooks, not
directly, except in `dev.tsx`'s mock:

```typescript
interface HuitzoMountContext {
  apiUrl: string;
  getToken: () => string;     // getter — call fresh, never store or log the result
  slug: string;
  sdkVersion: string;
  user: { id: string; email: string; name?: string; roles: string[]; tenantId: string };
  theme?: 'light' | 'dark';
  locale?: string;
  currency?: string;
  navigate: (path: string) => void;
  navigateToHub: () => void;
  navigateToDashboard: (slug: string) => void;
  showNotification: (message: string, type: 'info' | 'error' | 'success') => void;
  on: (event: string, handler: (data: unknown) => void) => () => void;
  emit: (event: string, data: unknown) => void;
}
```

`theme`, `locale`, and `currency` are optional — a hook that reads them
(`useHubContext`, `useLocale`) degrades gracefully (a `data-theme`
MutationObserver fallback for theme; `en-US` for locale) when Hub omits them.

## Events vocabulary

Two directions over the **per-mount event bus** exposed as `context.on`/
`context.emit` — this is not a WebSocket and never requires one:

- **Hub → dashboard** (consumed via `useRealtime`): `theme-change`,
  `navigation`, `viewport-resize`, `locale-change`, plus any pack-level event
  Hub chooses to re-emit.
- **Dashboard → Hub** (emitted by `useHubActions`/`useHubBreadcrumbs`):
  `hub-action:toast`, `hub-action:confirm` (+ reply
  `hub-action:confirm-result`), `hub-action:open-settings`,
  `hub-breadcrumbs:set` / `hub-breadcrumbs:clear`.

Prefer the hooks over calling `context.on`/`context.emit` directly — they
handle deduplication and unsubscribe-on-unmount for you.

## Teardown rules

- `unmount()` must leave nothing running: clear every `setInterval`/
  `setTimeout` your dashboard started, remove every manually-added event
  listener, and unsubscribe from every `context.on()` subscription (hooks do
  this for you automatically — a manual `on()` call does not).
- Never rely on the browser tab closing to clean up. Hub reuses the same page
  across many dashboard visits; a leaked timer or listener from one visit
  keeps firing during the next.
- `unmount(container)` receives the same `container` `mount` was given —
  don't assume it still has children by the time `unmount` runs.

## Dev vs production entry

- `src/main.tsx` — production entry, built by Vite in library mode into
  `dist/main.js` (ESM). This is the only file Hub imports.
- `src/dev.tsx` — dev-only entry. Builds a mock `HuitzoMountContext` (fake
  `getToken`, console-logging `navigate`/`emit`, a no-op `on`) and calls the
  real exported `mount()` — so local dev exercises the identical lifecycle
  Hub uses, just against fake data. Never shipped in the production bundle.

## Isolation rules

- Never read or write `window.location` — use `context.navigate()` /
  `context.navigateToHub()` / `context.navigateToDashboard()`.
- Never touch `document.body` or `document.title` — your dashboard owns only
  its `container`.
- Bundle every dependency (no Vite `external`) — the dashboard carries its
  own React, with zero version coupling to Hub.
