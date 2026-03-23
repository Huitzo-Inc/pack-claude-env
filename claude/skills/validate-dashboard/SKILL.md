---
description: Validate dashboard manifest, bundle, Hub contract, and traceability
disable-model-invocation: true
---

# /validate-dashboard

Validate the dashboard project structure, manifest, Hub contract, and code quality.

## Steps

1. **Check `huitzo-dashboard.yaml`** exists and validates:
   - `dashboard.name` — present, kebab-case, 3-50 characters
   - `dashboard.namespace` — present, lowercase no hyphens, 2-20 characters
   - `dashboard.version` — present, valid semver
   - `dashboard.description` — present, 10-200 characters
   - `dashboard.visibility` — one of: public, unlisted, organization, private
   - `pack_dependencies` — present (can be empty array)
   - `build.entry_point` — must be `main.js`
   - `build.output_directory` — must be `dist`

2. **Check Hub contract** — verify `src/main.tsx`:
   - File exists
   - Contains `export function mount`
   - Contains `export function unmount`

3. **Check traceability headers** — for each `.tsx` and `.ts` file in `src/`:
   - File has a JSDoc comment containing `@implements`
   - Count files with and without headers

4. **Check CSS isolation** — for each CSS import in `src/`:
   - All CSS imports use `.module.css` suffix
   - No bare `.css` imports

5. **Run type checking** (if TypeScript is configured):
   ```bash
   npx tsc --noEmit 2>&1
   ```

6. **Check build output** (if `dist/` exists):
   - `dist/main.js` exists
   - File contains `mount` and `unmount` (basic export check)
   - File size is under 50 MB

7. **Report results as a checklist**:
   ```
   Dashboard Validation Results
   ────────────────────────────
   Manifest (huitzo-dashboard.yaml)  ✓ valid
   Hub contract (mount/unmount)      ✓ exports present
   Traceability headers              ✓ 12/12 files
   CSS isolation                     ✓ all CSS Modules
   Type checking (tsc)               ✓ no errors
   Build output (dist/)              ✓ 1.2 MB, exports OK
   ```
