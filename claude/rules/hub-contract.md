---
paths:
  - "src/main.tsx"
  - "src/**/*.tsx"
  - "src/**/*.ts"
---

# Hub Contract Rules

Huitzo Hub dashboards are React micro-frontends loaded dynamically by the Hub. These rules ensure your dashboard integrates correctly.

## Module Contract

`src/main.tsx` MUST export exactly two functions:

```typescript
export function mount(container: HTMLElement, context: HuitzoContext): void;
export function unmount(container: HTMLElement): void;
```

- `mount` — Creates a React root in `container`, renders the app with `context`
- `unmount` — Cleans up the React root

Hub calls `mount` when navigating to your dashboard and `unmount` when navigating away.

## HuitzoContext Interface

The `context` parameter is a plain JavaScript object provided by Hub:

```typescript
interface HuitzoContext {
  apiUrl: string;          // Backend API URL
  token: string;           // JWT auth token
  slug: string;            // Dashboard slug
  sdkVersion: string;      // SDK version
  user: {
    id: string;
    email: string;
    roles: string[];
    tenantId: string;
  };
  navigate: (path: string) => void;      // Navigate within Hub
  navigateToHub: () => void;             // Return to Hub home
  showNotification: (message: string, type: string) => void;
  on: (event: string, handler: Function) => () => void;  // Subscribe
  emit: (event: string, data: any) => void;              // Publish
}
```

## Rules

### Isolation
- **Create your own React root** — Call `createRoot(container)` in `mount`. Never assume a root exists.
- **CSS Modules only** — All styles must use `.module.css` suffix. No global CSS that could bleed into Hub.
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
- **Never expose `context.token`** in the UI or logs
- **No `dangerouslySetInnerHTML`** without DOMPurify sanitization
- **No `eval()` or `Function()` constructors**

## Dev Mode vs Production

- `src/main.tsx` — Production entry point (exports `mount`/`unmount`). Vite library mode builds this into `dist/main.js` ESM.
- `src/dev.tsx` — Development entry point. Creates a mock `HuitzoContext` and calls `mount()`. Only used during `npm run dev`. `index.html` loads `dev.tsx`, not `main.tsx`.

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
