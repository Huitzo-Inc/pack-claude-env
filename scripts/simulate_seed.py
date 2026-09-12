#!/usr/bin/env python3
# Copyright (c) 2026 Huitzo Inc. All rights reserved.
# SPDX-License-Identifier: LicenseRef-Huitzo-Source-Available

"""
Module: scripts.simulate_seed
Description: Simulates how the Huitzo CLI seeds a project from this repository
    (`huitzo pack new` / `huitzo dashboard new` / `huitzo project init`) so a
    change here can be checked against the seeding contract without the CLI:

      * `claude/` is copied to `<project>/.claude/`;
      * for `pack-only` and `dashboard-only`, every path listed under
        `profiles/<profile>.json` -> files.exclude is dropped (prefix match on the
        `claude/...` relative path); `full-stack` copies everything;
      * root `CONSTITUTION.md` is copied next to `.claude/`;
      * the whole clone is rejected if any symlink exists.

    Exit 0 when every profile produces the expected shape, 1 otherwise.
    `--out DIR` keeps the simulated projects on disk for inspection.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

# Files that MUST land in a seeded project for the given profile, and files that
# MUST NOT. Keep in sync with README.md "Profiles".
EXPECTATIONS: dict[str, dict[str, list[str]]] = {
    "full-stack": {
        "present": [
            ".claude/CLAUDE.md",
            ".claude/settings.json",
            ".claude/agents/pack-developer.md",
            ".claude/agents/dashboard-developer.md",
            ".claude/skills/huitzo-sdk/SKILL.md",
            ".claude/skills/huitzo-dashboard-sdk/SKILL.md",
            ".claude/skills/init/SKILL.md",
            ".claude/hooks/session-start.sh",
            ".claude/hooks/docs-mcp.sh",
            "CONSTITUTION.md",
        ],
        "absent": [],
    },
    "pack-only": {
        "present": [
            ".claude/CLAUDE.md",
            ".claude/agents/pack-developer.md",
            ".claude/skills/huitzo-sdk/SKILL.md",
            ".claude/skills/huitzo-manifest/SKILL.md",
            ".claude/skills/huitzo-cli/SKILL.md",
            ".claude/skills/init/SKILL.md",
            ".claude/rules/sdk-patterns.md",
            "CONSTITUTION.md",
        ],
        "absent": [
            ".claude/agents/dashboard-developer.md",
            ".claude/agents/dashboard-reviewer.md",
            ".claude/skills/huitzo-dashboard-sdk/SKILL.md",
            ".claude/skills/scaffold-dashboard/SKILL.md",
            ".claude/rules/react-patterns.md",
            ".claude/rules/hub-contract.md",
        ],
    },
    "dashboard-only": {
        "present": [
            ".claude/CLAUDE.md",
            ".claude/agents/dashboard-developer.md",
            ".claude/skills/huitzo-dashboard-sdk/SKILL.md",
            ".claude/skills/huitzo-cli/SKILL.md",
            ".claude/skills/init/SKILL.md",
            ".claude/rules/react-patterns.md",
            "CONSTITUTION.md",
        ],
        "absent": [
            ".claude/agents/pack-developer.md",
            ".claude/agents/pack-reviewer.md",
            ".claude/skills/huitzo-sdk/SKILL.md",
            ".claude/skills/huitzo-manifest/SKILL.md",
            ".claude/skills/add-command/SKILL.md",
            ".claude/rules/sdk-patterns.md",
            ".claude/rules/pack-manifest.md",
        ],
    },
}


def has_symlink(root: Path) -> Path | None:
    for p in root.rglob("*"):
        if ".git" in p.parts:
            continue
        if p.is_symlink():
            return p
    return None


def apply_profile(repo: Path, project: Path, profile: str) -> None:
    """Mirror of the CLI's `_apply_profile`: copy claude/ minus exclude prefixes."""
    src = repo / "claude"
    dst = project / ".claude"
    profile_file = repo / "profiles" / f"{profile}.json"
    if profile == "full-stack" or not profile_file.exists():
        shutil.copytree(src, dst, dirs_exist_ok=True)
        return
    data = json.loads(profile_file.read_text(encoding="utf-8"))
    excludes = [e.rstrip("/") for e in data.get("files", {}).get("exclude", [])]

    def ignore(directory: str, names: list[str]) -> set[str]:
        rel_dir = Path(directory).relative_to(src)
        ignored: set[str] = set()
        for name in names:
            rel = "claude/" + str((rel_dir / name)).replace(os.sep, "/")
            if rel.startswith("claude/./"):
                rel = "claude/" + rel[len("claude/./"):]
            if any(rel == e or rel.startswith(e + "/") for e in excludes):
                ignored.add(name)
        return ignored

    shutil.copytree(src, dst, dirs_exist_ok=True, ignore=ignore)


def simulate(repo: Path, out: Path) -> list[str]:
    problems: list[str] = []
    link = has_symlink(repo)
    if link:
        problems.append(f"symlink present, the CLI would reject the clone: {link.relative_to(repo)}")
        return problems
    for profile, expect in EXPECTATIONS.items():
        project = out / profile
        project.mkdir(parents=True, exist_ok=True)
        apply_profile(repo, project, profile)
        shutil.copy2(repo / "CONSTITUTION.md", project / "CONSTITUTION.md", follow_symlinks=False)
        for rel in expect["present"]:
            if not (project / rel).exists():
                problems.append(f"{profile}: expected file missing: {rel}")
        for rel in expect["absent"]:
            if (project / rel).exists():
                problems.append(f"{profile}: file should be excluded: {rel}")
        seeded = sorted(str(p.relative_to(project)) for p in project.rglob("*") if p.is_file())
        print(f"{profile}: {len(seeded)} files seeded")
    return problems


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Simulate CLI seeding for every profile.")
    ap.add_argument("--root", default=".", help="pack-claude-env checkout (default: cwd)")
    ap.add_argument("--out", default=None, help="keep simulated projects under this directory")
    args = ap.parse_args(argv)
    repo = Path(args.root).resolve()
    if not (repo / "claude").is_dir():
        print("error: --root must point at a pack-claude-env checkout", file=sys.stderr)
        return 2
    if args.out:
        out = Path(args.out).resolve()
        out.mkdir(parents=True, exist_ok=True)
        problems = simulate(repo, out)
    else:
        with tempfile.TemporaryDirectory(prefix="pack-claude-env-seed-") as tmp:
            problems = simulate(repo, Path(tmp))
    if problems:
        print(f"simulate_seed: {len(problems)} problem(s)")
        for p in problems:
            print("  " + p)
        return 1
    print("simulate_seed: all profiles match expectations")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
