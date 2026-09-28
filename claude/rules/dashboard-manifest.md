---
paths:
  - "huitzo-dashboard.yaml"
  - "dashboard/huitzo-dashboard.yaml"
  - "dashboards/*/huitzo-dashboard.yaml"
  - "public/huitzo-dashboard.json"
  - "dashboard/public/huitzo-dashboard.json"
  - "dashboards/*/public/huitzo-dashboard.json"
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
| `min_sdk_version` | No | — (not checked when omitted) | Minimum **Hub mount-contract** version (`HuitzoContext`, versioned with core `@huitzo/dashboard-sdk`), **not** the `@huitzo/dashboard-sdk-react` version. See below |

### `min_sdk_version` is the Hub's mount contract

The Hub compares `min_sdk_version` with the mount-context version it provides
and refuses to mount a dashboard that asks for more, showing *"Incompatible
Dashboard: this dashboard requires Huitzo SDK X or later, but this Hub
provides Y"*. That version tracks the `HuitzoContext` contract (the core
`@huitzo/dashboard-sdk` line, e.g. `0.5.0` introduced the `getToken`
accessor), not the React package. Your dashboard bundles its own
`@huitzo/dashboard-sdk-react` inside `main.js`, so the React major is never a
Hub requirement.

```yaml
min_sdk_version: "0.5.0"   # needs the getToken accessor on the mount context
min_sdk_version: "7.0.0"   # ❌ the dashboard-sdk-react version: the Hub refuses to mount
```

Omit it unless you depend on a specific mount-context feature, and never set
it higher than the Hub you publish to provides.

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
`pack_dependencies: []` + `build`); `pricing`, `deployment` and `metadata`
are optional additions for marketplace publishing (see the manifest reference
doc), and `listing` is covered in the next section.

## Catalog listing: the Hub reads the bundled JSON

The Hub's catalog page (`/explore/<scope>/<slug>`) is filled from a
`huitzo-dashboard.json` at the **root of the published bundle**, not from
`huitzo-dashboard.yaml`. The YAML is the copy the CLI validates; if the bundle
only contains `main.js`, the page shows *"Listing details not available for
this dashboard."* however complete the YAML is.

Ship it through Vite's `public/` directory, which is copied into `dist/`:

```
public/huitzo-dashboard.json   → dist/huitzo-dashboard.json
public/assets/logo.png         → dist/assets/logo.png
public/assets/screenshot-*.png → dist/assets/screenshot-*.png
```

```json
{
  "minSdkVersion": "0.5.0",
  "packDependencies": [{ "scope": "@acme", "name": "claims-processor", "version": ">=2.0.0 <3.0.0", "required": true }],
  "listing": {
    "publisher": { "name": "Acme", "organization": "Acme Inc." },
    "short_description": "One sentence, 160 characters or fewer.",
    "links": { "website": "https://example.com" },
    "brand": { "logo": "assets/logo.png", "accent": "primary" },
    "screenshots": ["assets/screenshot-main.png"]
  }
}
```

- Keep `listing` identical in both files (a test that parses both and compares
  them is cheap insurance). `publisher.name` is what the card shows as
  "Made by …".
- An **invalid** `listing` block is dropped at publish time without failing
  the publish, so validate it before publishing: `https://` URLs only,
  bundle-relative asset paths, no `<` or `>` in text, `short_description` ≤ 160
  and `long_description` ≤ 5000 characters, `accent` one of `primary`,
  `secondary`, `success`, `warning`, `danger`, `info`, `neutral`.
- An **unsafe asset** fails the publish: PNG, JPG, WebP or SVG only, 2 MB per
  file and 8 MB total. SVGs may only use plain shapes and text (no `<style>`,
  `<script>`, `<image>`, filters, links or animation), so a PNG is the simpler
  logo. Crop screenshots to the dashboard content; don't publish the Hub's
  header with a user's name.
- After `huitzo dashboard publish`, check that "Bundle contents" lists
  `huitzo-dashboard.json` and every asset, not just `main.js`.

## Validation

Run before every commit:

```bash
huitzo dashboard validate
```

This checks the manifest fields above, then (when `dist/` exists) verifies
the bundle: entry point present, valid ESM, exports `mount` and `unmount`,
and under the platform's size limit.

`pricing`, `deployment` and `metadata` are additional optional sections for
marketplace publishing, out of scope for this checklist. `huitzo dashboard
validate` does not check `listing`; see "Catalog listing" above.
