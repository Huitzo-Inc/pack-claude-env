#!/usr/bin/env python3
# Copyright (c) 2026 Huitzo Inc. All rights reserved.
# SPDX-License-Identifier: LicenseRef-Huitzo-Source-Available

"""
Module: scripts.check_api_surface
Description: Executable accuracy check. Installs the exact public package
    versions this environment documents and asserts that every API fact the
    reference skills teach is true against the real packages — signatures,
    keyword arguments, defaults, exception names, exports and the shipped
    `hz-*` CSS primitives. Grep-based validation cannot catch a wrong kwarg or
    a renamed class; this can.

    Needs network (PyPI + npm), `python3 -m venv`, and `npm`. Exit 0 when every
    assertion holds, 1 otherwise, 2 when a prerequisite is missing.

    Pinned versions live in VERSIONS below and must match the "Verified
    against" lines in claude/skills/*/SKILL.md (validate_env.py cross-checks).
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import textwrap
from pathlib import Path

VERSIONS = {
    "huitzo-sdk": "1.7.0",
    "@huitzo/dashboard-sdk-react": "5.1.1",
    "@huitzo/dashboard-sdk": "0.6.0",
}

# Exact hz-* class set the dashboard reference teaches. Anything the stylesheet
# ships that is missing here is reported as a warning; anything here that the
# stylesheet does not ship is an error (that is how `hz-arch` slipped through).
EXPECTED_HZ_CLASSES = {
    "hz-card", "hz-card--lg", "hz-card--md", "hz-card--accent", "hz-card--success", "hz-card--warning",
    "hz-stat__number", "hz-stat__number--success", "hz-stat__number--warning",
    "hz-rail", "hz-step", "hz-step__badge",
    "hz-terminal", "hz-terminal__header", "hz-terminal__dots", "hz-terminal__dot", "hz-terminal__label",
    "hz-terminal__body", "hz-terminal__prompt", "hz-terminal__output", "hz-terminal__copy",
    "hz-terminal__copy--ok",
    "hz-btn", "hz-btn--primary", "hz-btn--secondary", "hz-btn--ghost",
    "hz-eyebrow", "hz-eyebrow--accent",
    "hz-kbd", "hz-code", "hz-form",
}
EXPECTED_HZ_FAMILIES = ("hz-tf", "hz-dashboard", "hz-form")
NEVER_SHIPPED = {"hz-arch"}

EXPECTED_REACT_EXPORTS = {
    "HuitzoProvider", "useHuitzo", "useCommand", "useStreamingCommand", "useHubContext", "useLocale",
    "useHubNavigation", "useRealtime", "useHubActions", "useHubBreadcrumbs", "usePacks",
    "useConnectionStatus", "DashboardTile", "DashboardInfoBlock", "TileGlyphIcon", "resolveTileIdentity",
    "Dashboard", "Form", "TemplateFrame", "useTemplateCommand",
}

PY_ASSERTIONS = r'''
import asyncio, inspect, typing
import huitzo_sdk
from huitzo_sdk import command, Context
from huitzo_sdk import errors as E
from huitzo_sdk.command import command as _cmd

failures = []
def check(cond, msg):
    if not cond:
        failures.append(msg)

sig = inspect.signature(_cmd)
params = sig.parameters
check("name" in params and "namespace" in params, "@command must take name and namespace")
check(params["queue"].default == "medium", f"queue default should be 'medium', got {params['queue'].default!r}")
check(params["timeout"].default == 60, "timeout default should be 60")
check(params["retries"].default == 3, "retries default should be 3")
check("streaming" in params, "@command should accept streaming=")
check("description" in params, "@command should accept description=")
try:
    from huitzo_sdk.types import QueueName
    args = typing.get_args(QueueName)
    check(set(args) == {"fast", "medium", "long"}, f"QueueName should be fast|medium|long, got {args}")
except ImportError as exc:
    failures.append(f"QueueName import failed: {exc}")

for name in ["CommandTimeoutError", "PackPermissionError", "ValidationError", "CommandError",
             "StorageError", "SecretsError", "ExternalAPIError", "IntegrationError",
             "HTTPSecurityError", "ConfigurationError"]:
    check(hasattr(E, name), f"huitzo_sdk.errors.{name} missing")
check(not hasattr(E, "TimeoutError") or E.TimeoutError is not getattr(E, "CommandTimeoutError", None),
      "errors should not alias builtin TimeoutError")

from huitzo_sdk.integrations.llm import LLMClient
for meth in ("complete", "chat", "stream"):
    p = inspect.signature(getattr(LLMClient, meth)).parameters
    check("profile" in p, f"LLMClient.{meth} should accept profile=")
    check("model" not in p, f"LLMClient.{meth} must not accept model=")
check(asyncio.iscoroutinefunction(LLMClient.complete), "LLMClient.complete should be async")

from huitzo_sdk.integrations.telegram import TelegramClient
p = inspect.signature(TelegramClient.send).parameters
check("chat_id" in p and "message" in p, "TelegramClient.send(chat_id=, message=)")
check(not hasattr(TelegramClient, "send_message"), "TelegramClient.send_message should not exist")

from huitzo_sdk.integrations.secrets import SecretsClient
for meth in ("require", "get", "exists"):
    check(asyncio.iscoroutinefunction(getattr(SecretsClient, meth)), f"SecretsClient.{meth} should be async")

from huitzo_sdk.storage.client import StorageClient
for meth in ("save", "get", "delete", "exists", "list", "save_many", "get_many", "delete_many", "query"):
    check(hasattr(StorageClient, meth), f"StorageClient.{meth} missing")
check(not hasattr(StorageClient, "set"), "StorageClient.set should not exist (use save)")
p = inspect.signature(StorageClient.save).parameters
check(p["scope"].default == "user", "StorageClient.save scope default should be 'user'")

from huitzo_sdk.integrations.log import LogClient
check(not asyncio.iscoroutinefunction(LogClient.info), "LogClient.info should be sync")

from huitzo_sdk.integrations.ssh import SSHClient
p = inspect.signature(SSHClient.run).parameters
check("target" in p and "command" in p and p["timeout"].default == 30, "SSHClient.run(target, command, *, timeout=30)")

from huitzo_sdk.integrations.files import FileClient
for meth in ("read", "write", "delete", "move", "copy", "info", "list", "exists", "get_url"):
    check(hasattr(FileClient, meth), f"FileClient.{meth} missing")

from huitzo_sdk.manifest import permissions as P
tokens = {t.value for t in P.PermissionToken}
expected_tokens = {"storage:read", "storage:write", "files:read", "files:write", "files:delete",
                   "llm:complete", "llm:stream", "http:request", "email:send", "telegram:send",
                   "mcp:call", "ssh:execute", "exec:local", "tts:synthesize"}
check(tokens == expected_tokens, f"permission tokens differ: missing={expected_tokens - tokens} extra={tokens - expected_tokens}")
check(callable(getattr(P, "parse_permission", None)), "parse_permission should be importable")

from huitzo_sdk.manifest.models import CommandSpec, PackManifest
check("enabled" not in CommandSpec.model_fields, "CommandSpec has no 'enabled' field")
check(CommandSpec.model_fields["queue"].default == "medium", "CommandSpec.queue default medium")
check("policy" in PackManifest.model_fields and PackManifest.model_fields["policy"].is_required(), "policy card is required")
check(PackManifest.model_config.get("extra") == "forbid", "PackManifest uses extra=forbid")

for c in ("llm", "http", "email", "telegram", "tts", "files", "ssh", "db", "storage", "commands",
          "secrets", "log", "cron", "pipeline", "mcp", "integrations"):
    check(hasattr(Context, c), f"Context.{c} property missing")

print("\n".join(failures))
'''


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def check_python(tmp: Path) -> list[str]:
    venv = tmp / "venv"
    r = run([sys.executable, "-m", "venv", str(venv)])
    if r.returncode != 0:
        return [f"venv creation failed: {r.stderr.strip()}"]
    pip = venv / "bin" / "pip"
    py = venv / "bin" / "python"
    r = run([str(pip), "install", "-q", f"huitzo-sdk=={VERSIONS['huitzo-sdk']}"])
    if r.returncode != 0:
        return [f"pip install huitzo-sdk failed: {r.stderr.strip()[-400:]}"]
    script = tmp / "assert_sdk.py"
    script.write_text(textwrap.dedent(PY_ASSERTIONS))
    r = run([str(py), str(script)])
    if r.returncode != 0:
        return [f"assertion script crashed: {r.stderr.strip()[-600:]}"]
    return [line for line in r.stdout.splitlines() if line.strip()]


# Tokens the stylesheet must declare on `:root` inside the cascade layer. This
# is the white-label mechanism, not a wording check: `@layer huitzo-tokens`
# loses to the Hub's unlayered declarations of the same properties, and `:root`
# is what makes them resolve document-wide. The `.huitzo-dashboard` wrapper is
# the CSS scope selector for a dashboard's own styles — it declares no tokens, and
# several docs used to claim it did.
TOKEN_LAYER = "huitzo-tokens"
LAYER_ROOT_TOKENS = {"--color-bg-primary", "--color-text-primary", "--color-accent", "--color-border"}


def _strip_css_comments(css: str) -> str:
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def _css_block(css: str, at: int) -> str | None:
    """Body of the brace-balanced block opening at the first `{` at/after `at`."""
    start = css.find("{", at)
    if start < 0:
        return None
    depth = 0
    for i in range(start, len(css)):
        if css[i] == "{":
            depth += 1
        elif css[i] == "}":
            depth -= 1
            if depth == 0:
                return css[start + 1 : i]
    return None


def check_token_mechanism(css_text: str) -> list[str]:
    """Assert WHERE tokens are declared, so the docs that explain it stay true.

    Goes red if the SDK ever moves tokens under `.huitzo-dashboard` (which
    would make the wrapper load-bearing for `var(--color-*)`) or drops the
    cascade layer (which would break Hub white-labeling).
    """
    problems: list[str] = []
    css = _strip_css_comments(css_text)

    layer = re.search(rf"@layer\s+{TOKEN_LAYER}\b", css)
    if not layer:
        return [f"tokens.css: no `@layer {TOKEN_LAYER}` block — white-label inheritance "
                f"no longer works by layering; every doc explaining it is now wrong"]
    layer_body = _css_block(css, layer.end())
    if layer_body is None:
        return [f"tokens.css: `@layer {TOKEN_LAYER}` block is unbalanced"]

    root = re.search(r"(?:\A|[{};])\s*:root\s*\{", layer_body)
    root_body = _css_block(layer_body, root.end() - 1) if root else None
    if root_body is None:
        problems.append(f"tokens.css: no `:root` rule inside `@layer {TOKEN_LAYER}` — tokens no "
                        f"longer resolve document-wide")
    else:
        declared = set(re.findall(r"(--[a-zA-Z0-9-]+)\s*:", root_body))
        missing = sorted(LAYER_ROOT_TOKENS - declared)
        if missing:
            problems.append(f"tokens.css: `:root` inside `@layer {TOKEN_LAYER}` no longer declares "
                            f"{missing} — find where they moved before trusting the token docs")

    for rule in re.finditer(r"(?:\A|[{};])\s*([^{}@;]*\.huitzo-dashboard[^{}@;]*)\{", css):
        body = _css_block(css, rule.end() - 1) or ""
        if re.search(r"--[a-zA-Z0-9-]+\s*:", body):
            problems.append(f"tokens.css: rule `{rule.group(1).strip()}` declares custom properties "
                            f"— the wrapper class is now load-bearing for tokens; docs that call it "
                            f"a pure CSS scope selector must be rewritten")
    return problems


def check_npm(tmp: Path) -> list[str]:
    problems: list[str] = []
    if not shutil.which("npm"):
        return ["npm not available"]
    for pkg in ("@huitzo/dashboard-sdk-react", "@huitzo/dashboard-sdk"):
        spec = f"{pkg}@{VERSIONS[pkg]}"
        r = run(["npm", "pack", spec, "--pack-destination", str(tmp)], cwd=tmp)
        if r.returncode != 0:
            problems.append(f"npm pack {spec} failed: {r.stderr.strip()[-300:]}")
            continue
        tgz = tmp / r.stdout.strip().splitlines()[-1]
        with tarfile.open(tgz) as tf:
            names = tf.getnames()
            if pkg.endswith("react"):
                dts = [n for n in names if n.endswith("index.d.ts") or n.endswith("index.d.mts")]
                css = [n for n in names if n.endswith("tokens.css")]
                if not dts:
                    problems.append("react package: no index.d.ts in tarball")
                else:
                    text = tf.extractfile(dts[0]).read().decode("utf-8", "replace")
                    exported = set(re.findall(r"\b(?:export\s+(?:declare\s+)?(?:function|const|class|type|interface)\s+|\bexport\s*\{[^}]*\b)([A-Za-z_][A-Za-z0-9_]*)", text))
                    # export { a, b as c } lists — collect every identifier inside export braces
                    for block in re.findall(r"export\s*\{([^}]*)\}", text):
                        for ident in re.findall(r"([A-Za-z_][A-Za-z0-9_]*)\s*(?:,|$|as)", block):
                            exported.add(ident)
                    missing = sorted(EXPECTED_REACT_EXPORTS - exported)
                    if missing:
                        problems.append(f"react package: documented exports not found in d.ts: {missing}")
                if not css:
                    problems.append("react package: no tokens.css in tarball")
                else:
                    css_text = tf.extractfile(css[0]).read().decode("utf-8", "replace")
                    shipped = set(re.findall(r"\.(hz-[a-z0-9_-]+)", css_text))
                    missing = sorted(EXPECTED_HZ_CLASSES - shipped)
                    if missing:
                        problems.append(f"documented hz-* classes not shipped: {missing}")
                    for fam in EXPECTED_HZ_FAMILIES:
                        if not any(c == fam or c.startswith(fam + "__") for c in shipped):
                            problems.append(f"expected primitive family not shipped: {fam}")
                    leaked = sorted(NEVER_SHIPPED & shipped)
                    if leaked:
                        problems.append(f"classes assumed never-shipped now exist, update docs: {leaked}")
                    problems.extend(check_token_mechanism(css_text))
                    extra = sorted(c for c in shipped - EXPECTED_HZ_CLASSES
                                   if not any(c == f or c.startswith(f + "__") for f in EXPECTED_HZ_FAMILIES))
                    if extra:
                        print(f"warning: stylesheet ships undocumented hz-* classes: {extra}")
    return problems


def main() -> int:
    if not shutil.which("npm"):
        print("check_api_surface: npm missing", file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory(prefix="huitzo-surface-") as tmp:
        problems = check_python(Path(tmp)) + check_npm(Path(tmp))
    if problems:
        print(f"check_api_surface: {len(problems)} problem(s)")
        for p in problems:
            print("  " + p)
        return 1
    print("check_api_surface: every documented API fact holds against the published packages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
