#!/usr/bin/env bash
# Copyright (c) 2026 Huitzo Inc. All rights reserved.
# SPDX-License-Identifier: LicenseRef-Huitzo-Source-Available
#
# NOT a hook — this is the launcher `.mcp.json` points `pack-docs` at. It
# resolves the project's docs/ root, picks a `your-docs-mcp` binary to run,
# and execs it. Supports `--print-config` (prints the resolution, exits 0,
# used by tests/humans to sanity-check setup without starting a server).
#
# DOCS_ROOT resolution: `$DOCS_ROOT` is used as-is when set and it does not
# contain the literal "${" (i.e. it was actually expanded by whoever set it
# — `.mcp.json` env values are NOT expanded by Claude Code, so a raw
# "${CLAUDE_PROJECT_DIR}/docs" is treated as unset and we fall back to
# resolving from CWD, which is always the project root when this runs as an
# MCP server command). Otherwise: "$PWD/docs".
#
# Launcher order: venv/bin, .venv/bin, pack/venv/bin (all relative to CWD),
# then PATH, then — only with HUITZO_DOCS_MCP_UVX=1 — `uvx --from
# your-docs-mcp==1.1.2 --with "mcp<2" your-docs-mcp` (that pin matters:
# your-docs-mcp 1.1.2 does not work with mcp>=2).
#
# No network beyond the exec'd server itself. Bash 3.2 compatible.

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=./_lib.sh
. "$SCRIPT_DIR/_lib.sh"

hz_in_project || exit 0

PRINT_CONFIG=0
for arg in "$@"; do
  if [ "$arg" = "--print-config" ]; then
    PRINT_CONFIG=1
  fi
done

# --- resolve DOCS_ROOT -------------------------------------------------------
RAW_DOCS_ROOT="${DOCS_ROOT:-}"
UNEXPANDED=0
case "$RAW_DOCS_ROOT" in
  *'${'*) UNEXPANDED=1 ;;
esac

if [ -n "$RAW_DOCS_ROOT" ] && [ "$UNEXPANDED" -eq 0 ]; then
  case "$RAW_DOCS_ROOT" in
    /*) RESOLVED_DOCS_ROOT="$RAW_DOCS_ROOT" ;;
    *) RESOLVED_DOCS_ROOT="$PWD/$RAW_DOCS_ROOT" ;;
  esac
else
  RESOLVED_DOCS_ROOT="$PWD/docs"
fi

# --- pick a launcher ---------------------------------------------------------
LAUNCHER=""
LAUNCHER_DESC=""
for cand in "$PWD/venv/bin/your-docs-mcp" "$PWD/.venv/bin/your-docs-mcp" "$PWD/pack/venv/bin/your-docs-mcp"; do
  if [ -x "$cand" ]; then
    LAUNCHER="$cand"
    LAUNCHER_DESC="$cand"
    break
  fi
done
if [ -z "$LAUNCHER" ] && command -v your-docs-mcp >/dev/null 2>&1; then
  LAUNCHER="your-docs-mcp"
  LAUNCHER_DESC="your-docs-mcp (PATH)"
fi
USE_UVX=0
if [ -z "$LAUNCHER" ] && [ "${HUITZO_DOCS_MCP_UVX:-}" = "1" ]; then
  USE_UVX=1
  LAUNCHER_DESC='uvx --from "your-docs-mcp==1.1.2" --with "mcp<2" your-docs-mcp'
fi
if [ -z "$LAUNCHER_DESC" ]; then
  LAUNCHER_DESC='none found — pip install "your-docs-mcp==1.1.2" "mcp<2" into the project venv, or set HUITZO_DOCS_MCP_UVX=1'
fi

if [ "$PRINT_CONFIG" -eq 1 ]; then
  printf 'docs root: %s\n' "$RESOLVED_DOCS_ROOT"
  printf 'launcher: %s\n' "$LAUNCHER_DESC"
  exit 0
fi

if [ ! -d "$RESOLVED_DOCS_ROOT" ]; then
  printf 'docs-mcp: docs/ not found at %s; create it or set DOCS_ROOT\n' "$RESOLVED_DOCS_ROOT" >&2
  exit 1
fi

if [ -z "$LAUNCHER" ] && [ "$USE_UVX" -ne 1 ]; then
  printf 'docs-mcp: no your-docs-mcp launcher found.\n' >&2
  printf '  Install it in the project venv: pip install "your-docs-mcp==1.1.2" "mcp<2"\n' >&2
  printf '  Or set HUITZO_DOCS_MCP_UVX=1 to run it via uvx instead.\n' >&2
  exit 1
fi

export DOCS_ROOT="$RESOLVED_DOCS_ROOT"
export MCP_DOCS_CACHE_TTL="${MCP_DOCS_CACHE_TTL:-300}"
export LOG_LEVEL="${LOG_LEVEL:-WARNING}"

if [ "$USE_UVX" -eq 1 ]; then
  exec uvx --from "your-docs-mcp==1.1.2" --with "mcp<2" your-docs-mcp
fi
exec "$LAUNCHER"
