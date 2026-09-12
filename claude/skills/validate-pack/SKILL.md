---
name: validate-pack
description: Validate a pack's manifest, entry points, traceability, and lint/type checks.
disable-model-invocation: true
---

# /validate-pack

Validate the Intelligence Pack's structure and quality.

## Steps

1. **Prefer the real CLI, when `huitzo` is on PATH:**

   ```bash
   huitzo pack validate --strict
   # or, to parse programmatically:
   huitzo pack validate --strict --json
   ```

   The `--json` shape is `{"ok": bool, "errors": [...], "warnings": [...]}`.
   Report every entry in `errors`; treat `warnings` as non-blocking notes.

2. **Manual fallback**, if the CLI is unavailable — walk the checks it would
   run:

   a. **Manifest loads.** `huitzo.yaml` is valid YAML, `schema_version: 2` is
      present, and it validates against the schema (no unknown keys, no
      missing `policy:`, `commands` has at least one entry). See the
      `huitzo-manifest` skill for the full schema if an error is unclear.

   b. **Entry points resolve.** For each `commands[].entry_point`
      (`module.path:function`), confirm the module and function actually
      exist under `src/`.

   c. **Namespace match.** Every command's `@command(..., namespace=...)` in
      code equals `pack.namespace` in `huitzo.yaml`.

   d. **Permission backing.** Every token in `permissions:` has its declared
      service (see the permission↔service table in the `pack-manifest` rule)
      and is also present in `policy.allowed_actions`.

   e. **Traceability headers.** Every `.py` file under `src/` and `tests/` has
      a module docstring with an `Implements:` block pointing at a
      `docs/commands/*.md` file that exists.

   f. **Lint/type check**, if the tools are installed:

      ```bash
      ruff check .
      mypy --strict src/
      ```

3. **Report as a checklist:**

   ```
   Manifest (huitzo.yaml)     ✓ valid
   Entry points               ✓ 3/3 resolve
   Namespace match             ✓ consistent
   Permission backing          ✓ consistent
   Traceability headers        ✓ 6/6 files
   Linting (ruff)               ✓ no issues
   Type checking (mypy)         ✗ 2 errors (list them)
   ```
