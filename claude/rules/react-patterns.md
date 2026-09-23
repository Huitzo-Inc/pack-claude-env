---
paths:
  - "src/**/*.tsx"
  - "src/**/*.ts"
  - "dashboard/src/**/*.{ts,tsx}"
  - "dashboards/*/src/**/*.{ts,tsx}"
---

# React Patterns

Engineering rules for React dashboard development on the Huitzo platform.
Visual design is governed separately by `dashboard-design.md` — read that
before writing UI markup. Full SDK reference: the `huitzo-dashboard-sdk` skill.

## Framework

- **React 19.2** with TypeScript in **strict mode**.
- **Functional components only** — no class components.
- **Hooks only** — no HOCs or render-props for new code.

## API calls

**All pack command calls MUST go through `useCommand`.** It is
execute-based — it does not auto-run unless you pass `initialArgs`:

```typescript
const { execute, data, loading, error, status, isPolling, reset } =
  useCommand<ResultType>('@scope/pack/command');

useEffect(() => { execute({ id }); }, [execute, id]);

if (loading) return isPolling ? <QueuedState /> : <LoadingSpinner />;
if (error) return <ErrorMessage error={error} onRetry={() => execute({ id })} />;
if (!data) return <Empty />;
return <ResultView data={data} />;
```

`status` is **five-state**: `'idle' | 'loading' | 'polling' | 'success' | 'error'`.
A command on a medium/long queue dispatches a 202 receipt and the hook enters
`polling` while it waits for the real result — `loading` is `true` for both
`loading` and `polling`, so check `isPolling` when you want to show a
"queued" state instead of a generic spinner. Never assume a 4-state status.

`execute()` resolves `Promise<T | undefined>` (the result, or `undefined` on
error, abort, or supersession) and never rejects. For a command that can run
past the 5 minute poll budget, pass `poll: { maxWaitMs }` (30 minute ceiling)
rather than writing your own poll loop.

Never use raw `fetch`, `axios`, or a direct API call — the SDK client handles
auth, base URL, retries, and error mapping.

## Component structure

```
src/components/{Name}/
├── {Name}.tsx              # Component
├── {Name}.module.css       # Scoped styles (or CSS scoped under .huitzo-dashboard)
└── {Name}.test.tsx         # Tests
```

Pages live at `src/pages/{PageName}.tsx`.

## Styles

Visual design is governed by `dashboard-design.md` (hard requirement). The
engineering rule here: every stylesheet must be scoped so it cannot leak into
Hub or another mounted dashboard. Two patterns are both acceptable —

- **CSS Modules** (`{Name}.module.css`) for component-local styles.
- **Plain CSS scoped under `.huitzo-dashboard`** (the CLI scaffold's
  `App.css`/`index.css` use this pattern) — every rule nests under or targets
  a class inside `.huitzo-dashboard`.

What is never acceptable: a bare global element selector (`button { }`,
`a { }`, `:root { }`) anywhere in a dashboard's CSS — it escapes the mount
boundary. Tailwind utilities are allowed for layout (`flex`, `grid`, `gap-*`)
only; color/shadow/radius come from tokens or `hz-*` primitives — see
`dashboard-design.md`.

```typescript
import styles from './MyComponent.module.css';

export function MyComponent() {
  return <div className={styles.container}>...</div>;
}
```

## Accessibility

- Clickable non-link elements MUST be `<button>` or have `role="button"` +
  `tabIndex={0}` + `onKeyDown`.
- Form inputs MUST have associated `<label>` elements.
- Images MUST have `alt` attributes.
- Color alone must not indicate state — pair it with an icon or text.
- Modals trap focus and restore it on close.
- Prefer semantic HTML: `<nav>`, `<main>`, `<section>`, `<article>`.

## TypeScript

- Strict mode (`"strict": true` in `tsconfig.json`).
- No `any` — use `unknown` and narrow.
- Export a props interface per component.
- Generic types on hooks: `useCommand<MyType>('@scope/pack/command')`, or the
  typed `CommandRef` overload when `@huitzo/dashboard-codegen` is available.

## State management

- Local component state: `useState` / `useReducer`.
- Server state (pack command results): `useCommand` — do not duplicate its
  cache into your own `useState`.
- Lift state only when siblings need it; avoid prop-drilling past 2 levels.
- Reach for React Context sparingly, for genuinely cross-cutting state.

## Error boundaries

Wrap the root in an error boundary whose fallback offers a way back to Hub —
a dashboard-tree error does not propagate to Hub's own boundary:

```typescript
function ErrorFallback({ error, resetErrorBoundary }: FallbackProps) {
  const { navigateToHub } = useHubNavigation();
  return (
    <div role="alert">
      <p>Something went wrong.</p>
      <button onClick={resetErrorBoundary}>Try again</button>
      <button onClick={navigateToHub}>Return to Hub</button>
    </div>
  );
}
```

## Testing

Use **Vitest** + **React Testing Library**. Any component that calls an SDK
hook MUST be rendered inside a **`HuitzoProvider`** — hooks throw outside one:

```typescript
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { HuitzoProvider, type HuitzoMountContext } from '@huitzo/dashboard-sdk-react';
import { MyComponent } from './MyComponent';

const mockContext: HuitzoMountContext = {
  apiUrl: 'http://localhost:8000', getToken: () => 'test-token', slug: 'test',
  sdkVersion: '7.0.0',
  user: { id: '1', email: 'a@b.com', roles: ['admin'], tenantId: 't1' },
  navigate: vi.fn(), navigateToHub: vi.fn(), navigateToDashboard: vi.fn(),
  showNotification: vi.fn(), on: vi.fn(() => vi.fn()), emit: vi.fn(),
};

function renderWithHuitzo(ui: React.ReactElement) {
  return render(<HuitzoProvider context={mockContext}>{ui}</HuitzoProvider>);
}

describe('MyComponent', () => {
  it('renders correctly', () => {
    renderWithHuitzo(<MyComponent title="Test" />);
    expect(screen.getByText('Test')).toBeInTheDocument();
  });

  it('handles click', () => {
    const onClick = vi.fn();
    renderWithHuitzo(<MyComponent onClick={onClick} />);
    fireEvent.click(screen.getByRole('button'));
    expect(onClick).toHaveBeenCalled();
  });
});
```

Mock `useCommand` with its full five-state return shape (spread the real
module so `HuitzoProvider` and other hooks survive):

```typescript
vi.mock('@huitzo/dashboard-sdk-react', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@huitzo/dashboard-sdk-react')>()),
  useCommand: () => ({
    execute: vi.fn(async () => ({ result: 'mocked' })), reset: vi.fn(),   // resolves the result
    data: { result: 'mocked' }, loading: false, error: null,
    status: 'success', isIdle: false, isPolling: false, isSuccess: true, isError: false,
  }),
}));
```

## Security

- Never use `dangerouslySetInnerHTML` without sanitizing (e.g. DOMPurify).
- Never use `eval()` or `new Function()`.
- Never log, store, or display the token from `context.getToken()`.
- Validate user input before passing it into a command's `args`.

## Traceability

Every `.ts`/`.tsx` source file carries a header pointing at the doc it
implements:

```typescript
/**
 * Module: ComponentName
 * Description: Brief description
 *
 * @implements docs/components/ComponentName.md
 */
```
