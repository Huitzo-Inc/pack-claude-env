#!/usr/bin/env python3
# Copyright (c) 2026 Huitzo Inc. All rights reserved.
# SPDX-License-Identifier: LicenseRef-Huitzo-Source-Available

"""
Module: scripts.check_links
Description: Live link check for every external URL this environment ships.
    `validate_env.py` proves docs.huitzo.ai links point at pages in the public
    inventory; this script proves they actually resolve today (HTTP < 400).
    Needs network. Exit 0 when every link resolves, 1 otherwise.

    Usage: check_links.py [--root DIR] [--timeout SECONDS]
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

URL_RE = re.compile(r"https?://[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]+")
TRAILING = ".,;:)]>'\"`*"
SKIP_HOSTS = ("localhost", "127.0.0.1", "example.com", "your-", "huitzo.ai/mcp")
TEXT_SUFFIXES = {".md", ".json", ".tmpl", ".sh", ".py", ".yaml", ".yml"}


def collect(root: Path) -> dict[str, set[str]]:
    found: dict[str, set[str]] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in {".git", "node_modules", "__pycache__"}]
        for fn in filenames:
            p = Path(dirpath) / fn
            if p.suffix not in TEXT_SUFFIXES:
                continue
            text = p.read_text(encoding="utf-8", errors="replace")
            for m in URL_RE.finditer(text):
                url = m.group(0).rstrip(TRAILING)
                if "${" in url or "{" in url or any(s in url for s in SKIP_HOSTS):
                    continue
                url = url.split("#", 1)[0]
                found.setdefault(url, set()).add(str(p.relative_to(root)))
    return found


def probe(url: str, timeout: float) -> tuple[bool, str]:
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "pack-claude-env-linkcheck/1"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status < 400, str(resp.status)
    except urllib.error.HTTPError as exc:
        if exc.code in (403, 405):  # HEAD refused; retry with GET
            try:
                req = urllib.request.Request(url, method="GET", headers={"User-Agent": "pack-claude-env-linkcheck/1"})
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    return resp.status < 400, str(resp.status)
            except urllib.error.HTTPError as exc2:
                return False, str(exc2.code)
            except Exception as exc2:  # noqa: BLE001 - report any transport failure as a broken link
                return False, type(exc2).__name__
        return False, str(exc.code)
    except Exception as exc:  # noqa: BLE001 - report any transport failure as a broken link
        return False, type(exc).__name__


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="HTTP-check every external link in the repo.")
    ap.add_argument("--root", default=".")
    ap.add_argument("--timeout", type=float, default=15.0)
    args = ap.parse_args(argv)
    root = Path(args.root).resolve()
    links = collect(root)
    broken: list[str] = []
    for url in sorted(links):
        ok, status = probe(url, args.timeout)
        print(f"{'ok ' if ok else 'BAD'} {status:>4} {url}")
        if not ok:
            broken.append(f"{url} ({status}) in {', '.join(sorted(links[url]))}")
    if broken:
        print(f"check_links: {len(broken)} broken link(s)")
        for b in broken:
            print("  " + b)
        return 1
    print(f"check_links: {len(links)} link(s) resolve")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
