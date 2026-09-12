#!/usr/bin/env bash
# Copyright (c) 2026 Huitzo Inc. All rights reserved.
# SPDX-License-Identifier: LicenseRef-Huitzo-Source-Available
#
# Shared helpers for claude/hooks/*.sh — sourced, never executed directly.
# Bash 3.2 compatible (no mapfile, no associative arrays, no ${var,,}).
# Two responsibilities:
#   1. The Huitzo project-marker gate (every hook is a no-op outside a
#      Huitzo project — plugin users open plenty of other repos too).
#   2. JSON field extraction from hook stdin, using jq when present and
#      falling back to python3 (no hard dependency on either).

# ---------------------------------------------------------------------------
# Project-marker gate
# ---------------------------------------------------------------------------

# hz_has_markers <dir>: true if <dir> looks like the root of a Huitzo
# pack, dashboard, project (pack+dashboard) or application (packs/+dashboards/).
hz_has_markers() {
  dir="$1"
  [ -f "$dir/huitzo.yaml" ] && return 0
  [ -f "$dir/huitzo-dashboard.yaml" ] && return 0
  [ -f "$dir/pack/huitzo.yaml" ] && return 0
  [ -f "$dir/dashboard/huitzo-dashboard.yaml" ] && return 0
  [ -d "$dir/packs" ] && return 0
  [ -d "$dir/dashboards" ] && return 0
  return 1
}

# hz_project_root: print the Huitzo project root and return 0, or print
# nothing and return 1. Checks $CLAUDE_PROJECT_DIR (if set) then $PWD —
# both are candidates for the "CWD" the hook was invoked with.
hz_project_root() {
  if [ -n "${CLAUDE_PROJECT_DIR:-}" ] && hz_has_markers "$CLAUDE_PROJECT_DIR"; then
    printf '%s\n' "$CLAUDE_PROJECT_DIR"
    return 0
  fi
  if hz_has_markers "$PWD"; then
    printf '%s\n' "$PWD"
    return 0
  fi
  return 1
}

# hz_in_project: boolean-only wrapper for the common "gate or exit 0" case.
hz_in_project() {
  hz_project_root >/dev/null 2>&1
}

# hz_detect_kind <root>: prints one of: pack | dashboard |
# "project (pack+dashboard)" | "application (packs/+dashboards/)" | unknown
hz_detect_kind() {
  root="$1"
  pack=0
  dash=0
  if [ -f "$root/huitzo.yaml" ] || [ -f "$root/pack/huitzo.yaml" ]; then
    pack=1
  fi
  if [ -f "$root/huitzo-dashboard.yaml" ] || [ -f "$root/dashboard/huitzo-dashboard.yaml" ]; then
    dash=1
  fi
  if [ -d "$root/packs" ] || [ -d "$root/dashboards" ]; then
    printf 'application (packs/+dashboards/)\n'
  elif [ "$pack" -eq 1 ] && [ "$dash" -eq 1 ]; then
    printf 'project (pack+dashboard)\n'
  elif [ "$pack" -eq 1 ]; then
    printf 'pack\n'
  elif [ "$dash" -eq 1 ]; then
    printf 'dashboard\n'
  else
    printf 'unknown\n'
  fi
}

# hz_extract_namespace <manifest-file>: grep-based (no YAML parser) pull of
# the `namespace:` scalar from a huitzo.yaml / huitzo-dashboard.yaml file.
hz_extract_namespace() {
  file="$1"
  [ -f "$file" ] || return 0
  grep -E '^[[:space:]]*namespace:[[:space:]]*' "$file" 2>/dev/null | head -1 \
    | sed -E 's/^[[:space:]]*namespace:[[:space:]]*//' \
    | sed -E 's/[[:space:]]+#.*$//' \
    | sed -E 's/^"(.*)"$/\1/' \
    | sed -E "s/^'(.*)'\$/\\1/"
}

# ---------------------------------------------------------------------------
# Traceability path rules (shared by post-edit.sh and pre-stop.sh)
# ---------------------------------------------------------------------------

# hz_is_traceable_source <relpath>: 0 if this path is one of the checked
# source locations (src/**/*.py|ts|tsx, optionally nested under pack/,
# packs/*/, dashboard/, dashboards/*/ for the application layout), after
# excluding tests/__init__/conftest/*.d.ts/dev.tsx. 1 otherwise.
hz_is_traceable_source() {
  rel="$1"
  case "$rel" in
    src/*.py | src/*.ts | src/*.tsx | \
      pack/src/*.py | pack/src/*.ts | pack/src/*.tsx | \
      dashboard/src/*.py | dashboard/src/*.ts | dashboard/src/*.tsx | \
      packs/*/src/*.py | packs/*/src/*.ts | packs/*/src/*.tsx | \
      dashboards/*/src/*.py | dashboards/*/src/*.ts | dashboards/*/src/*.tsx)
      ;;
    *)
      return 1
      ;;
  esac
  case "$rel" in
    */tests/* | test_* | */test_* | __init__.py | */__init__.py | \
      conftest.py | */conftest.py | *.d.ts | dev.tsx | */dev.tsx)
      return 1
      ;;
  esac
  return 0
}

# hz_traceability_marker <relpath>: prints the header token expected for
# this file's extension ("Implements:" for .py, "@implements" for ts/tsx).
hz_traceability_marker() {
  case "$1" in
    *.py) printf 'Implements:\n' ;;
    *) printf '@implements\n' ;;
  esac
}

# ---------------------------------------------------------------------------
# JSON extraction (jq preferred, python3 fallback, best-effort otherwise)
# ---------------------------------------------------------------------------

# hz_json_get <json> <dotted.path>: prints the string value at <dotted.path>
# (empty string if absent, non-JSON, or neither jq nor python3 is available).
# Stdin is never used for the payload — it is always passed as "$1" — so this
# is safe to call from a function that also needs its own stdin later.
hz_json_get() {
  json="$1"
  path="$2"
  [ -n "$json" ] || return 0
  if command -v jq >/dev/null 2>&1; then
    printf '%s' "$json" | jq -r --arg p "$path" '
      . as $root
      | ($p | split(".")) as $parts
      | reduce $parts[] as $k ($root; if . == null then null else (try .[$k] catch null) end)
      | if . == null then "" elif (type == "string") then . else tostring end
    ' 2>/dev/null
    return 0
  fi
  if command -v python3 >/dev/null 2>&1; then
    printf '%s' "$json" | python3 -c '
import sys, json
raw = sys.stdin.read()
path = sys.argv[1]
try:
    data = json.loads(raw) if raw.strip() else {}
except Exception:
    data = {}
cur = data
for part in path.split("."):
    if isinstance(cur, dict) and part in cur:
        cur = cur[part]
    else:
        cur = None
        break
if cur is None:
    print("")
elif isinstance(cur, (dict, list)):
    print(json.dumps(cur))
else:
    print(cur)
' "$path" 2>/dev/null
    return 0
  fi
  return 1
}

# hz_get_file_path <json>: tool_input.file_path, falling back to the
# camelCase spelling some tool schemas use.
hz_get_file_path() {
  json="$1"
  [ -n "$json" ] || return 0
  v="$(hz_json_get "$json" "tool_input.file_path")"
  if [ -z "$v" ]; then
    v="$(hz_json_get "$json" "tool_input.filePath")"
  fi
  printf '%s' "$v"
}

# hz_get_write_content <json>: the text a Write/Edit/MultiEdit/NotebookEdit
# call is about to put on disk — Write's .content, Edit's .new_string,
# MultiEdit's .edits[].new_string joined, or NotebookEdit's .new_source.
hz_get_write_content() {
  json="$1"
  [ -n "$json" ] || return 0
  if command -v jq >/dev/null 2>&1; then
    printf '%s' "$json" | jq -r '
      .tool_input as $ti
      | if $ti == null then ""
        elif $ti.content != null then $ti.content
        elif $ti.new_string != null then $ti.new_string
        elif $ti.new_source != null then $ti.new_source
        elif ($ti.edits | type) == "array" then ($ti.edits | map(.new_string // "") | join("\n"))
        else "" end
    ' 2>/dev/null
    return 0
  fi
  if command -v python3 >/dev/null 2>&1; then
    printf '%s' "$json" | python3 -c '
import sys, json
raw = sys.stdin.read()
try:
    data = json.loads(raw) if raw.strip() else {}
except Exception:
    data = {}
ti = data.get("tool_input") or {}
if not isinstance(ti, dict):
    ti = {}
if ti.get("content") is not None:
    out = ti["content"]
elif ti.get("new_string") is not None:
    out = ti["new_string"]
elif ti.get("new_source") is not None:
    out = ti["new_source"]
elif isinstance(ti.get("edits"), list):
    out = "\n".join(e.get("new_string", "") for e in ti["edits"] if isinstance(e, dict))
else:
    out = ""
sys.stdout.write(out if isinstance(out, str) else json.dumps(out))
' 2>/dev/null
    return 0
  fi
  return 1
}

# hz_version_lt <a> <b>: true (exit 0) if version <a> sorts before <b>.
# Tries `sort -V` first, falls back to a small python3 tuple comparison.
hz_version_lt() {
  a="$1"
  b="$2"
  [ "$a" = "$b" ] && return 1
  if printf '' | sort -V >/dev/null 2>&1; then
    first="$(printf '%s\n%s\n' "$a" "$b" | sort -V | head -1)"
    [ "$first" = "$a" ]
    return $?
  fi
  if command -v python3 >/dev/null 2>&1; then
    python3 -c '
import sys
def key(v):
    out = []
    for x in v.split("."):
        digits = ""
        for ch in x:
            if ch.isdigit():
                digits += ch
            else:
                break
        out.append(int(digits) if digits else 0)
    return tuple(out)
a, b = sys.argv[1], sys.argv[2]
sys.exit(0 if key(a) < key(b) else 1)
' "$a" "$b"
    return $?
  fi
  return 1
}
