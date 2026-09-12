---
paths:
  - "tests/**/*.py"
  - "pack/tests/**/*.py"
  - "packs/*/tests/**/*.py"
  - "conftest.py"
---

# Testing

Full patterns and a worked mock-`Context` example: the `huitzo-sdk` skill.
This rule is the condensed, path-scoped version (the always-on core is
`00-huitzo-core.md`).

## What a scaffolded pack actually has

`huitzo pack new` generates `pyproject.toml` with:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"   # async tests need no @pytest.mark.asyncio decorator
testpaths = ["tests"]

[tool.mypy]
strict = true

[tool.ruff]
target-version = "py311"
line-length = 100
```

`conftest.py` only adds `src/` to `sys.path` — there is **no** shared
`mock_ctx` fixture, no factory-boy, no faker, no pytest plugins beyond
`pytest-asyncio`/`pytest-cov`/`mypy`/`ruff` (the scaffold's own
`dev_dependencies`). If you want a shared mock-Context fixture, write it
yourself in `conftest.py` — don't assume one already exists.

## Pattern 1 — pure helpers first

Extract logic into a plain function your command delegates to; test it with
no `Context` and no `async` at all:

```python
def greet(name: str) -> str:
    return f"Hello, {name}!"

def test_greet() -> None:
    assert greet("Alice") == "Hello, Alice!"
```

This is the cheapest, fastest test in the suite — prefer it whenever the
logic doesn't actually need `ctx`.

## Pattern 2 — bare `Context()`

For a command that touches no service, call the decorated function directly
with a default `Context()`:

```python
from huitzo_sdk import Context
from my_pack.commands.hello import hello_world

async def test_hello_world() -> None:
    result = await hello_world({}, Context())
    assert result["message"] == "Hello, World!"
```

## Pattern 3 — `MagicMock(spec=Context)` + `AsyncMock`

For a command that calls services, mock only the ones it uses. Every service
is awaited except `ctx.log` (sync):

```python
from unittest.mock import AsyncMock, MagicMock
from huitzo_sdk import Context

def make_mock_ctx() -> MagicMock:
    ctx = MagicMock(spec=Context)
    ctx.llm = AsyncMock()
    ctx.secrets = AsyncMock()   # require/get/exists are all async
    ctx.log = MagicMock()       # sync — the one exception
    return ctx

async def test_calls_llm() -> None:
    ctx = make_mock_ctx()
    ctx.secrets.require.return_value = "sk-test"
    ctx.llm.complete.return_value = "the answer"
    result = await analyze_text({"text": "hi"}, ctx)
    ctx.llm.complete.assert_awaited_once()
    assert result["answer"] == "the answer"
```

`ctx.files.list()` returns `list[dict]`, never `list[str]` — stub it as
dicts (`[{"name": "a.json"}, ...]`), not bare filenames.

## Testing storage without a real backend

`InMemoryBackend`, `StorageClient`, and `StorageNamespace` are all public and
importable directly from `huitzo_sdk`:

```python
from uuid import uuid4
from huitzo_sdk import InMemoryBackend, StorageClient, StorageNamespace

async def test_storage_roundtrip() -> None:
    namespace = StorageNamespace(tenant_id=uuid4(), user_id=uuid4(), pack_id="my-pack")
    storage = StorageClient(InMemoryBackend(), namespace)
    await storage.save("key", {"value": 1})
    assert await storage.get("key") == {"value": 1}
```

Use this for a command's own storage-adjacent logic; don't use it to test
the SDK's storage backend itself — that's already covered upstream.

## Manifest contract test

Assert `huitzo.yaml` actually parses and validates, once per pack:

```python
from pathlib import Path
from huitzo_sdk.manifest import load_manifest

def test_manifest_is_valid() -> None:
    manifest = load_manifest(Path(__file__).parent.parent / "huitzo.yaml")
    assert manifest.pack.namespace == "my-pack"
```

This catches a schema drift (missing `policy:`, an unbacked permission
token, `extra="forbid"` violations) before `huitzo pack validate` does.

## What NOT to test

Don't test the platform: timeout enforcement, retry/backoff, queue dispatch,
the stale-execution reaper, SSRF blocking, DDL rejection, or anything else
the SDK itself already guarantees. Test *your* command logic — what it does
with a given `args`/`ctx`, and what it raises when a dependency fails.

## Running tests

```bash
huitzo pack test          # preferred, if the CLI is installed
pytest -v                 # direct invocation
pytest --cov=src/ --cov-report=term-missing -v   # with coverage
```

Every command function should have at least one test.
