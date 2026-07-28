#!/usr/bin/env python3
"""Path A of the local release smoke script asserts a premise it never establishes.

`scripts/smoke_release.sh` installs `goc` with `uv tool install`, then sends a
prompt claiming "goc is on PATH". Nothing between those two steps extends PATH
to uv's tool-bin directory, and nothing checks that `goc` resolves — even though
the same script guards its *other* prerequisites (`claude` on PATH, plugin dir
present) with explicit errors. The CI job it mirrors does extend PATH.

Exits non-zero while the gap is present, zero once Path A either extends PATH or
guards `goc` resolvability before launching the agent run.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


ROOT = _repo_root()
sys.path.insert(0, str(ROOT))

SCRIPT = ROOT / "scripts" / "smoke_release.sh"
WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"

script_text = SCRIPT.read_text()
workflow_text = WORKFLOW.read_text()


def cite(text: str, needle: str, label: str) -> None:
    for i, line in enumerate(text.splitlines(), 1):
        if needle in line:
            print(f"    {label}:{i}: {line.strip()}")
            return
    print(f"    {label}: (no line containing {needle!r})")


print("[1] The CI smoke job puts the freshly-installed goc on PATH:")
cite(workflow_text, "uv tool install", "release.yml")
cite(workflow_text, "GITHUB_PATH", "release.yml")

print("[2] The local mirror installs it and stops there:")
cite(script_text, "uv tool install", "smoke_release.sh")

print("[3] ...then tells the agent goc is already reachable:")
cite(script_text, "goc is on PATH", "smoke_release.sh")

# `uv tool install` drops console scripts into uv's tool-bin dir. Whether that
# directory is on PATH is the user's shell configuration, not something the
# install guarantees -- uv itself warns when it is absent.
bin_dir = ""
try:
    bin_dir = subprocess.run(
        ["uv", "tool", "dir", "--bin"], capture_output=True, text=True, timeout=30,
    ).stdout.strip()
except (OSError, subprocess.SubprocessError):
    pass
print(f"[4] uv installs the goc executable into: {bin_dir or '(uv unavailable here)'}")

# Structural checks: does Path A close the gap either way?
extends_path = bool(re.search(r"(^|\s)(export\s+PATH|PATH=)", script_text, re.MULTILINE))
guards_goc = bool(re.search(r"command -v goc|which goc", script_text))
guards_claude = bool(re.search(r"command -v claude", script_text))
asserts_on_path = "goc is on PATH" in script_text

print("[5] smoke_release.sh, structurally:")
print(f"    extends PATH for uv's tool-bin dir?  {extends_path}")
print(f"    guards that `goc` resolves?          {guards_goc}")
print(f"    guards that `claude` resolves?       {guards_claude}   <- the idiom it already uses")
print(f"    Path A prompt asserts goc on PATH?   {asserts_on_path}")

# Consequence: with uv's bin dir off PATH, `goc` is simply unresolvable, so the
# prompt's premise is false and Path A fails on the harness, not the payload.
# A fixed minimal PATH keeps this deterministic -- the ambient PATH of whatever
# runs this file (e.g. `uv run`, which prepends the repo venv) must not decide
# the answer.
tmp = tempfile.mkdtemp()
fake = Path(tmp, "goc")
fake.write_text("#!/bin/sh\necho installed-goc\n")
fake.chmod(0o755)
baseline = os.pathsep.join(["/usr/local/bin", "/usr/bin", "/bin"])
print("[6] resolving `goc` for the agent run (minimal PATH, uv's bin dir stands in as tmp):")
print(f"    with the tool-bin dir OFF PATH: {shutil.which('goc', path=baseline)!r}")
print(f"    with the tool-bin dir ON  PATH: {shutil.which('goc', path=tmp + os.pathsep + baseline)!r}")
shutil.rmtree(tmp, ignore_errors=True)

defect = asserts_on_path and not extends_path and not guards_goc
print()
if defect:
    print(
        "[FAIL] Path A asserts `goc` is on PATH but neither extends PATH nor "
        "guards resolvability; on a machine without uv's bin dir on PATH it "
        "burns a 30-turn agent run and reports 'FAIL Path A: deck dir not "
        "created' -- blaming the plugin payload for a harness gap."
    )
else:
    print(
        "[OK] Path A closes the gap: it extends PATH to uv's tool-bin dir "
        "and/or fails fast when `goc` does not resolve."
    )
sys.exit(1 if defect else 0)
