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

**All pack command calls MUST go through `useCommand`:**

```typescript
const { execute, data, loading, error } = useCommand<ResultType>('@scope/pack/command');

// Every useCommand must handle all three states:
if (loading) return <LoadingSpinner />;
if (error) return <ErrorMessage error={error} />;
return <ResultView data={data} />;
```

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

- **CSS Modules** (`.module.css`) for component-specific styles
- **Tailwind utilities** for layout and common patterns
- **Never global CSS** — no `import './styles.css'` without `.module.css`

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

```typescript
import { ErrorBoundary } from 'react-error-boundary';

function ErrorFallback({ error, resetErrorBoundary }) {
  return (
    <div role="alert">
      <p>Something went wrong</p>
      <button onClick={resetErrorBoundary}>Try again</button>
    </div>
  );
}

// In App.tsx
<ErrorBoundary FallbackComponent={ErrorFallback}>
  <Routes />
</ErrorBoundary>
```

## Testing

Use **Vitest** + **React Testing Library**:

```typescript
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { MyComponent } from './MyComponent';

describe('MyComponent', () => {
  it('renders correctly', () => {
    render(<MyComponent title="Test" />);
    expect(screen.getByText('Test')).toBeInTheDocument();
  });

  it('handles click', async () => {
    const onClick = vi.fn();
    render(<MyComponent onClick={onClick} />);
    fireEvent.click(screen.getByRole('button'));
    expect(onClick).toHaveBeenCalled();
  });
});
```

Mock `useCommand` in tests:

```typescript
vi.mock('@huitzo/dashboard-sdk-react', () => ({
  useCommand: () => ({
    execute: vi.fn(),
    data: { result: 'mocked' },
    loading: false,
    error: null,
  }),
}));
```

## Security

- **Never** use `dangerouslySetInnerHTML` without sanitizing with DOMPurify
- **Never** use `eval()` or `new Function()`
- **Never** log or display auth tokens
- Validate all user input before passing to commands
