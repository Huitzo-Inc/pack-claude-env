---
paths:
  - "src/**/*.tsx"
  - "src/**/*.ts"
---

# React Patterns

Rules for React dashboard development on the Huitzo platform.

## Framework

- **React 19.2** with TypeScript in strict mode
- **Functional components only** — no class components
- **Hooks only** — no HOCs or render props for new code

## API Calls

**All pack command calls MUST go through `useCommand`.** It is **execute-based** —
it does not auto-run. You trigger the command with `execute(args)` (e.g. from an
effect or an event handler) and read the lifecycle state:

```typescript
const { execute, data, loading, error, status, reset } =
  useCommand<ResultType>('@scope/pack/command');

// Run it — typically on mount or in response to user action:
useEffect(() => { execute({ id }); }, [execute, id]);

// Handle every state:
if (loading) return <LoadingSpinner />;
if (error) return <ErrorMessage error={error} onRetry={() => execute({ id })} />;
if (!data) return <Empty />;        // idle, before the first execute resolves
return <ResultView data={data} />;
```

The full return shape is
`{ execute, data, loading, error, reset, status, isIdle, isSuccess, isError }`
where `status` is `'idle' | 'loading' | 'success' | 'error'`. For auto-running
data fetches, pass `initialArgs`; for live data, pass `refetchInterval` (ms or
`(data) => ms`).

Never use raw `fetch`, `axios`, or direct API calls. The SDK handles auth, base URL, and error formatting.

## Component Structure

```
src/components/{Name}/
├── {Name}.tsx              # Component
├── {Name}.module.css       # Scoped styles (CSS Modules)
└── {Name}.test.tsx         # Tests
```

Pages live at `src/pages/{PageName}.tsx`.

## Styles

Visual design is governed by **`dashboard-design.md`** (hard requirement). The
engineering rules here:

- **CSS Modules** (`.module.css`) for component-specific layout.
- **Tailwind utilities** are allowed for layout only (`flex`, `grid`, `gap-*`).
- **Never global CSS** — no `import './styles.css'` without `.module.css`.
- **Never a hex color, RGB, HSL, or a hex literal in a Tailwind class**
  (`bg-[#155dfc]`). Color, shadow, and radius come from the brand tokens
  (`var(--color-*)`, `--shadow-*`, `--radius-*`) and the `hz-*` primitives. See
  `dashboard-design.md`.

```typescript
import styles from './MyComponent.module.css';

export function MyComponent() {
  return <div className={styles.container}>...</div>;
}
```

## Accessibility

- Clickable non-link elements MUST be `<button>` or have `role="button"` + `tabIndex={0}` + `onKeyDown`
- Form inputs MUST have associated `<label>` elements
- Images MUST have `alt` attributes
- Color alone must not indicate state — use icons or text too
- Focus management for modals: trap focus, restore on close
- Use semantic HTML: `<nav>`, `<main>`, `<section>`, `<article>`

## TypeScript

- Strict mode (`"strict": true` in tsconfig)
- No `any` types — use `unknown` and narrow
- Props interfaces defined and exported per component
- Generic types on hooks: `useCommand<MyType>()`

## State Management

- Local state with `useState` / `useReducer` for component state
- `useCommand` for server state (pack command results)
- Lift state only when siblings need it — avoid prop drilling more than 2 levels
- For complex shared state, use React Context sparingly

## Error Boundaries

The root ErrorBoundary MUST offer a "Return to Hub" action via `context.navigateToHub()` so users aren't stuck:

```typescript
import { ErrorBoundary } from 'react-error-boundary';

function ErrorFallback({ error, resetErrorBoundary }) {
  const { navigateToHub } = useHubNavigation();

  return (
    <div role="alert">
      <p>Something went wrong</p>
      <button onClick={resetErrorBoundary}>Try again</button>
      <button onClick={navigateToHub}>Return to Hub</button>
    </div>
  );
}

// In App.tsx
<ErrorBoundary FallbackComponent={ErrorFallback}>
  <Routes />
</ErrorBoundary>
```

## Testing

Use **Vitest** + **React Testing Library**. Components that use SDK hooks MUST be
rendered inside a **`HuitzoProvider`** — the hooks throw outside a provider:

```typescript
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { HuitzoProvider } from '@huitzo/dashboard-sdk-react';
import { MyComponent } from './MyComponent';

const mockContext = {
  apiUrl: 'http://localhost:8000', getToken: () => 'test-token', slug: 'test',
  sdkVersion: '4.1.0',
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

  it('handles click', async () => {
    const onClick = vi.fn();
    renderWithHuitzo(<MyComponent onClick={onClick} />);
    fireEvent.click(screen.getByRole('button'));
    expect(onClick).toHaveBeenCalled();
  });
});
```

Mock `useCommand` with its **full execute-based return shape** (spread the real
module so `HuitzoProvider` and other hooks survive):

```typescript
vi.mock('@huitzo/dashboard-sdk-react', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@huitzo/dashboard-sdk-react')>()),
  useCommand: () => ({
    execute: vi.fn(),
    reset: vi.fn(),
    data: { result: 'mocked' },
    loading: false,
    error: null,
    status: 'success',
    isIdle: false,
    isSuccess: true,
    isError: false,
  }),
}));
```

## Security

- **Never** use `dangerouslySetInnerHTML` without sanitizing with DOMPurify
- **Never** use `eval()` or `new Function()`
- **Never** log or display auth tokens
- Validate all user input before passing to commands
