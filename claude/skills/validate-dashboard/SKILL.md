---
name: validate-dashboard
description: Validate the dashboard manifest, module contract, CSS isolation, tokens, and build output.
disable-model-invocation: true
---

# /validate-dashboard

Validate the dashboard project's manifest, Hub contract, and code quality.

## Steps

1. **Prefer the real CLI, when `huitzo` is on PATH:**

   ```bash
   huitzo dashboard validate
   # or, to parse programmatically:
   huitzo --output json dashboard validate
   ```

   This checks `huitzo-dashboard.yaml` (required fields, kebab-case name,
   semver version, valid `visibility`) and, when `dist/` exists, the bundle
   (entry point exists, valid ESM, exports `mount`/`unmount`, under the
   platform's size limit). Under `--output json` the envelope's `data` is
   `{name, version, valid, errors?}` — report every entry in `errors` and
   treat a non-`valid` result as a hard failure.

2. **Manual checklist**, if the CLI is unavailable or you want to check
   beyond what it covers — see `dashboard-manifest.md` for the full field
   table:

   a. **Manifest fields.** `dashboard.name`/`namespace`/`version`/
      `description` present; `visibility` is one of
      `public|unlisted|organization|private`; `pack_dependencies` present
      (may be `[]`); `build.entry_point` matches the Vite `lib.fileName`
      output.

   b. **Module contract** (`src/main.tsx`):
      - Exports `mount(container, context)` and `unmount(container)`.
      - `mount` wraps the tree in `HuitzoProvider` **and**
        `<div className="huitzo-dashboard">` — both are mandatory (see
        `hub-contract.md`).

   c. **Design tokens** — grep `src/**/*.{tsx,css}` for a raw hex/rgb/hsl color or a Tailwind hex class (`bg-[#...]`); every color should resolve through `var(--color-*)` or an `hz-*` primitive. ❌ Flag any `hz-arch` reference — it ships no CSS.

   d. **CSS isolation** — grep for a bare global element selector
      (`button {`, `a {`, `:root {`) outside a `.module.css` file or a rule
      scoped under `.huitzo-dashboard`.

   e. **Traceability headers** — every `.tsx`/`.ts` file under `src/` has a
      header with `@implements docs/components/*.md` or
      `docs/pages/*.md`.

   f. **Type checking**, if configured:
      ```bash
      npm run typecheck
      ```

   g. **Build output**, if `dist/` exists:
      - `dist/main.js` exists, is valid ESM, and contains `mount`/`unmount`.
      - Bundle size is under the platform's size limit.

3. **Report as a checklist:**

   ```
   Manifest (huitzo-dashboard.yaml)  ✓ valid
   Module contract (mount/unmount)   ✓ exports present, Provider + wrapper OK
   Design tokens                     ✓ no hex/rgb/hsl literals found
   CSS isolation                     ✓ no global selectors
   Traceability headers              ✓ 12/12 files
   Type checking (tsc)               ✓ no errors
   Build output (dist/)              ✓ 1.2 MB, mount/unmount present
   ```
