---
name: test-pack
description: Run the pack's test suite, with coverage and filter options.
argument-hint: "[-k pattern] [--coverage]"
disable-model-invocation: true
---

# /test-pack

Run the Intelligence Pack's test suite.

## Steps

1. **Parse `$ARGUMENTS`** for an optional `-k <pattern>` (filter by test name)
   and/or `--coverage`.

2. **Prefer the real CLI, when `huitzo` is on PATH:**

   ```bash
   huitzo pack test                    # full suite
   huitzo pack test -k <pattern>       # filtered
   huitzo pack test --coverage         # with coverage report
   ```

3. **Manual fallback** — be honest about environment setup rather than
   assuming one:

   - If a `venv/` or `.venv/` exists, activate it (`source venv/bin/activate`
     or `source .venv/bin/activate`).
   - If the project uses `uv` (a `uv.lock` is present), run `uv run pytest`
     instead of activating a venv by hand.
   - If neither is set up yet, tell the user to run
     `pip install -e ".[dev]"` (or the `uv` equivalent) first — don't silently
     try to install things yourself.
   - Then run: `pytest -v` (add `-k <pattern>` / `--cov` as requested).

4. **On failure, triage before reporting:**
   - **Import errors** — the pack or `huitzo-sdk` isn't installed in the
     active environment. Suggest `pip install -e .`.
   - **Missing fixtures** — check `tests/conftest.py` defines what the failing
     test expects.
   - **Async test errors** — confirm `pytest-asyncio` is installed and
     `[tool.pytest.ini_options] asyncio_mode = "auto"` is in `pyproject.toml`
     (scaffolded packs have this by default — don't add
     `@pytest.mark.asyncio` decorators, they're unnecessary under auto mode).
   - **Genuine test failures** — report file, test name, assertion, and the
     actual vs. expected value; don't just paste the raw pytest output.

5. **Report** the pass/fail/skip summary and call out anything that needs the
   user's attention before merging.
