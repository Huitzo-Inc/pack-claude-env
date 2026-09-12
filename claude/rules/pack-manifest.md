---
paths:
  - "huitzo.yaml"
  - "pack/huitzo.yaml"
  - "packs/*/huitzo.yaml"
  - "pyproject.toml"
---

# Pack Manifest Rules

Checklist to run through every time `huitzo.yaml` is touched. Full field
reference: the `huitzo-manifest` skill (load it via the Skill tool if you need
the complete schema — this file is the checklist, not the reference).

## Before editing

- [ ] `schema_version: 2` is present (the literal integer `2`). It is checked
      before any other field.
- [ ] Every model in this file is `extra="forbid"` — an unknown key anywhere
      (a typo, a leftover v1 field, a copy-pasted field from another pack)
      fails the **whole** manifest, not just that section.

## `policy:` — required on every manifest

- [ ] `policy:` exists. There is no default; a pack with `permissions:` but no
      `policy:` fails to load.
- [ ] `policy.allowed_actions` is a **superset** of the top-level
      `permissions:` list. `permissions` is the mechanical grant;
      `allowed_actions` is the governance statement and must name at least
      everything `permissions` names (it may name more).
- [ ] `policy.data_scope.external_domains` (if set) is a subset of
      `services.http.allowed_domains`. If you list an external domain here,
      `services.http` must be declared.
- [ ] Every name in `policy.escalation.requires_human_approval` matches a real
      `commands[].name` in this same file.

## Permission ↔ service backing

Every permission token requires a matching declaration elsewhere in the same
manifest, or the load fails. Check this table whenever you add or remove a
token from `permissions:`:

| Token | Needs |
|---|---|
| `storage:read`, `storage:write`, `exec:local` | nothing extra |
| `files:read`, `files:write`, `files:delete` | `services.files` |
| `llm:complete`, `llm:stream` | `services.llm` |
| `http:request` | `services.http` |
| `email:send` | `services.email` |
| `telegram:send` | `services.telegram` |
| `tts:synthesize` | `services.tts` |
| `mcp:call` | ≥1 entry in `mcp_servers` |
| `ssh:execute` | `services.ssh` **and** non-empty `ssh_targets.allowed` |
| `commands:execute:<@scope/pack>` | nothing here — backing lives in the target pack |

- [ ] Adding a permission token to `permissions:`? Add the same token to
      `policy.allowed_actions` AND add its backing `services.*` declaration
      (or `mcp_servers`/`ssh_targets` entry).
- [ ] Removing a service block? Remove every permission token it backs first,
      from both `permissions:` and `policy.allowed_actions`.

## `commands:` entries

- [ ] No `enabled:` field. It doesn't exist in this schema — remove it if a
      stale example carried it over.
- [ ] `queue` is `fast`, `medium`, or `long` — never `"default"` or `"auto"`.
      Omit `queue:` entirely to take the `medium` default.
- [ ] `entry_point` is `module.path:function` — matches the real importable
      path (underscores, not hyphens, in both the module path and function
      name).
- [ ] `timeout` and `queue` in the manifest match the `@command` decorator's
      values in code — they're a checked mirror, not an independent setting.
- [ ] If `schedule` is set: 5-field cron, digits/`*`/`-`/`/`/`,`/spaces only,
      and no more often than once every 15 minutes. Also declare
      `services.cron`.

## After editing

- [ ] Run `huitzo pack sync` to regenerate `pyproject.toml` from
      `huitzo.yaml`. **Never hand-edit `pyproject.toml`** — it starts with an
      `AUTO-GENERATED — DO NOT EDIT` header and `huitzo pack sync` (also run
      automatically by `huitzo pack build`/`huitzo pack dev`) owns: `[project]`
      metadata/dependencies/authors, `[project.optional-dependencies]`,
      `[project.entry-points."huitzo.commands"]`, `[build-system]`, and the
      `[tool.pytest.ini_options]` / `[tool.mypy]` / `[tool.ruff]` /
      `[tool.ruff.lint]` sections (including the exact `ruff==` pin). If you
      need a `pyproject.toml` section this generation doesn't cover, that's a
      sign it belongs in `huitzo.yaml` instead, or genuinely doesn't belong in
      a generated file — don't patch the generated output directly.
- [ ] Run `huitzo pack validate --strict` and fix everything it reports before
      moving on.
- [ ] If a validation error names a field you didn't touch, re-read the
      cross-validation rules above — a change in one section (removing a
      service, renaming a command) can invalidate a permission or escalation
      entry elsewhere in the same file.
