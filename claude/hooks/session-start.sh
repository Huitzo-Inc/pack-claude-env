#!/usr/bin/env bash
# Copyright (c) 2026 Huitzo Inc. All rights reserved.
# SPDX-License-Identifier: LicenseRef-Huitzo-Source-Available
#
# SessionStart hook — matcher: startup|resume. Never blocks (always exits
# 0). Prints a short (<=15 line) orientation to stdout, which Claude Code
# folds into session context: project kind, namespace(s), SDK pins found,
# local tooling presence, and 2-3 next-step hints. Outside a Huitzo project
# this is a silent no-op.
#
# No network beyond running local binaries the developer already has
# installed (`huitzo --version`, `claude --version`), both guarded by
# `timeout` when available. Bash 3.2 compatible.

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=./_lib.sh
. "$SCRIPT_DIR/_lib.sh"

# The Claude Code version floor below which claude/rules/*.md path-scoped
# rules are not honored (see README "Verified against").
CLAUDE_CODE_RULES_FLOOR="2.1.84"

PROJECT_ROOT="$(hz_project_root)" || exit 0

# Read hook stdin (unused fields are fine to ignore) without blocking if
# there is none — SessionStart may be invoked with an empty pipe.
INPUT="$(cat 2>/dev/null || true)"

hz_run_guarded() {
  # hz_run_guarded <seconds> -- <cmd...>: run with `timeout` if available,
  # plain otherwise (guards a possibly-slow or hanging external binary).
  secs="$1"
  shift
  if command -v timeout >/dev/null 2>&1; then
    timeout "$secs" "$@" 2>/dev/null
  else
    "$@" 2>/dev/null
  fi
}

KIND="$(hz_detect_kind "$PROJECT_ROOT")"

# --- namespace(s) ------------------------------------------------------------
NAMESPACES=""
for f in "$PROJECT_ROOT/huitzo.yaml" "$PROJECT_ROOT/pack/huitzo.yaml" \
  "$PROJECT_ROOT/huitzo-dashboard.yaml" "$PROJECT_ROOT/dashboard/huitzo-dashboard.yaml"; do
  if [ -f "$f" ]; then
    ns="$(hz_extract_namespace "$f")"
    [ -n "$ns" ] || continue
    case " $NAMESPACES " in
      *" $ns "*) ;;
      *) NAMESPACES="$NAMESPACES $ns" ;;
    esac
  fi
done
if [ -d "$PROJECT_ROOT/packs" ]; then
  for f in "$PROJECT_ROOT"/packs/*/huitzo.yaml; do
    [ -f "$f" ] || continue
    ns="$(hz_extract_namespace "$f")"
    [ -n "$ns" ] || continue
    case " $NAMESPACES " in
      *" $ns "*) ;;
      *) NAMESPACES="$NAMESPACES $ns" ;;
    esac
  done
fi
if [ -d "$PROJECT_ROOT/dashboards" ]; then
  for f in "$PROJECT_ROOT"/dashboards/*/huitzo-dashboard.yaml; do
    [ -f "$f" ] || continue
    ns="$(hz_extract_namespace "$f")"
    [ -n "$ns" ] || continue
    case " $NAMESPACES " in
      *" $ns "*) ;;
      *) NAMESPACES="$NAMESPACES $ns" ;;
    esac
  done
fi
NAMESPACES="$(printf '%s' "$NAMESPACES" | sed -E 's/^ +//; s/ +$//; s/ +/, /g')"
[ -n "$NAMESPACES" ] || NAMESPACES="none found"

# --- SDK pins ------------------------------------------------------------
SDK_PIN="not found (no pyproject.toml)"
for f in "$PROJECT_ROOT/pyproject.toml" "$PROJECT_ROOT/pack/pyproject.toml"; do
  if [ -f "$f" ]; then
    hit="$(grep -m1 -i 'huitzo-sdk' "$f" 2>/dev/null)"
    if [ -n "$hit" ]; then
      SDK_PIN="$(printf '%s' "$hit" | sed -E 's/^[[:space:]]*//; s/[[:space:]]*$//')"
    else
      SDK_PIN="pyproject.toml present, no huitzo-sdk pin found"
    fi
    break
  fi
done

REACT_SDK_PIN="not found (no package.json)"
for f in "$PROJECT_ROOT/package.json" "$PROJECT_ROOT/dashboard/package.json"; do
  if [ -f "$f" ]; then
    hit="$(grep -m1 '@huitzo/dashboard-sdk-react' "$f" 2>/dev/null)"
    if [ -n "$hit" ]; then
      REACT_SDK_PIN="$(printf '%s' "$hit" | sed -E 's/^[[:space:]]*//; s/,[[:space:]]*$//')"
    else
      REACT_SDK_PIN="package.json present, no @huitzo/dashboard-sdk-react pin found"
    fi
    break
  fi
done

# --- local tooling presence -----------------------------------------------
PY_ENV="none found"
for d in "$PROJECT_ROOT/venv" "$PROJECT_ROOT/.venv" "$PROJECT_ROOT/pack/venv" "$PROJECT_ROOT/pack/.venv"; do
  if [ -d "$d" ]; then
    PY_ENV="${d#"$PROJECT_ROOT"/}"
    break
  fi
done

NODE_ENV="none found"
for d in "$PROJECT_ROOT/node_modules" "$PROJECT_ROOT/dashboard/node_modules"; do
  if [ -d "$d" ]; then
    NODE_ENV="${d#"$PROJECT_ROOT"/}"
    break
  fi
done

CLI_LINE="not on PATH"
CLI_VERSION=""
if command -v huitzo >/dev/null 2>&1; then
  CLI_VERSION="$(hz_run_guarded 3 huitzo --version)"
  if [ -n "$CLI_VERSION" ]; then
    CLI_LINE="on PATH ($CLI_VERSION)"
  else
    CLI_LINE="on PATH"
  fi
fi

MCP_DOCS="not configured"
MCP_JSON="$PROJECT_ROOT/.mcp.json"
HAS_DOCS_DIR=0
[ -d "$PROJECT_ROOT/docs" ] && HAS_DOCS_DIR=1
if [ -f "$MCP_JSON" ] && grep -q '"pack-docs"' "$MCP_JSON" 2>/dev/null; then
  MCP_DOCS="configured (pack-docs)"
fi

# --- next-step hints (2-3) --------------------------------------------------
HINT1=""
HINT2=""
HINT3=""
if [ "$HAS_DOCS_DIR" -eq 1 ] && [ "$MCP_DOCS" = "not configured" ]; then
  HINT1="run /huitzo-init to wire the project docs MCP server (docs/ exists, .mcp.json has no pack-docs entry)"
fi

if command -v claude >/dev/null 2>&1; then
  CLAUDE_VER_RAW="$(hz_run_guarded 3 claude --version)"
  CLAUDE_VER="$(printf '%s' "$CLAUDE_VER_RAW" | grep -Eo '[0-9]+\.[0-9]+\.[0-9]+' | head -1)"
  if [ -n "$CLAUDE_VER" ] && hz_version_lt "$CLAUDE_VER" "$CLAUDE_CODE_RULES_FLOOR"; then
    HINT2="Claude Code $CLAUDE_VER is below $CLAUDE_CODE_RULES_FLOOR: YAML-list paths: in .claude/rules/*.md may load unscoped (always on) — upgrade Claude Code"
  fi
fi

if [ -z "$HINT2" ]; then
  case "$KIND" in
    pack | "project (pack+dashboard)" | "application (packs/+dashboards/)")
      if [ "$PY_ENV" = "none found" ]; then
        HINT2="no Python venv found — create one before running pytest/ruff/mypy"
      fi
      ;;
  esac
fi

case "$KIND" in
  dashboard | "project (pack+dashboard)" | "application (packs/+dashboards/)")
    if [ "$NODE_ENV" = "none found" ]; then
      HINT3="no node_modules found — run npm install before dev/build/test"
    fi
    ;;
esac
if [ -z "$HINT3" ] && [ "$CLI_LINE" = "not on PATH" ]; then
  HINT3="huitzo CLI not on PATH — install it to run validate/test locally (see https://docs.huitzo.ai/docs/guides/quickstart/installation)"
fi

# --- print (<=15 lines) ------------------------------------------------------
printf 'Huitzo project detected — kind: %s\n' "$KIND"
printf 'Namespace(s): %s\n' "$NAMESPACES"
printf 'huitzo-sdk pin: %s\n' "$SDK_PIN"
printf 'dashboard-sdk-react pin: %s\n' "$REACT_SDK_PIN"
printf 'Python venv: %s | node_modules: %s\n' "$PY_ENV" "$NODE_ENV"
printf 'huitzo CLI: %s\n' "$CLI_LINE"
printf '.mcp.json pack-docs: %s\n' "$MCP_DOCS"
if [ -n "$HINT1" ] || [ -n "$HINT2" ] || [ -n "$HINT3" ]; then
  printf 'Next steps:\n'
  [ -n "$HINT1" ] && printf '  - %s\n' "$HINT1"
  [ -n "$HINT2" ] && printf '  - %s\n' "$HINT2"
  [ -n "$HINT3" ] && printf '  - %s\n' "$HINT3"
fi

exit 0
