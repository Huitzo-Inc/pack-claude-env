---
paths:
  - "huitzo-dashboard.yaml"
  - "dashboard/huitzo-dashboard.yaml"
  - "dashboards/*/huitzo-dashboard.yaml"
---

# Dashboard Manifest Rules

`huitzo-dashboard.yaml` defines your dashboard's identity, pack dependencies,
and build configuration. It lives at the project root, alongside `package.json`.

## Minimum shape

```yaml
dashboard:
  name: "my-dashboard"           # kebab-case, 3-50 characters
  namespace: "mydash"            # short, lowercase
  version: "1.0.0"               # valid semver
  description: "Dashboard for managing widgets"   # 10-200 characters
  visibility: "organization"     # public | unlisted | organization | private — always set this
                                  # explicitly (the docs default is "organization", but the CLI's
                                  # own scaffold writes "private" — don't rely on either default)

pack_dependencies: []            # Intelligence Packs this dashboard consumes

build:
  framework: "react"             # default: react
  node_version: ">=20.0.0"
  build_command: "npm run build"
  output_directory: "dist"
  entry_point: "main.js"         # Vite library-mode output: dist/main.js
```

## `dashboard` section

| Field | Required | Default | Notes |
|---|---|---|---|
| `name` | Yes | — | Unique identifier, kebab-case |
| `namespace` | Yes | — | Short namespace, lowercase |
| `version` | Yes | — | Semantic version (`MAJOR.MINOR.PATCH`) |
| `description` | Yes | — | 10-200 characters, meaningful (not just the name repeated) |
| `visibility` | No | `organization` (docs) / `private` (CLI scaffold) | `public` \| `unlisted` \| `organization` \| `private` — **always set it explicitly**; the documented default and the CLI's own scaffolded default disagree |
| `author` | No | — | Author or company name |
| `license` | No | `proprietary` | License identifier |
| `min_sdk_version` | No | `1.0.0` | Must be valid semver — declares the minimum `@huitzo/dashboard-sdk-react` version this dashboard needs |

Visibility levels: `public` (searchable, no grant needed) · `unlisted` (not
searchable, needs the link/ID) · `organization` (org members, needs a
`DashboardAccessGrant`) · `private` (owner organization only).

## `pack_dependencies` section

```yaml
pack_dependencies:
  - scope: "@acme"
    name: "claims-processor"
    version: ">=2.0.0 <3.0.0"
    required: true
  - scope: "@huitzo"
    name: "analytics"
    version: "*"
    required: false
```

| Field | Required | Default | Notes |
|---|---|---|---|
| `scope` | Yes | — | Pack scope, e.g. `@acme` |
| `name` | Yes | — | Pack name, kebab-case |
| `version` | Yes | — | Semver range, or `*` for any |
| `required` | No | `true` | `false` = dashboard installs without it; features degrade gracefully |

For an optional dependency, guard the feature at runtime rather than assuming
the pack is present:

```typescript
const { isPackInstalled } = useHuitzo();
if (isPackInstalled('@huitzo/analytics')) {
  // render the analytics-dependent feature
}
```

## `build` section

| Field | Required | Default | Notes |
|---|---|---|---|
| `framework` | No | `react` | `react` \| `vue` \| `svelte` \| `angular` \| `vanilla` — only `react` and `vanilla` are currently supported |
| `node_version` | No | `>=18.0.0` | Required Node.js version |
| `build_command` | No | `npm run build` | Command that produces the output directory |
| `output_directory` | No | `dist` | Build output directory |
| `entry_point` | No | `main.js` | ESM entry point — the Vite library-mode output filename, must match `vite.config.ts`'s `build.lib.fileName` |
| `env_prefix` | No | `VITE_` | Environment variable prefix exposed to the build |

The scaffolded manifest ships the minimum required set (`dashboard` +
`pack_dependencies: []` + `build`); `pricing`, `deployment`, `metadata`, and
`listing` sections are optional additions for marketplace publishing — see
the manifest reference doc, not this rule, for those.

## Validation

Run before every commit:

```bash
huitzo dashboard validate
```

This checks the manifest fields above, then (when `dist/` exists) verifies
the bundle: entry point present, valid ESM, exports `mount` and `unmount`,
and under the platform's size limit.

`pricing`, `deployment`, `metadata`, and `listing` are additional optional
sections for marketplace publishing — out of scope for this checklist.
