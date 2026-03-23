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

All command tests must be async:

```python
import pytest
from my_pack.commands.analyze import analyze_text, AnalyzeArgs

@pytest.mark.asyncio
async def test_analyze_text_basic():
    """Test basic analysis."""
    args = AnalyzeArgs(text="Hello world", language="en")
    result = await analyze_text(args)

    assert "analysis" in result
    assert result["language"] == "en"
```

## Mock Context

Context services are not available in tests. Create a mock:

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
    - docs/sdk/commands.md
"""

import pytest
from my_pack.commands.analyze import analyze_text, AnalyzeArgs

class TestAnalyzeText:
    """Tests for analyze_text command."""

    @pytest.mark.asyncio
    async def test_basic_analysis(self):
        """Test basic text analysis."""
        args = AnalyzeArgs(text="Hello world")
        result = await analyze_text(args)
        assert "analysis" in result

    @pytest.mark.asyncio
    async def test_with_language(self):
        """Test with explicit language."""
        args = AnalyzeArgs(text="Hola mundo", language="es")
        result = await analyze_text(args)
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

### Mock useCommand

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

### Mock HuitzoContext (for main.tsx tests)

```typescript
const mockContext: HuitzoContext = {
  apiUrl: 'http://localhost:8000',
  token: 'test-token',
  slug: 'test-dashboard',
  sdkVersion: '1.0.0',
  user: { id: '1', email: 'test@test.com', roles: ['admin'], tenantId: 't1' },
  navigate: vi.fn(),
  navigateToHub: vi.fn(),
  showNotification: vi.fn(),
  on: vi.fn(() => vi.fn()),
  emit: vi.fn(),
};
```

### What to Test

- Rendering with props
- User interactions (click, type, keyboard)
- Loading states (when `useCommand` returns `loading: true`)
- Error states (when `useCommand` returns an error)
- Accessibility (roles, labels, keyboard navigation)
