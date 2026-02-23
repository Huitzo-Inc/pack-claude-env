---
description: Run pack tests with virtual environment activation
disable-model-invocation: true
---

# /test-pack

Run the Intelligence Pack's test suite.

## Steps

1. **Check the virtual environment exists** at `venv/`. If not, tell the user to run:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -e ".[dev]"
   ```

2. **Run the tests**:
   ```bash
   source venv/bin/activate && pytest -v
   ```

3. **If tests fail**, analyze the output:
   - **Import errors**: Usually means the pack or SDK isn't installed in the venv. Suggest `pip install -e .` and `pip install huitzo-sdk`.
   - **Missing fixtures**: Check `tests/conftest.py` exists and has required fixtures.
   - **Async errors**: Ensure `pytest-asyncio` is installed and tests use `@pytest.mark.asyncio`.
   - **Actual test failures**: Report the failures clearly with file, test name, and error.

4. **Report results**: Show the summary (passed/failed/skipped counts) and highlight any failures that need attention.
