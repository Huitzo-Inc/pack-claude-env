---
paths:
  - "src/main.tsx"
  - "src/**/*.tsx"
  - "src/**/*.ts"
---

# Hub Contract Rules

> Reference: `docs/dashboards/loading.md` — the single source of truth for the
> runtime loading pipeline and module contract.

Huitzo Hub dashboards are React micro-frontends loaded dynamically by the Hub. These rules ensure your dashboard integrates correctly.

## Module Contract

`src/main.tsx` MUST export exactly two functions:

```typescript
export function mount(container: HTMLElement, context: HuitzoContext): void;
export function unmount(container: HTMLElement): void;
```

- `mount` — Creates a React root in `container`, wraps the app in
  `HuitzoProvider`, and renders it with `context`.
- `unmount` — Cleans up the React root.

Hub calls `mount` when navigating to your dashboard and `unmount` when navigating away.

## Mandatory: HuitzoProvider + huitzo-dashboard wrapper

You do **not** wire the context manually. Hub passes a vanilla `HuitzoContext`
object to `mount`; you hand that object to **`HuitzoProvider`**, which exposes it
to React context so every SDK hook (`useCommand`, `useHubContext`,
`useHubNavigation`, ...) works. This is required — hooks throw outside a provider.

```typescript
import { createRoot, type Root } from 'react-dom/client';
import type { HuitzoContext } from '@huitzo/dashboard-sdk';
import { HuitzoProvider } from '@huitzo/dashboard-sdk-react';
import '@huitzo/dashboard-sdk-react/styles';   // brand tokens + hz-* primitives
import App from './App';

let root: Root | null = null;

export function mount(container: HTMLElement, context: HuitzoContext): void {
  root = createRoot(container);
  root.render(
    <HuitzoProvider context={context}>
      <div className="huitzo-dashboard">
        <App />
      </div>
    </HuitzoProvider>
  );
}

export function unmount(_container: HTMLElement): void {
  root?.unmount();
  root = null;
}
```

Two non-negotiables:

1. **`HuitzoProvider`** wraps your tree. It calls `context.getToken()` for you
   automatically — never call `context.getToken()` to surface the JWT yourself.
2. **`<div className="huitzo-dashboard">`** wraps your app so the brand tokens
   resolve and theme switching (dark/light) works. See `dashboard-design.md`.

## HuitzoContext Interface

The `context` parameter is a plain JavaScript object provided by Hub. You rarely
touch it directly — `HuitzoProvider` and the hooks consume it for you.

```typescript
interface HuitzoContext {
  apiUrl: string;          // Backend API URL
  getToken: () => string;  // returns the JWT on demand (getter, not a property — never store/log/surface it)
  slug: string;            // Dashboard slug
  sdkVersion: string;      // Hub's SDK version (for compatibility checks)
  user: {
    id: string;
    email: string;
    roles: string[];
    tenantId: string;
  };
  navigate: (path: string) => void;            // Navigate within Hub
  navigateToHub: () => void;                   // Return to Hub home
  navigateToDashboard: (slug: string) => void; // Jump to another dashboard
  showNotification: (message: string, type: 'info' | 'error' | 'success') => void;
  on: (event: string, handler: (data: unknown) => void) => () => void;
  emit: (event: string, data: unknown) => void;
}
```

## Rules

### Isolation
- **Create your own React root** — Call `createRoot(container)` in `mount`, then wrap the tree in `HuitzoProvider` + the `huitzo-dashboard` div. Never assume a root exists.
- **CSS Modules only** — All component styles use the `.module.css` suffix. No global CSS that could bleed into Hub. Color/shadow/radius come from brand tokens — see `dashboard-design.md`.
- **Bundle everything** — Do not mark React or other deps as `external` in Vite config. Hub does not provide shared modules.

### Navigation
- **Use `context.navigate()`** for all in-Hub navigation
- **Use `context.navigateToHub()`** to return to Hub home
- **Never use `window.location`** directly — Hub manages routing

### DOM
- **Never modify `document.body`** — Your dashboard lives inside `container` only
- **Never add global event listeners** without cleaning them up in `unmount`
- **No `document.title` changes** — Hub manages the page title

### Error Handling
- **Wrap root in `ErrorBoundary`** — The fallback must call `context.navigateToHub()` so users aren't stuck
- **Handle all async errors** — Every `useCommand` must handle loading and error states
- **Show actionable error messages** — Tell users what to do, not just what went wrong

### Security
- **Never expose the JWT from `context.getToken()`** in the UI or logs
- **No `dangerouslySetInnerHTML`** without DOMPurify sanitization
- **No `eval()` or `Function()` constructors**

## Dev Mode vs Production

- `src/main.tsx` — Production entry point (exports `mount`/`unmount`). Vite library mode builds this into `dist/main.js` ESM.
- `src/dev.tsx` — Development entry point. Creates a mock `HuitzoContext` and calls `mount()` (so it goes through the same `HuitzoProvider` + `huitzo-dashboard` wrapper path). Only used during `npm run dev`. `index.html` loads `dev.tsx`, not `main.tsx`.

## Vite Configuration

Production build must use library mode:

```typescript
// vite.config.ts
build: {
  lib: {
    entry: 'src/main.tsx',
    formats: ['es'],
    fileName: 'main',
  },
}
```
