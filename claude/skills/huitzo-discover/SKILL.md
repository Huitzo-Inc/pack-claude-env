---
name: huitzo-discover
description: Mine your Claude Code history for work worth turning into Packs/Dashboards, with ROI. Use when deciding what to build next. Not for building it (/draft-spec).
argument-hint: "[--days N] [--top N] [--min-days N] [--hourly-rate USD] [--exclude-path TEXT]"
disable-model-invocation: true
---

# /huitzo-discover

Find the work this user keeps re-running as agent conversations and show, candidate by
candidate, whether it should become an Intelligence Pack (plus Dashboard), what that pack
would look like, and what it would save.

A recurring conversation is a pack waiting to happen when the job stays the same and
only the data changes. A pack runs it on demand or on a schedule, mostly
deterministically, with bounded `ctx.llm` calls where judgement is needed, and every run
is recorded. It does not re-explore the problem in a long agent loop each time.

## Privacy contract (tell the user before step 1)

- Everything runs on this machine. The scanner reads `~/.claude/projects/` (session
  transcripts) and, if present, `~/.claude/usage-data/facets/` (the per-session analysis
  `/insights` leaves behind). It writes into `~/.claude/huitzo-discover/<timestamp>/`.
- Secrets, e-mail addresses, long opaque strings and the home path are redacted before
  anything is written. Only short redacted excerpts reach this conversation.
- Never copy the output directory into a repository, and never paste transcript
  excerpts into docs, specs or commits.

## Steps

### 1. Scan

`SCRIPT = ${CLAUDE_SKILL_DIR}/scripts/discover.py`. If the placeholder was not
substituted, use `.claude/skills/huitzo-discover/scripts/discover.py`.

```bash
python3 "$SCRIPT" scan $ARGUMENTS      # stdlib only, Python 3.10+
```

Pass `--hourly-rate` only to step 5. The scan prints `summary.md` and the path of
`candidates.json`. Read `candidates.json` in full; it is redacted and small.

If the scan reports no recurring templates, say so plainly. That is a valid result.
Suggest re-running after more history has accumulated and stop.

### 2. Judge every candidate

For each entry in `candidates`, read `samples[].prompt`, `samples[].varying_part`,
`follow_up_prompts`, `insights`, `top_tools` and `origin`, then assign one verdict:

| Verdict | When |
|---|---|
| `pack` | Same job every run; the varying part is **data** (a diff, a document, an issue list, a URL). Inputs and output shape are stable. The steps can be written down. |
| `pack+dashboard` | A `pack` whose results a person reviews, approves or tracks over time, or that needs a trigger button or a history view. |
| `skill` | Recurring, but needs open-ended exploration or edits inside a repository or workstation. It stays in the agent; codify it as a Claude Code skill instead. |
| `keep-agentic` | The shared text is only a preamble or house rules, and the varying part is a **different task** each time. Not a recurring job. |
| `noise` | Session plumbing (resumes, compaction restarts, setup chatter). |

Be strict. A cluster earns `pack` only if you can name its inputs, its output and its
steps from the samples alone. When in doubt, choose the weaker verdict and say why.

### 3. Sketch the pack for every `pack` / `pack+dashboard`

For each, write:

- **Name** (kebab-case) and a one-line purpose.
- **Commands** as `verb-noun` names, each with its inputs and its typed output.
- **Steps**, each marked *deterministic* (fetch, parse, diff, validate, score by rule,
  render) or *model* (`ctx.llm`, with what it decides and roughly how many tokens go in
  and out). Apply deterministic-first sizing from `/huitzo-methodology`. Every step that
  can be a rule should be a rule.
- **Trigger**: on demand, schedule, or webhook/event.
- **Dashboard** (if any): the views a person needs, such as a queue, run history,
  approve/reject, or a trend.
- **What stops it being a pack**: the open question or risk, for example secrets,
  access to a private system, or judgement that is not yet written down.

### 4. Estimate, conservatively

Write `estimates.json` next to `candidates.json`:

```json
{
  "hourly_rate": 75,
  "candidates": [
    {
      "id": "c03",
      "name": "diff-review",
      "verdict": "pack",
      "confidence": "medium",
      "pack_llm_calls_per_run": 1,
      "pack_input_tokens_per_call": 12000,
      "pack_output_tokens_per_call": 1500,
      "pack_model": "claude-haiku-5-5",
      "human_minutes_saved_per_run": 3,
      "build_hours": 12,
      "reasoning": "one line per number"
    }
  ]
}
```

Include only `pack` and `pack+dashboard` candidates. Rules for the numbers:

- `pack_model` is the cheapest model tier that can do the model steps you sketched,
  as a model id the scanner prices (a Claude id from its pricing table).
- Token counts come from the varying part's size plus your own instructions, not from
  the agent's session totals. Those include exploration a pack does not repeat.
- Base `human_minutes_saved_per_run` on `median_human_prompts` and `origin`. For
  interactive runs, count typing, waiting on and re-checking the agent. For headless
  or subagent runs, count only the minutes a person spends dispatching or reading
  them. That is often 0–2. Do not count agent wall-clock time as human time.
- `build_hours` covers the docs-first spec, commands, tests and dashboard. Never go
  below 4.
- Use the `hourly_rate` from `$ARGUMENTS` if given, otherwise keep 75 and say so.

### 5. Compute ROI (arithmetic lives in the script)

```bash
python3 "$SCRIPT" roi --candidates <dir>/candidates.json --estimates <dir>/estimates.json
```

This writes `roi.json` and `roi.md`. Never adjust its numbers by hand. If one looks
wrong, fix the estimate and re-run.

### 6. Write the report

Write `<dir>/report.md`:

1. **Headline**: one paragraph. The recurring share of the user's sessions, the
   list-price spend in recurring work, the top two packs and their combined monthly
   value. Say that costs are API list-price equivalents, which are not a subscription
   bill.
2. **Ranked table**: the `roi.md` table.
3. **One card per pack candidate**: the sketch from step 3, its evidence (runs,
   runs/week, cost per run, origin) and what blocks it.
4. **Staying in the agent**: the `skill` and `keep-agentic` clusters, one line each
   with the reason.
5. **Recurring skills**: from `recurring_skills`, note any user-authored skill run
   many times. It is already a written-down procedure and often the fastest pack to
   build.
6. **Caveats**: the history window and `notes`. When retention limited the window,
   tell the user to raise `cleanupPeriodDays`. Also state: the costs are estimates,
   templates were clustered lexically, and the human-time figures are your
   estimates.

### 7. Hand off

Show the user the headline, the ranked table and the path to `report.md`. Offer
`/draft-spec <name>` for the top candidate. Do not start building without the user's
go-ahead. In a non-interactive run, stop after writing the report.

## Notes

- Claude Code documents its transcript format as internal and subject to change. The
  scanner skips records it cannot read and reports the counts under `parser`. If
  nearly everything is skipped, say the format changed. Do not guess.
- Costs use the published API price table embedded in the script, with its source
  link and verification date. `--pricing FILE` overrides it, for example for
  non-Claude models, which are otherwise listed as unpriced.
