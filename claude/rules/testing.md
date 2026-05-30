# Testing Rules

## Setup

Tests use `pytest` with `pytest-asyncio`. The pack's `conftest.py` is auto-generated with common fixtures.

```bash
source venv/bin/activate
pytest -v
```

## Test File Naming

- One test file per command: `tests/test_{command_name}.py`
- Test file mirrors command file: `commands/analyze.py` → `tests/test_analyze.py`

## Async Test Pattern

All command tests must be async. Commands take **two** arguments — `async def fn(args, ctx)` — so every call passes the `mock_ctx` fixture (defined below) alongside the args model:

```python
import pytest
from my_pack.commands.analyze import analyze_text, AnalyzeArgs

@pytest.mark.asyncio
async def test_analyze_text_basic(mock_ctx):
    """Test basic analysis."""
    args = AnalyzeArgs(text="Hello world", language="en")
    result = await analyze_text(args, mock_ctx)

    assert "analysis" in result
    assert result["language"] == "en"
```

## Mock Context

Context services are not available in tests. Create a mock — put this fixture in `tests/conftest.py` so every test file can use it:

```python
from unittest.mock import AsyncMock, MagicMock
from huitzo_sdk import Context

@pytest.fixture
def mock_ctx():
    """Create a mock Context with stubbed services."""
    ctx = MagicMock(spec=Context)
    ctx.llm = AsyncMock()
    ctx.http = AsyncMock()
    ctx.email = AsyncMock()
    ctx.telegram = AsyncMock()
    ctx.files = AsyncMock()
    ctx.storage = AsyncMock()      # async key/value storage (get/save)
    ctx.secrets = MagicMock()      # secrets.require()/get() are sync
    ctx.command_name = "test-command"
    ctx.namespace = "test-pack"
    return ctx
```

Then use it in tests:

```python
@pytest.mark.asyncio
async def test_command_uses_llm(mock_ctx):
    """Test command that calls LLM."""
    mock_ctx.llm.chat.return_value = {"content": "response"}

    args = MyArgs(prompt="Hello")
    result = await my_command(args, mock_ctx)

    mock_ctx.llm.chat.assert_called_once()
    assert result["response"] == "response"
```

## Pydantic Validation Testing

Test that invalid inputs are rejected:

```python
import pytest
from pydantic import ValidationError

def test_args_rejects_empty_text():
    """Test that empty text is rejected."""
    with pytest.raises(ValidationError):
        AnalyzeArgs(text="")

def test_args_rejects_invalid_count():
    """Test count must be positive."""
    with pytest.raises(ValidationError):
        AnalyzeArgs(text="hello", count=-1)

def test_args_defaults():
    """Test default values are applied."""
    args = AnalyzeArgs(text="hello")
    assert args.language == "en"
    assert args.max_tokens == 1000
```

## Test Structure

```python
"""
Module: test_analyze
Description: Tests for the analyze command

Implements:
    - docs/commands/analyze-text.md
"""

import pytest
from my_pack.commands.analyze import analyze_text, AnalyzeArgs

class TestAnalyzeText:
    """Tests for analyze_text command."""

    @pytest.mark.asyncio
    async def test_basic_analysis(self, mock_ctx):
        """Test basic text analysis."""
        args = AnalyzeArgs(text="Hello world")
        result = await analyze_text(args, mock_ctx)
        assert "analysis" in result

    @pytest.mark.asyncio
    async def test_with_language(self, mock_ctx):
        """Test with explicit language."""
        args = AnalyzeArgs(text="Hola mundo", language="es")
        result = await analyze_text(args, mock_ctx)
        assert result["language"] == "es"

    def test_invalid_args(self):
        """Test validation rejects bad input."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            AnalyzeArgs(text="")
```

## Coverage

Run with coverage to ensure all commands are tested:

```bash
pytest --cov=src/ --cov-report=term-missing -v
```

Every command function must have at least one test. Untested commands will be flagged during review.

---

## Dashboard Testing

Dashboard tests use **Vitest** + **React Testing Library**.

### Setup

```bash
npm test
```

### Test File Naming

- Component tests: `src/components/{Name}/{Name}.test.tsx`
- Page tests: `src/pages/{PageName}.test.tsx`

### Component Test Pattern

```typescript
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { MyComponent } from './MyComponent';

describe('MyComponent', () => {
  it('renders correctly', () => {
    render(<MyComponent title="Test" />);
    expect(screen.getByText('Test')).toBeInTheDocument();
  });

  it('handles user interaction', async () => {
    const onSubmit = vi.fn();
    render(<MyComponent onSubmit={onSubmit} />);
    fireEvent.click(screen.getByRole('button', { name: /submit/i }));
    expect(onSubmit).toHaveBeenCalled();
  });
});
```

### Wrap components in `HuitzoProvider`

SDK hooks (`useCommand`, `useHubContext`, ...) only work inside a `HuitzoProvider`. Render components under a provider with a mock mount context — define a small `renderWithHuitzo` helper and reuse it:

```typescript
import { render } from '@testing-library/react';
import { HuitzoProvider } from '@huitzo/dashboard-sdk-react';
import type { ReactElement } from 'react';

const mockContext = {
  apiUrl: 'http://localhost:8000',
  getToken: () => 'test-token',
  slug: 'test-dashboard',
  sdkVersion: '4.1.0',
  user: { id: '1', email: 'test@test.com', roles: ['admin'], tenantId: 't1' },
  navigate: vi.fn(),
  navigateToHub: vi.fn(),
  navigateToDashboard: vi.fn(),
  showNotification: vi.fn(),
  on: vi.fn(() => vi.fn()),
  emit: vi.fn(),
};

function renderWithHuitzo(ui: ReactElement) {
  return render(<HuitzoProvider context={mockContext}>{ui}</HuitzoProvider>);
}
```

### Mock useCommand

`useCommand` is **execute-based**: it returns `{ execute, data, loading, error, reset, status, isIdle, isSuccess, isError }`. Calling code triggers a command with `execute(args)` — it does NOT auto-run. Mock the full shape so components don't crash reading `status`/`reset`:

```typescript
import { vi } from 'vitest';

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

Spreading `importOriginal()` keeps `HuitzoProvider` and the other hooks intact while overriding only `useCommand`.

### What to Test

- Rendering with props (under `renderWithHuitzo`)
- User interactions (click, type, keyboard) and that they call `execute`
- Loading states (when `useCommand` returns `loading: true` / `status: 'loading'`)
- Error states (when `useCommand` returns an error / `status: 'error'`)
- Accessibility (roles, labels, keyboard navigation)
