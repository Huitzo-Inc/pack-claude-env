---
name: huitzo-methodology
description: >
  How to build, test, ship Packs/Dashboards: deterministic-first design,
  sizing, composition, docs-first, testing pyramid, quality gates. Use when
  planning/reviewing. Not signatures -> huitzo-sdk.
argument-hint: "[topic: sizing, composition, testing, gates, review]"
---

> Verified against docs.huitzo.ai (2026-09).

# Huitzo Methodology

This is **how** to design and ship work on Huitzo — command sizing,
composition, docs-first, testing, and release. For exact `@command`/`ctx.*`
signatures, see `huitzo-sdk`; for `huitzo.yaml` fields, see `huitzo-manifest`.

## What an Intelligence Pack is

An Intelligence Pack is a Python package of small, independently-testable
**commands**. The split that makes this work: deterministic Python code owns
every decision that can be computed or looked up; a model is called only
where it adds judgment a lookup can't — drafting prose, summarizing,
classifying ambiguous input. The platform records what ran (inputs,
timing, correlation id) so behavior is auditable after the fact. A pack
that calls a model for something a regex or a database query would answer
just as well is a pack that skipped the easy, reliable part.

## The four pillars

| Pillar | What it is |
|---|---|
| **Components** | Commands (and integrations) — the unit of work; each has a lifecycle the platform manages |
| **Composition** | Ways to connect commands into a workflow — see below |
| **Communication** | An event bus for async, fire-and-forget signals between packs |
| **Configuration** | A cascade — platform default → pack manifest → command → user override |

## Anatomy and size of a command

A command is **30–750 lines**, single responsibility, named `verb-noun`
(`analyze-claim`, `send-digest`, not `claims-processor`). Validated Pydantic
input, structured output, one clear job.

| Size | Lines | Notes |
|---|---|---|
| Simple | 10–30 | Lookup, status update, cache check |
| Standard | 30–80 | LLM analysis, notification, file parse |
| Complex | 80–300 | Multi-step workflow, batch processing |
| Large | 300–750 | Extended orchestration — acceptable only when the logic is tightly coupled; extract a cohesive sub-task if you can |
| Too large | >750 | Split it — you're rebuilding a monolith |

**Decomposing a problem:** don't build "the claims app" — build
`submit-claim`, `analyze-claim`, `check-coverage`, `approve-claim`,
`notify-customer`. Each is independently testable, independently
deployable, fails independently, and is reusable elsewhere.

**When *not* to call a model:** if the answer is a lookup, a threshold
check, a regex, or a rule your domain already has — write that in Python.
Reserve the model call for the step that genuinely needs judgment, and let
Python compute the gate around it (e.g. "flag for human review" logic
should be a deterministic rule, not something asked of the model).

## Composition — connecting commands

| Mechanism | Model | Use when |
|---|---|---|
| Intra-pack call (`ctx.commands.execute(...)`) | Sync, request→response | One command needs another's result, same pack |
| Pipeline (manifest `pipelines:` + execute endpoint) | Declarative, ordered stages | Data flows through a fixed sequence of transformations |
| Cross-pack call | Sync, crosses pack boundary | Calling into another pack's commands (requires the `commands:execute:<@scope/pack>` grant) |

Pipelines are **data, not glue code** — the chain of stages lives in the
manifest, each stage is an independently-testable command, and the platform
runs the chain end-to-end. Not every stage needs a model: a risk-assessment
stage that is pure rules is a legitimate, model-free pipeline stage.

## Governance: the Policy Card

Every pack's manifest carries a required `policy:` section — the
machine-readable contract of what the pack may do, at what **autonomy**
level (`read_only` | `suggest` | `act_with_approval` | `autonomous`), over
what data scope, and what must escalate to a human. `permissions:` (the
pack's actual capability grants) must be a subset of `policy.allowed_actions`
— a pack cannot hold a capability its own policy doesn't name. Request the
least autonomy and the fewest permissions the pack actually needs; users see
both, with a risk tier, before they install. See `huitzo-manifest` for the
full schema.

## Docs-first workflow

Documentation is written **before** code, and each stage has a skill:

1. **Spec** — `/draft-spec <name>` → `docs/spec/*.md` (requirements + architecture)
2. **Document** — `/draft-docs <command-name>` → `docs/commands/*.md`, `docs/components/*.md`
3. **Implement** — `/add-command` or `/scaffold-dashboard` — code implements the doc, not the reverse
4. **Test** — `/test-pack` / `/test-dashboard`
5. **Validate** — `/validate-pack` / `/validate-dashboard`
6. **Lint** — `/lint-and-fix`
7. **Publish** — `huitzo pack publish` / `huitzo dashboard publish`

Every `.py`/`.ts`/`.tsx` file carries a traceability header pointing at the
`docs/` section it implements (see your project's traceability rule) — the
doc lands first, the code cites it. Docs read like a contract: tables and
pseudocode, not copy-paste implementations that will drift from the code.

## Testing pyramid

**Packs** (fast → slow):
1. Pure helper functions — no `Context` needed at all
2. A command called directly with a mocked `Context`
   (`MagicMock(spec=Context)`, `AsyncMock` for async methods)
3. `huitzo pack dev` / sandbox execution — real platform, real queue behavior
4. REST/MCP end-to-end — the actual deployed surface

**Dashboards** (fast → slow):
1. `npm run typecheck` — TypeScript strict mode
2. Unit tests (vitest) for hooks/components in isolation
3. Mount/unmount contract test — the dashboard's actual Hub lifecycle
4. `npm run build` — the real bundle Hub will load

Prefer the fastest layer that would actually catch the bug. A unit test that
mocks `ctx.storage` and asserts business logic is worth ten sandbox runs.

## Quality gates

**Packs:**
```bash
pytest -v
ruff check .
ruff format --check .
mypy --strict src/
huitzo pack validate --strict
```

**Dashboards:**
```bash
npm run typecheck
npm test
npm run build
huitzo dashboard validate
```

All gates pass before publish. No exceptions — a failing gate is a signal to
fix the work, not to relax the gate.

## The development loop

```
new → dev → test → validate → build → publish
```

`huitzo pack new` / `huitzo dashboard new` scaffolds; `huitzo pack dev` runs
against a live sandbox with no local infrastructure; `test`/`validate` are
the gates above; `build` packages; `publish` ships under your `@scope`.
Publishing requires the manifest `version` to increase (semver) — you cannot
republish the same version.

## Dashboards consume, never decide

A dashboard is a thin consumer of a pack's commands — it renders what a
command decided and lets a user trigger the next command. Business logic
(approve/deny, risk scoring, eligibility) belongs in a command, not in a
`useEffect`. If a dashboard is computing a decision instead of displaying
one, that logic belongs in a pack command.

## Definition of done

- [ ] Doc exists in `docs/` before the code that implements it
- [ ] Traceability header present and accurate
- [ ] Command(s) sized 30–750 lines, single responsibility, `verb-noun`
- [ ] `policy:` and `permissions:` request the minimum needed
- [ ] Tests cover the pyramid's fast layers; sandbox/e2e for the risky path
- [ ] All quality gates pass locally
- [ ] Dashboard (if any) renders pack decisions, computes none of its own

## Review checklist

- **Correctness vs docs** — does the code match what `docs/` promises?
- **SDK misuse** — wrong error type, sync call where async is required,
  `model=` where `profile=` belongs (see `huitzo-sdk`)
- **Permissions** — no permission requested beyond what the command uses
- **Security** — secrets never logged, no hardcoded credentials, HTTP calls
  have explicit timeouts
- **Simplicity** — could this command be smaller, or is it two commands
  wearing one name?

## Five developer-constitution principles

From this project's `CONSTITUTION.md`:

1. **Intelligence must be real** — measurable advantage over raw model
   access; no thin wrapper with a logo.
2. **Own what you ship** — tests pass before publishing; traceability on
   every file; honest attribution, no blame.
3. **Simplicity is a discipline** — delete before adding; type hints and
   clean lint are the floor, not a nice-to-have.
4. **Data belongs to the customer** — scoped storage only, declared data
   flows, zero-access by default.
5. **Display what is true** — dashboards represent data faithfully:
   accurate visuals, explicit loading states, actionable errors,
   accessible by default.

## Learning path

[build-with-huitzo](https://github.com/Huitzo-Inc/build-with-huitzo) —
runnable, offline-testable examples, one tier at a time:

| Tier | Teaches |
|---|---|
| 0 — hello-pack | `@command`, Pydantic args, mocked-`Context` testing |
| 1a–1d | Storage, HTTP integration, email triage, CSV aggregation — deterministic logic paired with one model call |
| 2 — grounded-reco | Governance via Policy Card, grounding evals, audit trail |
| 3 — claims-pipeline | Multi-stage composition via manifest pipelines |
| 4 — first-dashboard | React dashboard, `useCommand`, mount/unmount contract |
| 5 — pack-from-outside | Calling a pack via REST, CLI, MCP, and CI — one model, four doors |
| 6 — fullstack-triage | Pack + dashboard together, end-to-end |
| 8 — trade-surveillance | Full governance loop on a regulated-industry example |

## Anti-patterns

| ❌ Don't | ✅ Do instead |
|---|---|
| ❌ Let the model decide everything, including things a rule could answer | Compute what you can in Python; call the model only for judgment |
| ❌ One 1,200-line command doing five jobs | Split into focused `verb-noun` commands and compose them |
| ❌ Skip `docs/` and write code straight from a ticket | Write the doc first — it's the implementation contract |
| ❌ Test that the platform works (auth, RLS, retries) | Test *your* logic with a mocked `Context`; trust the platform's own tests for its own guarantees |
| ❌ Hardcode a model name in a command | Use a configured LLM profile so the deployment controls the model |
| ❌ Compute a business decision in the dashboard | Compute it in a command; the dashboard renders the result |

## Read more

- [concepts/why-huitzo](https://docs.huitzo.ai/docs/concepts/why-huitzo)
- [concepts/building-methodology](https://docs.huitzo.ai/docs/concepts/building-methodology)
- [concepts/from-model-to-production](https://docs.huitzo.ai/docs/concepts/from-model-to-production)
- [packs/manifest](https://docs.huitzo.ai/docs/packs/manifest)
- [guides/quickstart/first-pack](https://docs.huitzo.ai/docs/guides/quickstart/first-pack)
