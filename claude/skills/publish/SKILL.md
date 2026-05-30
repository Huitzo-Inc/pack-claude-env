---
name: publish
description: Ship a pack or dashboard to Huitzo (pack publish / dashboard publish + grant)
argument-hint: "[pack|dashboard]"
disable-model-invocation: true
---

# /publish

Ship this project to Huitzo — the final **ship** rung of the loop: scaffold →
develop → test → sandbox → **publish**. Use this skill for a pack
(`huitzo pack publish`) or a dashboard (`huitzo dashboard publish`).

Detect the target from the manifest in the current directory:

- `huitzo.yaml` present → **pack**
- `huitzo-dashboard.yaml` present → **dashboard**

## Visibility & namespace come from the manifest, never a flag

Neither `pack publish` nor `dashboard publish` accepts `--visibility` or
`--namespace`. They read those fields from the manifest. To publish privately,
set the field in the manifest before publishing:

- Pack: `pack.namespace`, `pack.visibility` (`private` by default), `pack.version`.
- Dashboard: `dashboard.namespace`, `dashboard.visibility` (`private` by default), `dashboard.version`.

Your namespace/scope must match your personal namespace or an organization you
belong to, or the backend rejects the upload.

---

## Publish a pack — `huitzo pack publish`

```bash
huitzo pack publish
```

What it does (from the real CLI):

1. Loads `huitzo.yaml` and authenticates.
2. Runs a **capability cross-check** against the backend for any `extensions:`
   your pack requires. Break-glass override: `--skip-capability-check`
   (the only flag `pack publish` accepts; it is logged).
3. Finds a wheel in `dist/`; if none, it builds one (`uv build --wheel`).
4. `POST /api/v1/packs` to register the pack (a `409` "already registered" is
   fine — it resolves the existing pack and adds a new version).
5. Uploads the wheel as `version`.

On success the JSON `data` is the backend's response, including the registered
`commands`. Bump `pack.version` for each release — re-publishing the same
version is rejected by the backend.

Pre-flight in order:

```bash
huitzo pack validate --strict     # or /validate-pack
huitzo pack test                  # or /test-pack
huitzo pack publish
```

> `pack build` does **not** run validation — always validate first.
> `pyproject.toml` is auto-generated from `huitzo.yaml`; never hand-edit it
> (run `huitzo pack sync` if publish complains about a stale `pyproject.toml`).

---

## Publish a dashboard — `huitzo dashboard publish`

```bash
huitzo dashboard build                # produces dist/main.js
huitzo dashboard publish --dry-run    # smoke test — bundles, prints contents, uploads nothing
huitzo dashboard publish
```

`publish` is the only flag-bearing dashboard publish command — it takes a single
flag, `--dry-run` (simulate without uploading). What it does:

1. Loads + validates `huitzo-dashboard.yaml`.
2. Requires the build output (`dist/` with the manifest's `entry_point`, default
   `main.js`). **Run `huitzo dashboard build` first** or publish fails.
3. Tarballs `dist/` (skipping symlinks for safety).
4. `--dry-run` stops here and reports `{name, version, dry_run: true, size_kb}`.
5. Otherwise: `POST /api/v1/dashboards` to register (a `409` is fine), then
   uploads the tarball as a new `version`.

Success envelope:

```json
{"ok": true, "data": {"name": "my-dashboard", "version": "0.1.0", "url": "https://hub.huitzo.com/d/my-dashboard"}}
```

Pre-flight: `/validate-dashboard` (or `huitzo dashboard validate`) →
`/test-dashboard` → `/dashboard-e2e` → build → publish.

### Grant org-visibility access — `huitzo dashboard grant`

For a dashboard with `visibility: organization`, grant a specific tenant access:

```bash
huitzo dashboard grant <dashboard-slug> <tenant-uuid>
```

Both arguments are positional (no flags). The dashboard name must be kebab-case
and the tenant must be a **UUID** — organization-slug → UUID resolution is **not
yet available** (the backend `GET /api/v1/organizations?slug=` endpoint does not
exist yet), so you must pass the raw tenant UUID. Success returns
`{dashboard, tenant_id, granted}`.

### Not yet implemented (stubbed in the CLI)

Be honest about these — they exist as commands but the backend endpoints are
missing, so they print a warning and **exit 1**:

- `huitzo dashboard revoke <dashboard> <tenant-uuid>` — *"Backend revoke endpoint not yet implemented."*
- `huitzo dashboard share <dashboard> [--expires 1d|7d|30d|never]` — *"Backend share endpoint not yet implemented."*

Do not build workflows that depend on `revoke`/`share` until the backend ships them.

---

## Steps

1. **Detect target** from the manifest in the cwd (pack vs dashboard).
2. **Set visibility/namespace** in the manifest (not via a flag) if the defaults
   aren't what you want.
3. **Validate + test** (`/validate-*`, `/test-*`; dashboards also `/dashboard-e2e`).
4. **Build** — dashboards MUST `huitzo dashboard build` first; packs build
   automatically if `dist/` is empty.
5. **Dry-run** (dashboards) — `huitzo dashboard publish --dry-run`.
6. **Publish** — `huitzo pack publish` or `huitzo dashboard publish`.
7. **Grant** (org dashboards only) — `huitzo dashboard grant <slug> <tenant-uuid>`.

## JSON / agent mode

Add the **global** `--output json` flag BEFORE the subcommand
(`huitzo --output json pack publish`). Note that `publish` commands print
human-format progress lines on stdout/stderr even in JSON mode — parse the final
`{...}` envelope line, not the whole stream, and check the exit code. See
`/cli-non-interactive` for the envelope, exit codes, and full publish recipes.
