#!/usr/bin/env bash
# Copyright (c) 2026 Huitzo Inc. All rights reserved.
# SPDX-License-Identifier: LicenseRef-Huitzo-Source-Available
#
# Stop hook. Never blocks — ALWAYS exits 0. Lists modified/added source
# files (tracked changes vs. HEAD, plus untracked files) that are missing a
# traceability header, and reminds which `huitzo ... validate` command
# applies to this project kind. Outside a git repo, or outside a Huitzo
# project, this is a silent no-op.
#
# No network. Bash 3.2 compatible.

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=./_lib.sh
. "$SCRIPT_DIR/_lib.sh"

hz_in_project || exit 0
PROJECT_ROOT="$(hz_project_root)" || exit 0

git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0

CHANGED="$(
  {
    git diff --name-only HEAD 2>/dev/null
    git ls-files --others --exclude-standard 2>/dev/null
  } | sort -u
)"

[ -n "$CHANGED" ] || exit 0

MISSING=""
while IFS= read -r rel; do
  [ -n "$rel" ] || continue
  file="$PROJECT_ROOT/$rel"
  [ -f "$file" ] || continue
  hz_is_traceable_source "$rel" || continue
  marker="$(hz_traceability_marker "$rel")"
  if ! head -25 "$file" | grep -qF "$marker"; then
    MISSING="$MISSING
  - $rel (missing $marker)"
  fi
done <<EOF
$CHANGED
EOF

if [ -n "$MISSING" ]; then
  printf 'pre-stop: modified/added source files missing a traceability header:%s\n' "$MISSING" >&2
fi

KIND="$(hz_detect_kind "$PROJECT_ROOT")"
case "$KIND" in
  pack)
    printf 'pre-stop: before opening a PR, run: huitzo pack validate --strict\n' >&2
    ;;
  dashboard)
    printf 'pre-stop: before opening a PR, run: huitzo dashboard validate\n' >&2
    ;;
  "project (pack+dashboard)" | "application (packs/+dashboards/)")
    printf 'pre-stop: before opening a PR, run: huitzo pack validate --strict / huitzo dashboard validate\n' >&2
    ;;
esac

exit 0
