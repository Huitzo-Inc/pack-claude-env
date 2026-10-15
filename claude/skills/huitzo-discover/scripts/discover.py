#!/usr/bin/env python3
# Copyright (c) 2026 Huitzo Inc. All rights reserved.
# SPDX-License-Identifier: LicenseRef-Huitzo-Source-Available

"""
Module: huitzo-discover scanner
Description: Local, stdlib-only miner of Claude Code session history for the
    /huitzo-discover skill. Finds work the user keeps re-running as agent
    conversations (recurring job templates, recurring skills) and measures what
    each costs today, so the skill can judge which ones should become an
    Intelligence Pack (and Dashboard). Nothing leaves the machine: the scanner
    reads local files and writes redacted JSON next to them.

    Subcommands:
      scan  read ~/.claude/projects (+ /insights facets when present) and write
            candidates.json + summary.md
      roi   combine candidates.json with the model's per-candidate estimates
            (estimates.json) into roi.json + roi.md. Arithmetic lives here, not
            in the model.

    Transcript format note: Claude Code documents its JSONL transcripts as an
    internal format that can change between releases. Every field access below
    is defensive; records the parser does not understand are counted and skipped,
    never fatal.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any

# --- Pricing -------------------------------------------------------------------
# USD per million tokens: (input, 5m cache write, 1h cache write, cache hit, output).
# Source: https://platform.claude.com/docs/en/about-claude/pricing (verified 2026-10-14).
# Longest matching model-id prefix wins. Override with --pricing FILE (same shape).
PRICING_SOURCE = "https://platform.claude.com/docs/en/about-claude/pricing"
PRICING_VERIFIED = "2026-10-14"
PRICING: dict[str, tuple[float, float, float, float, float]] = {
    "claude-fable-5-1": (10, 12.5, 20, 0.25, 50),
    "claude-mythos-5-1": (10, 12.5, 20, 0.25, 50),
    "claude-fable-5": (10, 12.5, 20, 1, 50),
    "claude-mythos-5": (10, 12.5, 20, 1, 50),
    "claude-opus-5-5": (4, 5, 8, 0.2, 20),
    "claude-opus-5": (5, 6.25, 10, 0.5, 25),
    "claude-opus-4-8": (5, 6.25, 10, 0.5, 25),
    "claude-opus-4-7": (5, 6.25, 10, 0.5, 25),
    "claude-opus-4-6": (5, 6.25, 10, 0.5, 25),
    "claude-opus-4-5": (5, 6.25, 10, 0.5, 25),
    "claude-opus-4-1": (15, 18.75, 30, 1.5, 75),
    "claude-opus-4": (15, 18.75, 30, 1.5, 75),
    "claude-sonnet-5-5": (2, 2.5, 4, 0.1, 10),
    "claude-sonnet-5": (2, 2.5, 4, 0.2, 10),
    "claude-sonnet-4-6": (3, 3.75, 6, 0.3, 15),
    "claude-sonnet-4-5": (3, 3.75, 6, 0.3, 15),
    "claude-sonnet-4": (3, 3.75, 6, 0.3, 15),
    "claude-haiku-5-5": (0.1, 0.125, 0.2, 0.01, 0.5),
    "claude-haiku-4-5": (1, 1.25, 2, 0.1, 5),
}
# Haiku 5.5 bills prompts over 100,000 tokens at a higher tier.
LONG_PROMPT_TIER = {"claude-haiku-5-5": (100_000, (0.5, 0.625, 1, 0.05, 2.5))}

IDLE_CAP_SECONDS = 300  # gaps longer than this do not count as active time
MIN_TEMPLATE_TOKENS = 4  # shorter opening prompts ("continue", "yes") are not jobs
SAMPLE_CHARS = 700
SELF_MARKER = "huitzo-discover"

# --- Redaction -----------------------------------------------------------------
_SECRET_PATTERNS = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S),
    re.compile(r"\b(sk|rk|pk)-[A-Za-z0-9_\-]{16,}"),
    re.compile(r"\b(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"\bxox[abprs]-[A-Za-z0-9\-]{10,}"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}"),
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]{16,}"),
    re.compile(r"(?i)\b([A-Z0-9_]*(SECRET|TOKEN|PASSWORD|PASSWD|API_KEY|APIKEY|PRIVATE_KEY)[A-Z0-9_]*)\s*[:=]\s*\S+"),
    re.compile(r"[a-z][a-z0-9+.\-]*://[^\s:/@]+:[^\s@/]+@"),
]
_EMAIL = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
_LONG_BLOB = re.compile(r"\b[A-Za-z0-9+/_\-]{40,}={0,2}")


def redact(text: str, home: str) -> str:
    """Remove secrets, e-mail addresses, long opaque blobs and the home path."""
    for pat in _SECRET_PATTERNS:
        text = pat.sub("[REDACTED-SECRET]", text)
    text = _EMAIL.sub("[EMAIL]", text)
    text = _LONG_BLOB.sub("[BLOB]", text)
    if home:
        text = text.replace(home, "~")
    return text


# --- Template signatures -------------------------------------------------------
_NORMALIZERS = [
    (re.compile(r"https?://\S+"), " <url> "),
    (re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I), " <id> "),
    (re.compile(r"\b[0-9a-f]{7,}\b", re.I), " <id> "),
    (re.compile(r"(?:~|\.{1,2})?/[\w.\-/]+"), " <path> "),
    (re.compile(r"\d+(?:\.\d+)*"), " <n> "),
]
_WORD = re.compile(r"<\w+>|[a-z][a-z0-9_\-]*")
# Wrapper tags (agent-to-agent envelopes) carry per-task attributes such as a
# summary; they say nothing about the job's shape, so drop them before tokenizing.
_TAG = re.compile(r"</?[a-z][\w\-]*(?:\s[^<>]*)?>", re.I)
# Opening prompts that restart an earlier session rather than start a job.
_NOT_A_JOB = ("this session is being continued from a previous conversation",)


def template_tokens(text: str) -> list[str]:
    t = _TAG.sub(" ", text).lower()
    for pat, rep in _NORMALIZERS:
        t = pat.sub(rep, t)
    return _WORD.findall(t)


def jaccard(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


# --- Helpers -------------------------------------------------------------------
def parse_ts(value: Any) -> dt.datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def price_for(model: str, pricing: dict[str, tuple[float, ...]]) -> tuple[str, tuple[float, ...]] | None:
    best = None
    for prefix in pricing:
        if model.startswith(prefix) and (best is None or len(prefix) > len(best)):
            best = prefix
    return (best, pricing[best]) if best else None


def usage_cost(model: str, usage: dict[str, Any], pricing: dict[str, tuple[float, ...]]) -> float | None:
    hit = price_for(model, pricing)
    if not hit:
        return None
    prefix, rates = hit
    inp = usage.get("input_tokens") or 0
    out = usage.get("output_tokens") or 0
    read = usage.get("cache_read_input_tokens") or 0
    write = usage.get("cache_creation_input_tokens") or 0
    detail = usage.get("cache_creation") if isinstance(usage.get("cache_creation"), dict) else {}
    write_1h = detail.get("ephemeral_1h_input_tokens") or 0
    write_5m = max(write - write_1h, 0)
    tier = LONG_PROMPT_TIER.get(prefix)
    if tier and inp + read + write > tier[0]:
        rates = tier[1]
    r_in, r_w5, r_w1h, r_hit, r_out = rates
    return (inp * r_in + write_5m * r_w5 + write_1h * r_w1h + read * r_hit + out * r_out) / 1e6


def text_of(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        if any(isinstance(b, dict) and b.get("type") == "tool_result" for b in content):
            return ""
        return "\n".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
    return ""


def median(values: list[float]) -> float:
    return float(statistics.median(values)) if values else 0.0


# --- Session parsing -----------------------------------------------------------
class Session:
    __slots__ = ("sid", "path", "subagent", "headless", "cwd", "start", "end", "active_s", "prompts",
                 "first_prompt", "turns", "cost", "out_tokens", "models", "tools", "skills",
                 "commands", "unpriced", "skill_cost")

    def __init__(self, sid: str, path: Path, subagent: bool) -> None:
        self.sid, self.path, self.subagent = sid, path, subagent
        self.headless = False
        self.cwd = ""
        self.start: dt.datetime | None = None
        self.end: dt.datetime | None = None
        self.active_s = 0.0
        self.prompts: list[str] = []
        self.first_prompt = ""
        self.turns = 0
        self.cost = 0.0
        self.out_tokens = 0
        self.models: Counter[str] = Counter()
        self.tools: Counter[str] = Counter()
        self.skills: Counter[str] = Counter()
        self.commands: Counter[str] = Counter()
        self.unpriced: Counter[str] = Counter()
        self.skill_cost: Counter[str] = Counter()


_COMMAND = re.compile(r"<command-name>/?([\w:.\-]+)</command-name>")


def parse_session(path: Path, subagent: bool, pricing: dict[str, tuple[float, ...]], stats: Counter[str]) -> Session:
    s = Session(path.stem, path, subagent)
    seen_requests: set[str] = set()
    last_ts: dt.datetime | None = None
    try:
        handle = path.open(encoding="utf-8", errors="replace")
    except OSError:
        stats["unreadable_files"] += 1
        return s
    with handle:
        for line in handle:
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                stats["bad_lines"] += 1
                continue
            if not isinstance(rec, dict):
                continue
            ts = parse_ts(rec.get("timestamp"))
            if ts:
                s.start = s.start or ts
                if last_ts:
                    s.active_s += min(max((ts - last_ts).total_seconds(), 0), IDLE_CAP_SECONDS)
                last_ts = s.end = ts
            if rec.get("entrypoint") == "sdk-cli":
                s.headless = True
            if not s.cwd and isinstance(rec.get("cwd"), str):
                s.cwd = rec["cwd"]
            msg = rec.get("message") if isinstance(rec.get("message"), dict) else {}
            kind = rec.get("type")
            if kind == "assistant":
                # Claude Code writes one record per content block and repeats the
                # message usage on each, so bill each API response exactly once.
                key = f"{msg.get('id')}:{rec.get('requestId')}"
                for block in msg.get("content") or []:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        name = str(block.get("name", ""))
                        s.tools[name] += 1
                        if name == "Skill" and isinstance(block.get("input"), dict):
                            s.skills[str(block["input"].get("skill"))] += 1
                if key in seen_requests:
                    continue
                seen_requests.add(key)
                model = str(msg.get("model") or "")
                if model.startswith("<"):
                    continue
                s.turns += 1
                s.models[model] += 1
                usage = msg.get("usage") if isinstance(msg.get("usage"), dict) else {}
                s.out_tokens += usage.get("output_tokens") or 0
                cost = usage_cost(model, usage, pricing)
                if cost is None:
                    s.unpriced[model] += 1
                else:
                    s.cost += cost
                    skill = rec.get("attributionSkill")
                    if isinstance(skill, str) and skill:
                        s.skill_cost[skill] += cost
            elif kind == "user" and not rec.get("isMeta"):
                text = text_of(msg.get("content")).strip()
                if not text:
                    continue
                cmd = _COMMAND.search(text)
                if cmd:
                    s.commands["/" + cmd.group(1)] += 1
                    args = re.search(r"<command-args>(.*?)</command-args>", text, re.S)
                    text = f"/{cmd.group(1)} {args.group(1).strip() if args else ''}".strip()
                elif text.startswith(("<local-command", "<task-notification", "<system-reminder")):
                    continue
                s.prompts.append(text)
                if (not s.first_prompt and len(template_tokens(text)) >= MIN_TEMPLATE_TOKENS
                        and not text.lower().startswith(_NOT_A_JOB)):
                    s.first_prompt = text
    return s


def discover_files(projects: Path, include_subagents: bool) -> list[tuple[Path, bool]]:
    files = [(p, False) for p in projects.glob("*/*.jsonl")]
    if include_subagents:
        files += [(p, True) for p in projects.glob("*/*/subagents/*.jsonl")]
    return sorted(files)


def load_facets(usage_dir: Path) -> dict[str, dict[str, Any]]:
    facets: dict[str, dict[str, Any]] = {}
    for f in (usage_dir / "facets").glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict):
            facets[str(data.get("session_id") or f.stem)] = data
    return facets


def retention_days(claude_dir: Path) -> int:
    try:
        settings = json.loads((claude_dir / "settings.json").read_text(encoding="utf-8"))
        return int(settings.get("cleanupPeriodDays", 30))
    except (OSError, json.JSONDecodeError, ValueError, TypeError, AttributeError):
        return 30


# --- Clustering ----------------------------------------------------------------
def cluster_sessions(sessions: list[Session], threshold: float) -> list[list[Session]]:
    """Leader clustering: a session joins the first group whose leader's opening
    60 normalized tokens overlap its own by at least `threshold` (Jaccard)."""
    groups: list[tuple[set[str], list[Session]]] = []
    for s in sorted(sessions, key=lambda x: x.start or dt.datetime.min.replace(tzinfo=dt.timezone.utc)):
        shape = set(template_tokens(s.first_prompt)[:60])
        for g_shape, g_members in groups:
            if jaccard(shape, g_shape) >= threshold:
                g_members.append(s)
                break
        else:
            groups.append((shape, [s]))
    return [m for _, m in groups]


# --- scan ----------------------------------------------------------------------
def cmd_scan(args: argparse.Namespace) -> int:
    claude_dir = Path(args.claude_dir).expanduser()
    projects = claude_dir / "projects"
    if not projects.is_dir():
        print(f"No Claude Code transcripts at {projects}", file=sys.stderr)
        return 2
    pricing = load_pricing(args.pricing)
    home = str(Path.home())
    stats: Counter[str] = Counter()
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=args.days) if args.days else None

    sessions: list[Session] = []
    for path, subagent in discover_files(projects, not args.no_subagents):
        s = parse_session(path, subagent, pricing, stats)
        if not s.start or (cutoff and s.start < cutoff):
            stats["out_of_window"] += 1
            continue
        if any(SELF_MARKER in p for p in s.prompts[:2]):
            stats["self_sessions_skipped"] += 1
            continue
        if any(x in s.cwd for x in args.exclude_path):
            stats["excluded_by_path"] += 1
            continue
        sessions.append(s)
    if not sessions:
        print("No sessions in the selected window.", file=sys.stderr)
        return 2

    facets = load_facets(claude_dir / "usage-data")
    start = min(s.start for s in sessions if s.start)
    end = max(s.end for s in sessions if s.end)
    weeks = max((end - start).total_seconds() / 604800, 1.0)
    total_cost = sum(s.cost for s in sessions)
    unpriced: Counter[str] = Counter()
    for s in sessions:
        unpriced.update(s.unpriced)

    jobs = [s for s in sessions if s.first_prompt]
    # A task re-dispatched several times on one day is a retry, not recurring work.
    clusters = [c for c in cluster_sessions(jobs, args.similarity)
                if len(c) >= args.min_runs and len({s.start.date() for s in c if s.start}) >= args.min_days]
    clusters.sort(key=lambda c: -sum(s.cost for s in c))

    candidates = []
    for i, members in enumerate(clusters[: args.top], 1):
        members.sort(key=lambda s: s.start or start)
        costs = [s.cost for s in members]
        tools: Counter[str] = Counter()
        skills: Counter[str] = Counter()
        models: Counter[str] = Counter()
        projects_seen: Counter[str] = Counter()
        for s in members:
            tools.update(s.tools)
            skills.update(s.skills)
            models.update(s.models)
            projects_seen[redact(s.cwd, home) or "?"] += 1
        human = sum(1 for s in members if not s.subagent and not s.headless)
        picks = [members[0], members[len(members) // 2], members[-1]] if len(members) >= 3 else members
        # The shared prefix is the template; what follows it is the per-run part.
        # Same job with different data (a diff, a document) and a shared preamble
        # in front of different jobs look alike lexically; the varying part tells
        # them apart.
        openings = [redact(s.first_prompt, home) for s in members]
        shared = len(os.path.commonprefix(openings))
        samples = []
        for s in dict.fromkeys(picks):
            opening = redact(s.first_prompt, home)
            sample: dict[str, Any] = {
                "session": s.sid,
                "date": s.start.date().isoformat() if s.start else None,
                "prompt": opening[:SAMPLE_CHARS],
                "varying_part": opening[shared: shared + SAMPLE_CHARS],
                "follow_up_prompts": [redact(p, home)[:200] for p in s.prompts[1:4]],
            }
            facet = facets.get(s.sid)
            if facet:
                sample["insights"] = {k: redact(str(facet[k]), home) for k in
                                      ("underlying_goal", "brief_summary", "outcome") if k in facet}
            samples.append(sample)
        candidates.append({
            "id": f"c{i:02d}",
            "runs": len(members),
            "runs_per_week": round(len(members) / weeks, 2),
            "distinct_days": len({s.start.date() for s in members if s.start}),
            "first_seen": members[0].start.date().isoformat() if members[0].start else None,
            "last_seen": members[-1].start.date().isoformat() if members[-1].start else None,
            "origin": {"interactive": human, "headless": sum(1 for s in members if s.headless and not s.subagent),
                       "subagent": sum(1 for s in members if s.subagent)},
            "cost_usd": {"total": round(sum(costs), 2), "mean": round(sum(costs) / len(costs), 3),
                         "median": round(median(costs), 3)},
            "shared_prefix_chars": shared,
            "median_turns": median([s.turns for s in members]),
            "median_output_tokens": median([s.out_tokens for s in members]),
            "median_active_minutes": round(median([s.active_s / 60 for s in members]), 1),
            "median_human_prompts": median([len(s.prompts) for s in members]),
            "models": dict(models.most_common(3)),
            "top_tools": dict(tools.most_common(6)),
            "skills_used": dict(skills.most_common(5)),
            "projects": dict(projects_seen.most_common(3)),
            "samples": samples,
        })

    skill_runs: Counter[str] = Counter()
    skill_sessions: Counter[str] = Counter()
    skill_cost: Counter[str] = Counter()
    for s in sessions:
        for name, n in list(s.skills.items()) + list(s.commands.items()):
            skill_runs[name] += n
            skill_sessions[name] += 1
        skill_cost.update(s.skill_cost)
    recurring_skills = [
        {"name": name, "invocations": n, "sessions": skill_sessions[name],
         "attributed_cost_usd": round(skill_cost.get(name.lstrip("/"), 0.0), 2)}
        for name, n in skill_runs.most_common(25) if skill_sessions[name] >= args.min_runs
    ]

    clustered = sum(len(c) for c in clusters)
    ret = retention_days(claude_dir)
    notes = []
    if (end - start).days < ret + 2 and ret <= 30:
        notes.append(f"History covers {(end - start).days} days because Claude Code deletes transcripts after "
                     f"cleanupPeriodDays={ret}. Raise it in ~/.claude/settings.json to keep more history.")
    if unpriced:
        notes.append(f"Unpriced models (excluded from cost): {dict(unpriced)}. Pass --pricing to add them.")
    result = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "source": "claude-code",
        "window": {"start": start.isoformat(timespec="seconds"), "end": end.isoformat(timespec="seconds"),
                   "weeks": round(weeks, 2), "cleanup_period_days": ret},
        "pricing": {"basis": "API list price equivalent (subscription plans are not billed per token)",
                    "source": PRICING_SOURCE if not args.pricing else args.pricing,
                    "verified": PRICING_VERIFIED if not args.pricing else None},
        "totals": {"sessions": len(sessions), "job_sessions": len(jobs),
                   "subagent_sessions": sum(1 for s in sessions if s.subagent),
                   "headless_sessions": sum(1 for s in sessions if s.headless and not s.subagent),
                   "recurring_sessions": clustered,
                   "recurring_share": round(clustered / len(jobs), 3) if jobs else 0,
                   "recurring_templates": len(clusters),
                   "cost_usd": round(total_cost, 2),
                   "recurring_cost_usd": round(sum(s.cost for c in clusters for s in c), 2),
                   "insights_facets_joined": sum(1 for s in sessions if s.sid in facets)},
        "parser": dict(stats),
        "candidates": candidates,
        "recurring_skills": recurring_skills,
        "notes": notes,
    }

    out = Path(args.out).expanduser() if args.out else default_out(claude_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "candidates.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    summary = render_summary(result)
    (out / "summary.md").write_text(summary, encoding="utf-8")
    print(summary)
    print(f"\nWrote {out / 'candidates.json'}")
    return 0


def default_out(claude_dir: Path) -> Path:
    return claude_dir / "huitzo-discover" / dt.datetime.now().strftime("%Y%m%d-%H%M%S")


def load_pricing(path: str | None) -> dict[str, tuple[float, ...]]:
    if not path:
        return dict(PRICING)
    data = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    return {str(k): tuple(float(x) for x in v) for k, v in data.items()}


def render_summary(r: dict[str, Any]) -> str:
    t = r["totals"]
    lines = [
        "# huitzo-discover scan",
        "",
        f"Window: {r['window']['start'][:10]} → {r['window']['end'][:10]} ({r['window']['weeks']} weeks)  ",
        f"Sessions: {t['sessions']} ({t['subagent_sessions']} subagent, {t['headless_sessions']} headless)  ",
        f"Recurring: {t['recurring_sessions']} of {t['job_sessions']} job sessions "
        f"({t['recurring_share']:.0%}) across {t['recurring_templates']} templates  ",
        f"Cost (API list-price equivalent): ${t['cost_usd']:,.0f} total, "
        f"${t['recurring_cost_usd']:,.0f} in recurring work",
        "",
        "| id | runs | runs/wk | cost total | cost/run (median) | active min/run | origin i/h/s | opening prompt |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for c in r["candidates"]:
        o = c["origin"]
        opening = c["samples"][0]["prompt"].replace("\n", " ").replace("|", "\\|")[:70]
        lines.append(f"| {c['id']} | {c['runs']} | {c['runs_per_week']} | ${c['cost_usd']['total']:,.2f} | "
                     f"${c['cost_usd']['median']:.2f} | {c['median_active_minutes']} | "
                     f"{o['interactive']}/{o['headless']}/{o['subagent']} | {opening} |")
    if r["recurring_skills"]:
        lines += ["", "Recurring skills and commands: " + ", ".join(
            f"{s['name']} ×{s['invocations']}" for s in r["recurring_skills"][:12])]
    for note in r["notes"]:
        lines += ["", f"> {note}"]
    return "\n".join(lines) + "\n"


# --- roi -----------------------------------------------------------------------
def cmd_roi(args: argparse.Namespace) -> int:
    cands = json.loads(Path(args.candidates).expanduser().read_text(encoding="utf-8"))
    est = json.loads(Path(args.estimates).expanduser().read_text(encoding="utf-8"))
    pricing = load_pricing(args.pricing)
    rate = float(est.get("hourly_rate", args.hourly_rate))
    by_id = {c["id"]: c for c in cands.get("candidates", [])}
    rows = []
    for e in est.get("candidates", []):
        c = by_id.get(e.get("id"))
        if not c:
            print(f"skip unknown candidate {e.get('id')!r}", file=sys.stderr)
            continue
        runs_month = c["runs_per_week"] * 52 / 12
        agent_run = c["cost_usd"]["mean"]
        calls = float(e.get("pack_llm_calls_per_run", 0))
        usage = {"input_tokens": int(e.get("pack_input_tokens_per_call", 0)),
                 "output_tokens": int(e.get("pack_output_tokens_per_call", 0))}
        model = str(e.get("pack_model", "claude-haiku-5-5"))
        per_call = usage_cost(model, usage, pricing)
        if per_call is None:
            print(f"{e['id']}: unpriced pack_model {model!r}", file=sys.stderr)
            return 2
        pack_run = calls * per_call
        minutes = float(e.get("human_minutes_saved_per_run", 0))
        build_h = float(e.get("build_hours", 0))
        token_saving = (agent_run - pack_run) * runs_month
        time_value = minutes / 60 * rate * runs_month
        monthly = token_saving + time_value
        rows.append({
            "id": c["id"], "name": e.get("name", c["id"]), "verdict": e.get("verdict", ""),
            "confidence": e.get("confidence", ""), "runs_per_month": round(runs_month, 1),
            "agent_cost_per_run": round(agent_run, 3), "pack_cost_per_run": round(pack_run, 4),
            "model_cost_saved_per_month": round(token_saving, 2),
            "hours_saved_per_month": round(minutes * runs_month / 60, 1),
            "time_value_per_month": round(time_value, 2),
            "total_value_per_month": round(monthly, 2),
            "build_cost": round(build_h * rate, 2),
            "payback_weeks": round(build_h * rate / (monthly * 12 / 52), 1) if monthly > 0 else None,
        })
    rows.sort(key=lambda r: -r["total_value_per_month"])
    out = Path(args.out).expanduser() if args.out else Path(args.candidates).expanduser().parent
    result = {"hourly_rate": rate, "pricing_source": PRICING_SOURCE if not args.pricing else args.pricing,
              "rows": rows,
              "totals": {k: round(sum(r[k] for r in rows), 2) for k in
                         ("model_cost_saved_per_month", "hours_saved_per_month", "time_value_per_month",
                          "total_value_per_month", "build_cost")}}
    (out / "roi.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    lines = ["| candidate | verdict | runs/mo | agent $/run | pack $/run | model $ saved/mo | hours saved/mo "
             "| value/mo | build cost | payback (wk) | confidence |", "|" + "---|" * 11]
    for r in rows:
        lines.append(f"| {r['name']} | {r['verdict']} | {r['runs_per_month']} | ${r['agent_cost_per_run']:.2f} | "
                     f"${r['pack_cost_per_run']:.4f} | ${r['model_cost_saved_per_month']:,.0f} | "
                     f"{r['hours_saved_per_month']} | ${r['total_value_per_month']:,.0f} | ${r['build_cost']:,.0f} | "
                     f"{r['payback_weeks'] if r['payback_weeks'] is not None else '—'} | {r['confidence']} |")
    tot = result["totals"]
    lines.append(f"\nTotal: ${tot['total_value_per_month']:,.0f}/month "
                 f"(${tot['model_cost_saved_per_month']:,.0f} model cost, {tot['hours_saved_per_month']} hours at "
                 f"${rate:.0f}/h) for ${tot['build_cost']:,.0f} of build effort.")
    table = "\n".join(lines) + "\n"
    (out / "roi.md").write_text(table, encoding="utf-8")
    print(table)
    print(f"Wrote {out / 'roi.json'}")
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Find agent conversations worth turning into Huitzo packs.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sc = sub.add_parser("scan", help="mine local Claude Code history")
    sc.add_argument("--claude-dir", default=os.environ.get("CLAUDE_CONFIG_DIR", "~/.claude"))
    sc.add_argument("--days", type=int, default=0, help="only sessions started in the last N days (0 = all)")
    sc.add_argument("--min-runs", type=int, default=3, help="minimum runs for a recurring template")
    sc.add_argument("--min-days", type=int, default=2, help="minimum distinct days a template must recur on")
    sc.add_argument("--top", type=int, default=15, help="candidates to keep, ranked by total cost")
    sc.add_argument("--similarity", type=float, default=0.55, help="Jaccard threshold to merge templates")
    sc.add_argument("--no-subagents", action="store_true", help="ignore subagent transcripts")
    sc.add_argument("--exclude-path", action="append", default=[], help="skip sessions whose cwd contains this")
    sc.add_argument("--pricing", help="JSON {model-prefix: [in, 5m write, 1h write, hit, out]}")
    sc.add_argument("--out", help="output directory (default ~/.claude/huitzo-discover/<timestamp>)")
    ro = sub.add_parser("roi", help="turn estimates into ROI")
    ro.add_argument("--candidates", required=True)
    ro.add_argument("--estimates", required=True)
    ro.add_argument("--hourly-rate", type=float, default=75.0)
    ro.add_argument("--pricing")
    ro.add_argument("--out")
    args = ap.parse_args(argv)
    return cmd_scan(args) if args.cmd == "scan" else cmd_roi(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
