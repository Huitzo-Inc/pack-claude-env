#!/usr/bin/env bash
# Copyright (c) 2026 Huitzo Inc. All rights reserved.
# SPDX-License-Identifier: LicenseRef-Huitzo-Source-Available
#
# PreToolUse hook — matcher: Write|Edit|MultiEdit|NotebookEdit.
# Scans the content a tool call is about to write for high-confidence
# secret patterns. Blocks (exit 2) on a match; the message on stderr is
# shown to Claude. Allows (exit 0) everything else, including when no
# Huitzo project marker is found (a plugin user's other repos), when the
# input is empty, or when the target path is allowlisted.
#
# No network. Bash 3.2 compatible. jq preferred, python3 fallback (see
# _lib.sh) — if neither is present, scanning is skipped and the call is
# allowed rather than blocked on a guess.

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=./_lib.sh
. "$SCRIPT_DIR/_lib.sh"

hz_in_project || exit 0

INPUT="$(cat)"
[ -n "$INPUT" ] || exit 0

FILE_PATH="$(hz_get_file_path "$INPUT")"
CONTENT="$(hz_get_write_content "$INPUT")"
[ -n "$CONTENT" ] || exit 0

# --- allowlist: paths where secret-shaped strings are expected -------------
# Kept deliberately small — every entry here is a place a "real-looking"
# credential is allowed to appear on purpose (a documented placeholder or
# the docs that talk about secrets), never a place secrets actually live.
case "$FILE_PATH" in
  *.env.example | *.env.sample | *secrets-scan.sh | docs/*secret*)
    exit 0
    ;;
esac

# --- pattern list ------------------------------------------------------------
# label|regex, one per line. High-confidence formats only — this is meant to
# catch an accidental paste, not to be a general-purpose secret detector.
MATCH_LABEL=""
hz_scan() {
  label="$1"
  pattern="$2"
  if [ -z "$MATCH_LABEL" ] && printf '%s' "$CONTENT" | grep -Eq -- "$pattern"; then
    MATCH_LABEL="$label"
  fi
}

hz_scan "Huitzo API key (sk-huitzo-...)" 'sk-huitzo-[0-9a-f]{64}'
hz_scan "AWS access key (AKIA...)" 'AKIA[0-9A-Z]{16}'
hz_scan "GitHub token (ghp_/gho_/ghu_/ghs_/ghr_...)" '\b(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}'
hz_scan "Anthropic API key (sk-ant-...)" 'sk-ant-[A-Za-z0-9_-]{20,}'
hz_scan "Slack token (xox[abprs]-...)" 'xox[abprs]-[A-Za-z0-9-]{10,}'
hz_scan "Stripe live key (sk_live_...)" 'sk_live_[0-9A-Za-z]{20,}'
hz_scan "Google API key (AIza...)" 'AIza[0-9A-Za-z_-]{35}'
hz_scan "PEM private key block" '-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----'
hz_scan "JWT (eyJ...eyJ...)" 'eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+'
# OpenAI-shaped key last: broadest pattern, checked only if nothing more
# specific already matched (sk-huitzo-... and sk-ant-... are checked first).
hz_scan "OpenAI-shaped key (sk-...)" '\bsk-[A-Za-z0-9]{32,}'

if [ -n "$MATCH_LABEL" ]; then
  {
    printf 'secrets-scan: blocked write to %s\n' "${FILE_PATH:-<unknown file>}"
    printf '  matched pattern: %s\n' "$MATCH_LABEL"
    printf '  do not write secrets into source. Instead:\n'
    printf '    - Python:  await ctx.secrets.require("SOME_KEY")\n'
    printf '    - shell/CI: read it from an environment variable\n'
    printf '    - docs/tests needing a placeholder: put it in .env.example\n'
  } >&2
  exit 2
fi

exit 0
