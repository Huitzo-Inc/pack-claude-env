---
name: publish
description: Ship a pack or dashboard to Huitzo (pack publish / dashboard publish + grant)
argument-hint: "[pack|dashboard]"
disable-model-invocation: true
---

# /publish

> Verified against the Huitzo CLI surface as of 2026-09 (`huitzo <cmd> --help` is authoritative).

Ship this project — the final **ship** rung of the loop: scaffold → develop →
test → sandbox → **publish**.

Detect the target from the manifest in the current directory:

- `huitzo.yaml` present → **pack**
- `huitzo-dashboard.yaml` present → **dashboard**

## Visibility & namespace come from the manifest, never a flag

Neither `pack publish` nor `dashboard publish` accepts `--visibility` or
`--namespace`. They read `pack.namespace` / `pack.visibility` (or the
dashboard equivalents) straight from the manifest, defaulting to `private`.
Your namespace must match your personal namespace or an organization you
belong to — a mismatch fails registration with an actionable message naming
the namespace that would work. To publish under a different visibility or
namespace, edit the manifest first, not the command line.

## Preflight (both targets)

1. **Bump the version.** A version is immutable once registered — re-publishing
   the same `pack.version` / `dashboard.version` is rejected. Version must
   increase.
2. **Test.** `huitzo pack test` (packs only — no `dashboard test` command).
3. **Validate strictly.** `huitzo pack validate --strict` or
   `huitzo dashboard validate`.
4. **Build.** Packs build automatically on publish if `dist/` is empty;
   dashboards MUST run `huitzo dashboard build` first — `publish` fails
   without a build output present.

## Publish a pack

```bash
huitzo pack test
huitzo pack validate --strict
huitzo pack publish
```

| Flag | Meaning |
|---|---|
| `--no-build` | Break-glass: publish the existing `dist/` wheel as-is instead of clean-building from source. Wheel/source parity is then on you. |
| `--skip-capability-check` | Skip the pre-publish extension-capability cross-check against the backend (logged; not recommended). |

By default, publish **clean-builds the wheel from current source** so the
uploaded artifact always matches HEAD. Registering the pack (`POST
/api/v1/packs`) returns `409` if it already exists — that's fine, the CLI
resolves the existing pack and adds this build as a new version. Success data
includes the registered pack and its commands.

`pyproject.toml` is auto-generated from `huitzo.yaml`; never hand-edit it —
run `huitzo pack sync` if publish complains it's stale.

## Publish a dashboard

```bash
huitzo dashboard build                # produces the manifest's build output
huitzo dashboard validate
huitzo dashboard publish --dry-run    # bundles + reports contents, uploads nothing
huitzo dashboard publish
```

`publish` takes one flag, `--dry-run`. Sequence: validate the manifest again,
confirm the build output directory exists (fails with "Run `huitzo dashboard
build` first" if not), tarball it (skipping symlinks), then either stop and
report `{"name","version","dry_run":true,"size_kb"}` (`--dry-run`) or register
(`POST /api/v1/dashboards`, `409` on an existing dashboard is fine) and upload
the tarball as a new version.

### Grant access — `huitzo dashboard grant`

For a dashboard visible to `organization`, grant a specific tenant access:

```bash
huitzo dashboard grant <dashboard-name> <tenant-uuid> [--scope SCOPE]
```

Both `<dashboard-name>` and `<tenant-uuid>` are positional arguments.

### What visibility means

- **private** — only you (the publishing account) can install/run it.
- **organization** — members of tenants you explicitly `grant` can install/run it.
- **unlisted** — installable by direct reference, not shown in listings.
- **public** — anyone can discover and install it.

Set the level in the manifest before publishing; it isn't a publish-time flag.

## Post-publish verification

```bash
huitzo --output json pack list             # confirm the new version registered
huitzo --output json run @scope/pack/cmd --args '{}'   # smoke-test it live
```

For a dashboard, confirm in the Hub UI or with `huitzo dashboard validate`
against the published manifest.

## Rollback

No documented rollback path for a published pack or dashboard version —
publish a new, higher version instead. (`huitzo rollback` manages the
*launcher-installed CLI itself*, not published packs/dashboards — do not
conflate the two.)

## JSON / agent mode

Add the **global** `--output json` flag before the subcommand
(`huitzo --output json pack publish`). Both publish commands print
human-format progress lines even in JSON mode — parse the **last** `{...}`
line and trust the exit code, don't scan the whole stream. See the
`/cli-non-interactive` skill for the envelope shape and exit codes.
