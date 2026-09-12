#!/usr/bin/env bash
# Copyright (c) 2026 Huitzo Inc. All rights reserved.
# SPDX-License-Identifier: LicenseRef-Huitzo-Source-Available
#
# PostToolUse hook — matcher: Write|Edit|MultiEdit|NotebookEdit.
# Non-blocking: ALWAYS exits 0. Reads the file back from disk (the edit has
# already landed by the time PostToolUse runs) and warns on stderr about:
#   (a) a source file missing its traceability header
#   (b) ctx.llm.* called with model= instead of profile=
#   (c) a hardcoded hex/rgb()/hsl() color in dashboard .tsx/.css
#   (d) dangerouslySetInnerHTML
#   (e) `ruff check` findings, when ruff is on PATH, for a .py file
#
# No network. Bash 3.2 compatible. Missing file or no Huitzo project marker
# → silent exit 0.

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=./_lib.sh
. "$SCRIPT_DIR/_lib.sh"

hz_in_project || exit 0
PROJECT_ROOT="$(hz_project_root)" || exit 0

INPUT="$(cat)"
[ -n "$INPUT" ] || exit 0

FILE_PATH="$(hz_get_file_path "$INPUT")"
[ -n "$FILE_PATH" ] || exit 0
[ -f "$FILE_PATH" ] || exit 0

case "$FILE_PATH" in
  "$PROJECT_ROOT"/*)
    REL="${FILE_PATH#"$PROJECT_ROOT"/}"
    ;;
  *)
    REL="$FILE_PATH"
    ;;
esac

# Never anything useful to say about build/dependency output.
case "$REL" in
  */node_modules/* | */.venv/* | */venv/* | */dist/* | */build/* | */__pycache__/*)
    exit 0
    ;;
esac

# --- (a) traceability header -------------------------------------------------
# src/**/*.py and src/**/*.ts(x), optionally nested under pack/, packs/*/,
# dashboard/, dashboards/*/ (the single-project vs. application layouts).
if hz_is_traceable_source "$REL"; then
  marker="$(hz_traceability_marker "$REL")"
  if ! head -25 "$FILE_PATH" | grep -qF "$marker"; then
    printf 'post-edit: %s is missing a traceability header (%s) in the first 25 lines\n' \
      "$REL" "$marker" >&2
  fi
fi

# --- (b) ctx.llm(...) with model= instead of profile= ------------------------
case "$REL" in
  *.py)
    if grep -q 'ctx\.llm\.' "$FILE_PATH" 2>/dev/null && grep -Eq '\bmodel[[:space:]]*=' "$FILE_PATH" 2>/dev/null; then
      printf 'post-edit: %s calls ctx.llm.* with model= — use profile= instead (there is no model= kwarg)\n' \
        "$REL" >&2
    fi
    ;;
esac

# --- (c) hardcoded color literal in dashboard .tsx/.css ----------------------
case "$REL" in
  *.tsx | *.css)
    base="$(basename "$REL")"
    if [ "$base" != "index.css" ]; then
      if grep -Eq '#[0-9a-fA-F]{3,8}\b|rgb\(|hsl\(' "$FILE_PATH" 2>/dev/null; then
        printf 'post-edit: %s has a hardcoded color literal — use var(--color-*) tokens instead\n' \
          "$REL" >&2
      fi
    fi
    ;;
esac

# --- (d) dangerouslySetInnerHTML ---------------------------------------------
if grep -q 'dangerouslySetInnerHTML' "$FILE_PATH" 2>/dev/null; then
  printf 'post-edit: %s uses dangerouslySetInnerHTML — sanitize input or avoid it (XSS)\n' "$REL" >&2
fi

# --- (e) ruff, best-effort, non-blocking -------------------------------------
case "$REL" in
  *.py)
    if command -v ruff >/dev/null 2>&1; then
      RUFF_OUT="$(ruff check "$FILE_PATH" 2>&1)"
      if [ -n "$RUFF_OUT" ]; then
        printf 'post-edit: ruff check %s (non-blocking):\n%s\n' "$REL" "$RUFF_OUT" >&2
      fi
    fi
    ;;
esac

exit 0
