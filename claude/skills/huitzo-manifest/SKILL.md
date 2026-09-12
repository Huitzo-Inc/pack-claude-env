---
name: huitzo-manifest
description: huitzo.yaml manifest schema v2: sections, permissions, policy, validation. Use editing huitzo.yaml or debugging validate/sync errors. Not ctx API (huitzo-sdk) or dashboards (huitzo-dashboard-sdk).
---

> Verified against huitzo-sdk 1.7.0 (2026-09).

# Huitzo Pack Manifest (`huitzo.yaml`, schema v2)

`huitzo.yaml` is the single source of truth for a pack. Every model is
Pydantic with `extra="forbid"`: **an unknown key anywhere fails the entire
manifest load**, not just that section. `schema_version: 2` (the literal
integer `2`) is required and is checked *before* any field validation — a
missing or wrong value fails with its own error, not a field-level one.

Loader limits: manifest file must be ≤ 1 MB, valid UTF-8, and plain YAML —
**YAML aliases/anchors are rejected outright** (anti-DoS), so no `&anchor` /
`*alias` reuse.

## Top-level sections

| Key | Type | Required | Default |
|---|---|---|---|
| `schema_version` | `2` (literal) | ✅ | — |
| `pack` | object | ✅ | — |
| `policy` | object | ✅ | — |
| `permissions` | list of tokens | optional | `[]` |
| `commands` | list, min 1 | ✅ | — |
| `services` | object | optional | — |
| `data_types` | list | optional | `[]` |
| `mcp_servers` | list | optional | `[]` |
| `extensions` | list | optional | `[]` |
| `ssh_targets` | object | optional | — |
| `secrets` | object | optional | — |
| `pipelines` | object, keyed by pipeline name | optional | — |
| `deployment` | object | optional | — |
| `resources` | object | optional | — |
| `embedded_models` | list | optional | `[]` (reserved for future edge-model support; not yet active) |
| `metadata` | object | optional | — |
| `listing` | object | optional | — |

## `pack:` section

| Field | Type | Required | Default |
|---|---|---|---|
| `name` | string (kebab-case) | ✅ | — |
| `namespace` | string (lowercase) | ✅ | — |
| `version` | string (semver) | ✅ | — |
| `description` | string, ≤200 chars | ✅ | — |
| `visibility` | `public`\|`unlisted`\|`organization`\|`private` | optional | `organization` |
| `author` | string | optional | — |
| `author_email` | string | optional | — |
| `license` | string | optional | `proprietary` |
| `min_sdk_version` | string | optional | — |
| `min_platform_version` | string | optional | — |
| `dependencies` | list[string] | optional | `[]` |
| `dev_dependencies` | list[string] | optional | `[]` |
| `pricing` | object | optional | — (see below) |

`pack.pricing` (marketplace/cloud only — `model`: `one-time`\|`subscription`\|`usage`,
`price`, `currency`, plus model-specific fields like `billing_period`/`trial_days`
or `per_execution`/`monthly_minimum`). See the pricing reference at the "Read
more" link below for the full field set — it is presentation/billing metadata,
not enforced by manifest cross-validation.

## `policy:` — the REQUIRED policy card

Every pack MUST declare a governance card. There is no default; omitting
`policy:` fails to load.

| Field | Type | Required | Default |
|---|---|---|---|
| `autonomy` | `read_only`\|`suggest`\|`act_with_approval`\|`autonomous` | ✅ | — |
| `allowed_actions` | list of permission tokens | ✅ | — |
| `data_scope.scope` | `user`\|`tenant` | ✅ | — |
| `data_scope.external_domains` | list[string] | optional | `[]` |
| `escalation.requires_human_approval` | list[string] | optional | `[]` |
| `audit.level` | `standard`\|`detailed` | optional | `standard` |

**Cross-validation rules (manifest load fails if violated):**

1. `permissions` (top level) must be a **subset** of `policy.allowed_actions` —
   `allowed_actions` is the superset governance statement.
2. `policy.data_scope.external_domains` must be a subset of
   `services.http.allowed_domains`. If `external_domains` is non-empty but
   `services.http` isn't declared at all, that's also an error.
3. Every name in `policy.escalation.requires_human_approval` must match a real
   `commands[].name` in this same manifest.
4. No duplicate command names, MCP server names, data-type names, or
   permission tokens (checked across `permissions` and `policy.allowed_actions`
   together).

## `permissions:` — the 14 tokens + one parameterized grant

The vocabulary is **closed** — any other string is rejected. Each token
(except a few "always available" ones) requires its backing `services:`
declaration; granting it without the declaration fails to load.

| Token | Requires declared | Risk |
|---|---|---|
| `storage:read` | — | low |
| `storage:write` | — | low |
| `files:read` | `services.files` | low |
| `files:write` | `services.files` | low |
| `files:delete` | `services.files` | medium |
| `llm:complete` | `services.llm` | medium |
| `llm:stream` | `services.llm` | medium |
| `http:request` | `services.http` | medium |
| `email:send` | `services.email` | medium |
| `telegram:send` | `services.telegram` | medium |
| `mcp:call` | ≥1 entry in `mcp_servers` | high |
| `ssh:execute` | `services.ssh` **and** non-empty `ssh_targets.allowed` | high |
| `exec:local` | — | high |
| `tts:synthesize` | `services.tts` | medium |

**Parameterized grant:** `commands:execute:<@scope/pack>` (e.g.
`commands:execute:@acme/claims`) authorizes a cross-pack pipeline stage to run
another pack's commands. Its target must match the `@scope/pack` grammar (see
Identifiers below); its backing declaration lives in the *target* pack, not
this manifest — only the format is checked here.

## `commands:` — one entry per command

| Field | Type | Required | Default |
|---|---|---|---|
| `name` | string (kebab-case) | ✅ | — |
| `description` | string | ✅ | — |
| `entry_point` | string, `module.path:function` | ✅ | — |
| `timeout` | int (seconds) | optional | `60` |
| `queue` | `fast`\|`medium`\|`long` | optional | `medium` |
| `retries` | int | optional | `3` |
| `output_format` | string | optional | `json` |
| `schedule` | string, 5-field cron, ≤128 chars | optional | — |
| `deprecated` | bool | optional | `false` |
| `deprecation_message` | string | optional | — |
| `resources` | object | optional | — |

**There is no `enabled` field.** `extra="forbid"` means an unrecognized key
anywhere in a command entry fails the whole manifest, not just that command.

`timeout` and `queue` must equal the `@command` decorator's values in code —
the manifest is a checked mirror, not a second place to configure them (see
the `huitzo-sdk` skill for the decorator). `queue` accepts only `fast`,
`medium`, or `long` — **`"auto"` and `"default"` are both rejected.** The CLI's
add-command flag offers a `default` choice for convenience, but writing
`queue: "default"` ❌ (or `auto` ❌) into `huitzo.yaml` fails validation; omit
`queue:` entirely to take the `medium` default, or name one of the three
values explicitly.

`schedule` is a plain 5-field cron string (`minute hour day-of-month month
day-of-week`) using only digits, `*`, `-`, `/`, `,`, and spaces — no month/day
names, no `L`/`W`/`#N`/`?` extensions. It must not fire more often than **once
every 15 minutes**; a denser schedule (e.g. `"* * * * *"` or `"*/5 * * * *"`)
fails at manifest load.

`resources` (command-level):

| Field | Type | Default |
|---|---|---|
| `tier` | `standard`\|`compute`\|`gpu` | `standard` |
| `timeout_seconds` | int | `60` |
| `memory_hint` | string | — |
| `cpu_hint` | string | — |

## `services:` — per-integration declarations

Each sub-block is optional and has its own `required: bool` (default
`false`) plus specifics. `extra="forbid"` applies to `services:` itself and
every sub-block.

| Service | Fields |
|---|---|
| `llm` | `required`, `requirements` (`min_context`, `capabilities`: `structured_output`\|`tool_use`), `profiles` (dict of named requirement overrides) |
| `http` | `required`, `allowed_domains` (list, no empty entries), `timeout` (default `60`), `max_redirects` (default `5`) |
| `db` | `required`, `integrations` (list[string]\|null — null = any tenant DB integration) |
| `files` | `required`, `max_size_mb`, `allowed_types`, `integrations` (list[string]\|null) |
| `email` | `required` |
| `telegram` | `required` |
| `cron` | `required` (pairs with a command's `schedule`) |
| `ssh` | `required` (pairs with top-level `ssh_targets.allowed`) |
| `tts` | `required` |

`services.llm` is **model-agnostic** — there is no `models`, `default_model`,
`max_tokens`, or `temperature` field. A pack declares a capability floor
(`requirements`) or named `profiles`; it never names a model. `services.llm: {}`
(all defaults) is enough to back `llm:complete`/`llm:stream`.

## `mcp_servers:` — MCP servers the pack connects to

Discriminated on `type`.

**`stdio`:** `name`, `type: "stdio"`, `command` (list[string], min 1),
`env` (dict, default `{}`), `working_dir` (optional).

**`http`:** `name`, `type: "http"`, `url`, `headers` (dict, default `{}`),
`timeout` (default `30`), `force_plaintext_headers` (default `false`).

A header whose **key** looks credential-shaped (`authorization`, `api-key`,
`token`, `secret`, `credential`, `password`, `cookie` — case-insensitive) and
whose **value** is a literal (not a `${secrets.NAME}` interpolation) is
**rejected** — reference a declared secret instead. Set
`force_plaintext_headers: true` only if the value is genuinely not sensitive.

Pin the server version explicitly in `command` (e.g. `["npx", "-y",
"@acme/mcp-server@1.4.2"]`) or in `url`/`env` — an unpinned server can change
behavior under the pack without a manifest diff.

## `ssh_targets:`

`allowed`: list[string], default `[]`. Pairs with `services.ssh`; `ssh:execute`
requires both `services.ssh` declared *and* a non-empty `ssh_targets.allowed`.

## `secrets:`

| Field | Type | Default |
|---|---|---|
| `user_required` | list of `{name, description, help_url}` | `[]` |
| `user_optional` | list of `{name, description, help_url}` | `[]` |

Declares what a user must/may configure. Access at runtime is covered by the
`huitzo-sdk` skill (`ctx.secrets.require`/`.get`).

## `pipelines:` — declarative multi-stage flows

Keyed by pipeline name; each value has `description`, `timeout` (default
`300`, 1–3600s), `stages` (1–32 entries), `error_strategy` (`fail_fast`).

A stage is either a command stage — `name`, `command` (a ref, see below),
`config` (dict), `accept_routes`, `buffer_size` (default 100, max 10000),
`checkpoint_after` — or a parallel block — `name`, `parallel: {branches: [2..16
stages], joiner: stage}`, `checkpoint_after`.

`command` refs use one of two shapes:

- `namespace:command` — intra-pack (this pack owns it).
- `@scope/pack:namespace:command` — cross-pack; requires a matching
  `commands:execute:<@scope/pack>` permission naming the same target.

## `resources:` (pack-level) and `deployment:`

`resources`: `min_memory_mb` (default 256), `recommended_memory_mb` (default
512), `requires_gpu` (default `false`).

`deployment`: `cloud_capable`, `self_hosted_capable` (both default `true`),
`edge_capable`, `offline_capable` (both default `false`), `requires_internet`
(default `true`).

## `metadata:` and `listing:`

`metadata` is discovery info (`homepage`, `repository`, `documentation`,
`changelog`, `keywords`, `category`, `icon`, `screenshots`) — free-form.

`listing` is additive marketplace presentation: `publisher` (required —
`name`, optional `organization`/`contact_email`) plus optional `links`,
`legal`, `brand`, `compatibility`, `commercial`, `short_description` (≤160
chars), `long_description` (≤5000 chars), `screenshots`. All URLs must be
`https://`; asset paths must be bundle-relative (no `..`, no absolute paths);
free-text fields reject `<`/`>` (no embedded markup).

## Identifiers grammar

- `SEGMENT` — one kebab-case piece: `[a-z][a-z0-9-]*` (starts with a letter).
- `@scope/pack` — `@SEGMENT/SEGMENT`. Used by `commands:execute:<...>` grants
  and cross-pack pipeline refs.
- A command ref is `namespace:command` or `@scope/pack:namespace:command` —
  exactly the two shapes pipeline `command` fields and execute grants share, so
  a ref one schema accepts is always a ref the other can authorize.

## Complete example

```yaml
schema_version: 2

pack:
  name: notes-pack
  namespace: notes
  version: 0.0.0
  description: "Save and retrieve short notes"
  visibility: private
  author: "Jane Doe"
  author_email: "jane@example.com"
  dependencies: []
  dev_dependencies:
    - "pytest>=9.0"
    - "pytest-asyncio>=1.0"
    - "mypy>=1.19"
    - "ruff==0.15.20"

# Required governance card (see "policy:" above).
policy:
  autonomy: read_only
  allowed_actions: [llm:complete]
  data_scope:
    scope: user

# Pack-level grants — must stay a subset of policy.allowed_actions.
permissions: [llm:complete]

# Backing declaration for llm:complete. services.llm is model-agnostic.
services:
  llm: {}

commands:
  - name: hello
    description: A simple hello world command
    entry_point: "notes_pack.commands.hello:hello_world"
```

## `huitzo pack sync` — pyproject.toml generation

`huitzo pack sync` (and it happens automatically on `huitzo pack build`/`dev`)
regenerates `pyproject.toml` from `huitzo.yaml`. It writes:

- `[project]` — `name`/`version`/`description` from `pack:`, `dependencies`
  (`huitzo-sdk` first, then `pack.dependencies`), `authors`.
- `[project.optional-dependencies] dev = [...]` from `pack.dev_dependencies`.
- `[project.entry-points."huitzo.commands"]` — one line per command,
  `"@namespace/name/command-name" = "entry_point"`.
- `[build-system]` — `hatchling`.
- Fixed tool sections every scaffolded pack gets: `[tool.pytest.ini_options]`
  `asyncio_mode = "auto"`, `testpaths = ["tests"]`; `[tool.mypy] strict = true`;
  `[tool.ruff]` `target-version = "py311"`, `line-length = 100`; and an
  **explicit** `[tool.ruff.lint] select = ["E4", "E7", "E9", "F"]` paired with
  an **exact** `ruff==0.15.20` pin in `dev_dependencies` — both pinned so the
  lint verdict can't shift under a pack just because a newer ruff shipped.

`pyproject.toml` starts with an `AUTO-GENERATED — DO NOT EDIT` header. Never
hand-edit it; edit `huitzo.yaml` and re-run `huitzo pack sync`.

## Anti-patterns

| ❌ Don't | ✅ Do instead |
|---|---|
| `commands: [{name: x, ..., enabled: true}]` ❌ | Omit `enabled` entirely — it doesn't exist; unknown keys fail the whole manifest. |
| `queue: "default"` or `queue: "auto"` ❌ | Use `fast`, `medium`, or `long` — or omit `queue` for the `medium` default. |
| A manifest with `permissions: [llm:complete]` and no `policy:` block ❌ | `policy:` is required on every manifest — add the card (`autonomy`, `allowed_actions`, `data_scope`). |
| `permissions: [ssh:execute]` with no `services.ssh`/`ssh_targets` ❌ | Every permission needs its backing declaration — add `services.ssh` and a non-empty `ssh_targets.allowed`. |
| `services: {llm: {models: ["gpt-4"]}}` ❌ | `services.llm` is model-agnostic — no model names anywhere; use `requirements`/`profiles`. |
| `mcp_servers: [{name: x, type: stdio, command: ["npx", "-y", "@acme/mcp-server"]}]` ❌ | Pin a version: `"@acme/mcp-server@1.4.2"`. |
| `schedule: "*/5 * * * *"` ❌ | Every 15 minutes is the floor — use `"*/15 * * * *"` or wider. |
| Any stray top-level or nested key not in the tables above ❌ | Remove it — every model is `extra="forbid"`; unknown keys fail the load. |

## Read more

- https://docs.huitzo.ai/docs/packs/manifest
- https://docs.huitzo.ai/docs/guides/quickstart/first-pack
