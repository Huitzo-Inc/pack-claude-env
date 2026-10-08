#!/usr/bin/env bash
# Copyright (c) 2026 Huitzo Inc. All rights reserved.
# SPDX-License-Identifier: LicenseRef-Huitzo-Source-Available
#
# Behavioural tests for the hook scripts in claude/hooks/. Runs each script the
# way Claude Code runs it (JSON on stdin, exit code + stderr as the contract)
# inside a throw-away project directory. Also checks that validate_env.py
# flags the wrong teaching the hooks nudge about. No network, no jq requirement.
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

expect_stderr_lacks() {  # expect_stderr_lacks <label> <needle>
  if grep -q -- "$2" "$TMP/err"; then fail "$1 (stderr had '$2'): $(head -c 300 "$TMP/err")"; else pass "$1"; fi
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
expect_exit "allows a JWT-shaped example in markdown" 0 "$HOOKS/secrets-scan.sh" \
  '{"tool_name":"Write","tool_input":{"file_path":"'"$TMP"'/project/docs/commands/x.md","content":"Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIn0.sig"}}'
expect_exit "still blocks a real key in markdown" 2 "$HOOKS/secrets-scan.sh" \
  '{"tool_name":"Write","tool_input":{"file_path":"'"$TMP"'/project/README.md","content":"sk-huitzo-0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"}}'
expect_exit "allows an absolute docs/*secret* path" 0 "$HOOKS/secrets-scan.sh" \
  '{"tool_name":"Write","tool_input":{"file_path":"'"$TMP"'/project/docs/secrets.md","content":"sk-huitzo-0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"}}'
printf '%s' '{"tool_name":"Write","tool_input":{"file_path":"x.py","content":"AKIAIOSFODNN7EXAMPLE1"}}' | (cd "$TMP/project" && HUITZO_SECRETS_SCAN=warn bash "$HOOKS/secrets-scan.sh") >"$TMP/out" 2>"$TMP/err"; got=$?
if [ "$got" -eq 0 ] && grep -q "AWS" "$TMP/err"; then pass "warn mode reports without blocking"; else fail "warn mode (exit $got)"; fi

echo "post-edit.sh"
expect_exit "warns on missing traceability (non-blocking)" 0 "$HOOKS/post-edit.sh" \
  '{"tool_name":"Write","tool_input":{"file_path":"'"$TMP"'/project/src/demo/commands/noheader.py"}}'
expect_stderr_contains "mentions Implements" "Implements"
expect_exit "silent on a file with a header" 0 "$HOOKS/post-edit.sh" \
  '{"tool_name":"Write","tool_input":{"file_path":"'"$TMP"'/project/src/demo/commands/hello.py"}}'
if grep -q "Implements" "$TMP/err"; then fail "no traceability warning expected"; else pass "no traceability warning"; fi
expect_exit "ignores missing file" 0 "$HOOKS/post-edit.sh" \
  '{"tool_name":"Write","tool_input":{"file_path":"'"$TMP"'/project/does-not-exist.py"}}'

CMD_DIR="$TMP/project/src/demo/commands"
write_cmd() {  # write_cmd <file> <body line>... — a command file with a traceability header
  local file="$CMD_DIR/$1"; shift
  printf '"""\nModule: m\n\nImplements:\n    - docs/commands/hello.md\n"""\n' >"$file"
  printf '%s\n' "$@" >>"$file"
}
post_edit() {  # post_edit <label> <file under src/demo/commands/>
  expect_exit "$1" 0 "$HOOKS/post-edit.sh" \
    '{"tool_name":"Write","tool_input":{"file_path":"'"$CMD_DIR/$2"'"}}'
}
write_cmd model_http.py 'async def run(args, ctx):' \
  '    return await ctx.http.post("https://api.openai.com/v1/chat/completions", json={})'
post_edit "model host with ctx.http is non-blocking" model_http.py
expect_stderr_contains "nudges towards ctx.llm" "model-provider host"
write_cmd data_http.py 'async def run(args, ctx):' \
  '    return await ctx.http.get("https://api.example.com/v1/weather/today")'
post_edit "ordinary ctx.http host" data_http.py
expect_stderr_lacks "no model-host nudge for a data API" "model-provider host"
write_cmd model_llm.py '# api.openai.com is the provider; this pack reaches it through ctx.llm' \
  'async def run(args, ctx):' '    return await ctx.llm.complete("hi", profile="default")'
post_edit "model host named without ctx.http" model_llm.py
expect_stderr_lacks "no model-host nudge without ctx.http" "model-provider host"
write_cmd chain.py 'async def run(args, ctx):' '    a = await ctx.commands.execute("extract", {})' \
  '    return await ctx.commands.execute("assess", a)'
post_edit "chained ctx.commands.execute is non-blocking" chain.py
expect_stderr_contains "suggests a pipeline" "belongs in a pipeline"
write_cmd single.py 'async def run(args, ctx):' '    # ctx.commands.execute("old", {}) used to be here' \
  '    return await ctx.commands.execute("lookup", {})'
post_edit "single ctx.commands.execute" single.py
expect_stderr_lacks "no pipeline nudge for one helper call" "belongs in a pipeline"
rm -f "$CMD_DIR/model_http.py" "$CMD_DIR/data_http.py" "$CMD_DIR/model_llm.py" "$CMD_DIR/chain.py" "$CMD_DIR/single.py"

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
mkdir -p "$TMP/notproject" && ( cd "$TMP/notproject" && timeout 5 bash "$HOOKS/docs-mcp.sh" >"$TMP/out" 2>"$TMP/err" ); got=$?
if [ "$got" -eq 1 ] && grep -q "project marker" "$TMP/err"; then pass "exits 1 with a message outside a Huitzo project"; else fail "outside project: exit $got"; fi
( cd "$TMP/project" && DOCS_ROOT='${CLAUDE_PROJECT_DIR}/docs' timeout 5 bash "$HOOKS/docs-mcp.sh" --print-config >"$TMP/out" 2>"$TMP/err" )
expect_stdout_contains "resolves docs root from CWD when unexpanded" "$TMP/project/docs"
rm -rf "$TMP/project/docs"
( cd "$TMP/project" && timeout 5 bash "$HOOKS/docs-mcp.sh" >"$TMP/out" 2>"$TMP/err" ); got=$?
if [ "$got" -eq 1 ]; then pass "exits 1 with a clear message when docs/ is missing"; else fail "exits $got when docs/ is missing (wanted 1)"; fi
expect_stderr_contains "names the missing docs root" "docs/ not found"

echo "validate_env.py (wrong teaching in the environment's own text)"
mkdir -p "$TMP/env/claude/rules" "$TMP/env/profiles"
validate_fixture() {  # validate_fixture <line written to claude/rules/x.md>
  printf '%s\n' "$1" >"$TMP/env/claude/rules/x.md"
  python3 "$ROOT/scripts/validate_env.py" --root "$TMP/env" >"$TMP/out" 2>"$TMP/err"
}
validate_fixture 'await ctx.http.post("https://api.openai.com/v1/chat/completions")'
expect_stdout_contains "flags a model-provider host taught as correct" "model-provider host"
validate_fixture 'await ctx.http.post("https://api.openai.com/v1/chat/completions")  # ❌'
if grep -q "model-provider host" "$TMP/out"; then fail "a ❌ model-host line must be exempt"; else pass "exempts a ❌ model-host line"; fi
validate_fixture 'async def run(args: Args, ctx: Context) -> dict:'
expect_stdout_contains "flags a command example returning an untyped dict" "untyped dict"
validate_fixture 'async def run(args: Args, ctx: Context) -> Result:'
if grep -q "untyped dict" "$TMP/out"; then fail "a typed return must pass"; else pass "accepts a typed return model"; fi

echo
if [ "$FAILURES" -gt 0 ]; then echo "test_hooks: $FAILURES failure(s)"; exit 1; fi
echo "test_hooks: all passed"
