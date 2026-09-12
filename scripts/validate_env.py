#!/usr/bin/env python3
# Copyright (c) 2026 Huitzo Inc. All rights reserved.
# SPDX-License-Identifier: LicenseRef-Huitzo-Source-Available

"""
Module: scripts.validate_env
Description: Structural, accuracy and information-boundary validator for the
    pack-claude-env repository. Stdlib only. Run from the repo root (or pass
    --root). Exit 0 when clean, 1 when findings remain, 2 on usage error.

    Checks (see README.md "Validation"):
      1. No symlinks anywhere (the Huitzo CLI rejects the whole clone otherwise).
      2. Profiles: every listed path exists; for partial profiles every file under
         claude/ is either included or covered by an exclude prefix.
      3. Plugin manifest: agents list == claude/agents/*.md; hook scripts exist and
         are executable; settings.json carries no `mcpServers` (Claude Code ignores it).
      4. Frontmatter: skills have name == folder + description; agents have
         name + description.
      5. Information boundary: no private-repo links, retired vocabulary, internal
         process terms or monorepo-internal doc paths.
      6. docs.huitzo.ai links only point at pages in the public inventory.
      7. Stale versions and known-wrong API tokens are absent.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

TEXT_SUFFIXES = {".md", ".json", ".sh", ".py", ".yaml", ".yml", ".tmpl", ".txt", ".toml", ".css"}

# --- 6. Public docs inventory (docs.huitzo.ai/docs/<slug>) -------------------
PUBLIC_DOC_SLUGS = {
    "",
    "api/", "api/rest",
    "architecture/", "architecture/security",
    "cli/", "cli/overview", "cli/reference", "cli/dashboards",
    "concepts/", "concepts/why-huitzo", "concepts/building-methodology",
    "concepts/from-model-to-production",
    "dashboards/", "dashboards/overview", "dashboards/sdk", "dashboards/manifest",
    "dashboards/publishing",
    "guides/", "guides/accounts", "guides/billing", "guides/connect-claude-mcp",
    "guides/external-integrations", "guides/mcp-pack-integration",
    "guides/quickstart/", "guides/quickstart/installation", "guides/quickstart/first-pack",
    "guides/self-hosting/", "guides/self-hosting/QUICK_START", "guides/self-hosting/deployment",
    "guides/self-hosting/requirements", "guides/self-hosting/operations",
    "guides/self-hosting/azure-deployment", "guides/self-hosting/azure-monitoring-scaling",
    "guides/self-hosting/observability",
    "packs/", "packs/manifest",
    "reference/", "reference/configuration", "reference/secrets", "reference/rate-limiting",
    "reference/ssh-targets",
    "sdk/", "sdk/overview", "sdk/commands", "sdk/namespaces", "sdk/context", "sdk/integrations",
    "sdk/storage", "sdk/storage-backends", "sdk/error-handling", "sdk/file-storage", "sdk/mcp",
    "sdk/ssh",
    "search", "tags/",
}
DOCS_LINK_RE = re.compile(r"https?://docs\.huitzo\.ai/docs/([A-Za-z0-9_./-]*)")

# --- 5. Information boundary --------------------------------------------------
BOUNDARY_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("private repo link", re.compile(r"github\.com/Huitzo-Inc/(huitzo|sdk|cli|frontend-sdk)(?![\w-])", re.I)),
    ("retired slogan", re.compile(r"operating system for intelligence", re.I)),
    ("internal metaphor", re.compile(r"\b(railroad|the body, not the brain|huitzo is the body)\b", re.I)),
    ("internal process term", re.compile(r"(review-and-submit|implementation_plan|HUITZO_HEADLESS|headless-worker|\./gate\b|gate-spec)", re.I)),
    ("internal host", re.compile(r"staging\.huitzo\.ai", re.I)),
    ("monorepo-internal doc path", re.compile(r"docs/(architecture/(?!security\b)|governance|plans|ideas|roadmaps|release-notes|studio|hub|testing|incidents|reports|runbooks|onprem)/", re.I)),
    ("monorepo-internal guide", re.compile(r"docs/guides/(developer-environment|how-to-release|testing|application-structure)\.md", re.I)),
    ("monorepo-internal dashboard doc", re.compile(r"docs/dashboards/(loading|backlog|deployment|team-management|ai-tooling|v6|template-release)", re.I)),
    ("monorepo-internal cli doc", re.compile(r"docs/cli/agent-integration\.md", re.I)),
]

# --- 7. Stale versions / known-wrong API tokens --------------------------------
STALE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("stale dashboard-sdk-react version", re.compile(r"dashboard-sdk-react[`'\"]?\s*(4\.\d|\^4)")),
    ("stale '4.1.x' claim", re.compile(r"\b4\.1\.x\b")),
    ("ctx.storage.set (should be .save)", re.compile(r"ctx\.storage\.set\(")),
    ("ctx.telegram.send_message (should be .send)", re.compile(r"ctx\.telegram\.send_message\(")),
    ("model= passed to ctx.llm (use profile=)", re.compile(r"ctx\.llm\.(complete|chat|stream)\([^)]*\bmodel=")),
    ("queue default/auto (real values: fast|medium|long)", re.compile(r"queue\s*[:=]\s*[\"']?(default|auto)\b")),
    ("enabled: field in huitzo.yaml (does not exist)", re.compile(r"^\s*enabled:\s*(true|false)\s*$", re.M)),
    ("hz-arch primitive (never shipped)", re.compile(r"hz-arch\b")),
    ("builtin-shadowing error name", re.compile(r"huitzo_sdk\.errors import[^\n]*\b(TimeoutError|PermissionError)\b")),
    ("mcpServers in settings.json", re.compile(r'"mcpServers"')),
]

FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)


def frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}
    out: dict[str, str] = {}
    key: str | None = None
    for line in m.group(1).splitlines():
        km = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if km:
            key = km.group(1)
            out[key] = km.group(2).strip().strip("\"'")
        elif key and line.startswith((" ", "\t")):
            out[key] = (out[key] + " " + line.strip()).strip()
    return out


class Report:
    def __init__(self) -> None:
        self.findings: list[str] = []

    def add(self, check: str, msg: str) -> None:
        self.findings.append(f"[{check}] {msg}")


def iter_text_files(root: Path, skip_dirs: set[str]) -> list[Path]:
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        for fn in filenames:
            p = Path(dirpath) / fn
            if p.suffix in TEXT_SUFFIXES or fn in {"AGENTS.md", "CLAUDE.md"}:
                files.append(p)
    return sorted(files)


def check_symlinks(root: Path, rep: Report) -> None:
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        for name in dirnames + filenames:
            p = Path(dirpath) / name
            if p.is_symlink():
                rep.add("symlink", f"{p.relative_to(root)} is a symlink (the CLI rejects the whole clone)")


def check_profiles(root: Path, rep: Report) -> None:
    claude_dir = root / "claude"
    all_files = sorted(
        str(p.relative_to(root)).replace(os.sep, "/")
        for p in claude_dir.rglob("*")
        if p.is_file()
    )
    for prof in sorted((root / "profiles").glob("*.json")):
        data = json.loads(prof.read_text(encoding="utf-8"))
        files = data.get("files", {})
        include = files.get("include", [])
        exclude = files.get("exclude", [])
        if include == ["*"]:
            continue
        for entry in include + exclude:
            target = root / entry
            if not target.exists():
                rep.add("profiles", f"{prof.name}: listed path does not exist: {entry}")
        excl_prefixes = [e.rstrip("/") for e in exclude]
        for f in all_files:
            covered = f in include or any(f == e or f.startswith(e + "/") for e in excl_prefixes)
            if not covered:
                rep.add("profiles", f"{prof.name}: {f} is neither included nor excluded")
        for entry in include:
            if not entry.startswith("claude/") and entry != "CONSTITUTION.md":
                rep.add("profiles", f"{prof.name}: include entry outside claude/: {entry}")


def check_plugin(root: Path, rep: Report) -> None:
    manifest_path = root / ".claude-plugin" / "plugin.json"
    if not manifest_path.exists():
        rep.add("plugin", "missing .claude-plugin/plugin.json")
        return
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    agents_listed = manifest.get("agents", [])
    if isinstance(agents_listed, str):
        agents_listed = [agents_listed]
    listed = {Path(a).name for a in agents_listed}
    on_disk = {p.name for p in (root / "claude" / "agents").glob("*.md")}
    for missing in sorted(on_disk - listed):
        rep.add("plugin", f"agent not listed in plugin.json: claude/agents/{missing}")
    for extra in sorted(listed - on_disk):
        rep.add("plugin", f"plugin.json lists a non-existent agent: {extra}")
    hooks_rel = manifest.get("hooks")
    if hooks_rel:
        hooks_path = root / hooks_rel
        if not hooks_path.exists():
            rep.add("plugin", f"hooks manifest missing: {hooks_rel}")
        else:
            text = hooks_path.read_text(encoding="utf-8")
            for m in re.finditer(r"\$\{CLAUDE_PLUGIN_ROOT\}/([A-Za-z0-9_./-]+)", text):
                script = root / m.group(1)
                if not script.exists():
                    rep.add("plugin", f"hook script missing: {m.group(1)}")
                elif not os.access(script, os.X_OK):
                    rep.add("plugin", f"hook script not executable: {m.group(1)}")
    mcp_rel = manifest.get("mcpServers")
    if isinstance(mcp_rel, str):
        mcp_path = root / mcp_rel
        if not mcp_path.exists():
            rep.add("plugin", f"mcp config missing: {mcp_rel}")
        else:
            for m in re.finditer(r"\$\{CLAUDE_PLUGIN_ROOT\}/([A-Za-z0-9_./-]+)", mcp_path.read_text(encoding="utf-8")):
                if not (root / m.group(1)).exists():
                    rep.add("plugin", f"mcp launcher missing: {m.group(1)}")
    settings = root / "claude" / "settings.json"
    if settings.exists():
        data = json.loads(settings.read_text(encoding="utf-8"))
        if "mcpServers" in data:
            rep.add("plugin", "claude/settings.json has mcpServers (ignored by Claude Code; use .mcp.json)")
        for group in data.get("hooks", {}).values():
            for entry in group:
                for hook in entry.get("hooks", []):
                    cmd = hook.get("command", "")
                    m = re.search(r"\.claude/hooks/([A-Za-z0-9_.-]+)", cmd)
                    if m and not (root / "claude" / "hooks" / m.group(1)).exists():
                        rep.add("plugin", f"settings.json references missing hook script: {m.group(1)}")
    marketplace = root / ".claude-plugin" / "marketplace.json"
    if marketplace.exists():
        mk = json.loads(marketplace.read_text(encoding="utf-8"))
        for plugin in mk.get("plugins", []):
            if plugin.get("name") == manifest.get("name") and plugin.get("version") != manifest.get("version"):
                rep.add("plugin", "marketplace.json version differs from plugin.json version")


def check_frontmatter(root: Path, rep: Report) -> None:
    for skill in sorted((root / "claude" / "skills").glob("*/SKILL.md")):
        fm = frontmatter(skill)
        rel = skill.relative_to(root)
        if fm.get("name") != skill.parent.name:
            rep.add("frontmatter", f"{rel}: name '{fm.get('name')}' != folder '{skill.parent.name}'")
        desc = fm.get("description", "")
        if not desc:
            rep.add("frontmatter", f"{rel}: missing description")
        elif len(desc) > 1024:
            rep.add("frontmatter", f"{rel}: description longer than 1024 chars")
    for agent in sorted((root / "claude" / "agents").glob("*.md")):
        fm = frontmatter(agent)
        rel = agent.relative_to(root)
        if not fm.get("name"):
            rep.add("frontmatter", f"{rel}: missing name")
        elif fm["name"] != agent.stem:
            rep.add("frontmatter", f"{rel}: name '{fm['name']}' != file stem '{agent.stem}'")
        if not fm.get("description"):
            rep.add("frontmatter", f"{rel}: missing description")


def check_text(root: Path, rep: Report) -> None:
    skip = {".git", "node_modules", "__pycache__", ".venv", "venv"}
    self_path = Path(__file__).resolve()
    vendored = {"scripts/check_legal_headers.py"}
    for path in iter_text_files(root, skip):
        if path.resolve() == self_path:
            continue
        if str(path.relative_to(root)).replace(os.sep, "/") in vendored:
            continue
        rel = str(path.relative_to(root)).replace(os.sep, "/")
        text = path.read_text(encoding="utf-8", errors="replace")
        for label, pat in BOUNDARY_PATTERNS:
            for m in pat.finditer(text):
                line = text.count("\n", 0, m.start()) + 1
                rep.add("boundary", f"{rel}:{line}: {label}: {m.group(0)!r}")
        for m in DOCS_LINK_RE.finditer(text):
            slug = m.group(1).split("#", 1)[0]
            if slug not in PUBLIC_DOC_SLUGS:
                line = text.count("\n", 0, m.start()) + 1
                rep.add("docs-link", f"{rel}:{line}: not a public docs page: {m.group(0)}")
        for label, pat in STALE_PATTERNS:
            if label == "mcpServers in settings.json" and not rel.endswith("settings.json"):
                continue
            if rel == "CHANGELOG.md":
                continue
            for m in pat.finditer(text):
                line = text.count("\n", 0, m.start()) + 1
                context = text[max(0, m.start() - 40): m.start()]
                # Allow explicit "do not write" anti-pattern rows that name the wrong token.
                if re.search(r"(never|not|wrong|don't|do not|stale|removed|❌|✗)", context, re.I):
                    continue
                rep.add("stale", f"{rel}:{line}: {label}: {m.group(0)!r}")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--root", default=".", help="repo root (default: cwd)")
    args = ap.parse_args(argv)
    root = Path(args.root).resolve()
    if not (root / "claude").is_dir() or not (root / "profiles").is_dir():
        print(f"error: {root} does not look like pack-claude-env (need claude/ and profiles/)", file=sys.stderr)
        return 2
    rep = Report()
    check_symlinks(root, rep)
    check_profiles(root, rep)
    check_plugin(root, rep)
    check_frontmatter(root, rep)
    check_text(root, rep)
    if rep.findings:
        print(f"validate_env: {len(rep.findings)} finding(s)")
        for f in rep.findings:
            print("  " + f)
        return 1
    print("validate_env: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
