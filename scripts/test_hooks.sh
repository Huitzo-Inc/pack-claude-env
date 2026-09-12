#!/usr/bin/env bash
# Copyright (c) 2026 Huitzo Inc. All rights reserved.
# SPDX-License-Identifier: LicenseRef-Huitzo-Source-Available
#
# Behavioural tests for the hook scripts in claude/hooks/. Runs each script the
# way Claude Code runs it (JSON on stdin, exit code + stderr as the contract)
# inside a throw-away project directory. No network, no jq requirement.
#
# Usage: bash scripts/test_hooks.sh   (from the repo root)

set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOOKS="$ROOT/claude/hooks"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
FAILURES=0

pass() { printf '  ok   %s\n' "$1"; }
fail() { printf '  FAIL %s\n' "$1"; FAILURES=$((FAILURES + 1)); }

expect_exit() {  # expect_exit <label> <expected-code> <script> <stdin-json>
  local label="$1" want="$2" script="$3" input="$4" got
  printf '%s' "$input" | (cd "$TMP/project" && bash "$script") >"$TMP/out" 2>"$TMP/err"
  got=$?
  if [ "$got" -eq "$want" ]; then pass "$label (exit $got)"; else fail "$label (exit $got, wanted $want): $(head -c 300 "$TMP/err")"; fi
}

expect_stderr_contains() {  # expect_stderr_contains <label> <needle>
  if grep -q -- "$2" "$TMP/err"; then pass "$1"; else fail "$1 (stderr lacked '$2'): $(head -c 300 "$TMP/err")"; fi
}

expect_stdout_contains() {  # expect_stdout_contains <label> <needle>
  if grep -q -- "$2" "$TMP/out"; then pass "$1"; else fail "$1 (stdout lacked '$2'): $(head -c 300 "$TMP/out")"; fi
}

# --- fixture project: a minimal pack --------------------------------------
mkdir -p "$TMP/project/src/demo/commands" "$TMP/project/tests" "$TMP/project/docs/commands"
cat >"$TMP/project/huitzo.yaml" <<'YAML'
schema_version: 2
pack:
  name: demo
  namespace: demo
  version: 0.0.0
  description: "demo"
YAML
printf '"""\nModule: hello\n\nImplements:\n    - docs/commands/hello.md\n"""\n' >"$TMP/project/src/demo/commands/hello.py"
printf 'def x():\n    return 1\n' >"$TMP/project/src/demo/commands/noheader.py"
printf 'HUITZO_API_KEY=\n' >"$TMP/project/.env.example"
(cd "$TMP/project" && git init -q . && git add -A && git -c user.email=t@t -c user.name=t commit -qm init)

echo "secrets-scan.sh"
expect_exit "blocks a Huitzo API key" 2 "$HOOKS/secrets-scan.sh" \
  '{"tool_name":"Write","tool_input":{"file_path":"src/demo/commands/hello.py","content":"KEY = \"sk-huitzo-0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef\""}}'
expect_exit "blocks a PEM private key" 2 "$HOOKS/secrets-scan.sh" \
  '{"tool_name":"Write","tool_input":{"file_path":"x.py","content":"-----BEGIN RSA PRIVATE KEY-----\\nabc"}}'
expect_exit "allows ordinary code" 0 "$HOOKS/secrets-scan.sh" \
  '{"tool_name":"Edit","tool_input":{"file_path":"src/demo/commands/hello.py","new_string":"api_key = await ctx.secrets.require(\"OPENAI_API_KEY\")"}}'
expect_exit "allows .env.example" 0 "$HOOKS/secrets-scan.sh" \
  '{"tool_name":"Write","tool_input":{"file_path":".env.example","content":"AWS_KEY=AKIAIOSFODNN7EXAMPLE"}}'
expect_exit "tolerates empty input" 0 "$HOOKS/secrets-scan.sh" ''

echo "post-edit.sh"
expect_exit "warns on missing traceability (non-blocking)" 0 "$HOOKS/post-edit.sh" \
  '{"tool_name":"Write","tool_input":{"file_path":"'"$TMP"'/project/src/demo/commands/noheader.py"}}'
expect_stderr_contains "mentions Implements" "Implements"
expect_exit "silent on a file with a header" 0 "$HOOKS/post-edit.sh" \
  '{"tool_name":"Write","tool_input":{"file_path":"'"$TMP"'/project/src/demo/commands/hello.py"}}'
if grep -q "Implements" "$TMP/err"; then fail "no traceability warning expected"; else pass "no traceability warning"; fi
expect_exit "ignores missing file" 0 "$HOOKS/post-edit.sh" \
  '{"tool_name":"Write","tool_input":{"file_path":"'"$TMP"'/project/does-not-exist.py"}}'

echo "pre-stop.sh"
printf 'def y():\n    return 2\n' >"$TMP/project/src/demo/commands/changed.py"
(cd "$TMP/project" && git add -A)
expect_exit "never blocks" 0 "$HOOKS/pre-stop.sh" '{"hook_event_name":"Stop"}'
expect_stderr_contains "lists the unheadered file" "changed.py"

echo "session-start.sh"
expect_exit "prints context" 0 "$HOOKS/session-start.sh" '{"hook_event_name":"SessionStart","cwd":"'"$TMP"'/project"}'
expect_stdout_contains "detects a pack" "pack"
expect_stdout_contains "reports the namespace" "demo"

echo "docs-mcp.sh"
( cd "$TMP/project" && DOCS_ROOT='${CLAUDE_PROJECT_DIR}/docs' timeout 5 bash "$HOOKS/docs-mcp.sh" --print-config >"$TMP/out" 2>"$TMP/err" )
expect_stdout_contains "resolves docs root from CWD when unexpanded" "$TMP/project/docs"
rm -rf "$TMP/project/docs"
( cd "$TMP/project" && timeout 5 bash "$HOOKS/docs-mcp.sh" >"$TMP/out" 2>"$TMP/err" ); got=$?
if [ "$got" -eq 0 ]; then pass "exits 0 when docs/ is missing"; else fail "exits $got when docs/ is missing"; fi

echo
if [ "$FAILURES" -gt 0 ]; then echo "test_hooks: $FAILURES failure(s)"; exit 1; fi
echo "test_hooks: all passed"
