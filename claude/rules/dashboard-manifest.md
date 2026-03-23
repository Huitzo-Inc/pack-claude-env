---
paths:
  - "huitzo-dashboard.yaml"
---

# Dashboard Manifest Rules

The `huitzo-dashboard.yaml` manifest defines your dashboard's identity, dependencies, and build configuration.

## Required Fields

```yaml
dashboard:
  name: my-dashboard           # kebab-case, 3-50 characters
  namespace: mynamespace       # lowercase, no hyphens, 2-20 characters
  version: 1.0.0               # Valid semver
  description: "..."           # 10-200 characters
  visibility: private          # public | unlisted | organization | private
  author: Your Name

pack_dependencies:             # Packs this dashboard consumes
  - scope: "@my-scope"
    name: "my-pack"
    version: ">=1.0.0"
    required: true             # true = dashboard won't install without this pack

build:
  framework: react
  node_version: ">=20.0.0"
  build_command: npm run build
  output_directory: dist
  entry_point: main.js         # Must be main.js (convention)
```

## Validation Rules

### Name
- Must be kebab-case (`[a-z0-9-]+`)
- 3 to 50 characters
- Must start with a letter

### Namespace
- Lowercase letters and numbers only (no hyphens)
- 2 to 20 characters
- Must start with a letter

### Version
- Must be valid semver (e.g., `1.0.0`, `0.1.0-beta.1`)

### Description
- 10 to 200 characters
- Must be meaningful (not just the name repeated)

### Visibility
- Must be one of: `public`, `unlisted`, `organization`, `private`

### Pack Dependencies
- Every pack your dashboard imports commands from must be listed
- `scope` must start with `@`
- `version` must be a valid semver range
- Set `required: true` for packs the dashboard cannot function without

### Build
- `framework` must be `react` (for now)
- `entry_point` must be `main.js`
- `output_directory` must be `dist`

## Validation

Run before every commit:

```bash
huitzo dashboard validate
```

This checks the manifest, verifies the bundle exports `mount`/`unmount`, and validates bundle size (< 50 MB).
