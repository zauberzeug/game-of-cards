#!/usr/bin/env python3
"""Reproduce: the OpenClaw `agent_end` hook's code-mutation detector only
recognizes Claude Code's file-edit tool names.

Extracts the production predicate straight out of `openclaw-plugin/index.ts`
(the same TS-extraction technique `tests/test_openclaw_session_start_hook.py`
uses, so no `npm install` is needed) and runs it under Node against synthetic
tool-call lists.

Exit 0 means the defect is PRESENT: the shell branch accepts both hosts'
spellings while the edit branch accepts only Claude Code's three names and
none of the plausible OpenClaw-native spellings. Exit 1 means fixed.
"""

from __future__ import annotations

import json
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
INDEX_TS = ROOT / "openclaw-plugin" / "index.ts"


def _const_block(src: str, name: str) -> str:
    """Capture `const NAME = ...;`, including multi-line initializers."""
    m = re.search(rf"^const {re.escape(name)} = .*?;$", src, re.DOTALL | re.MULTILINE)
    if not m:
        raise SystemExit(f"const {name} not found in {INDEX_TS}")
    return m.group(0)


def _function_block(src: str, name: str) -> str:
    """Capture a top-level `function NAME(...)` block ending at a column-0 `}`."""
    m = re.search(
        rf"^function {re.escape(name)}\b.*?(?=^\}}$)\}}$", src, re.DOTALL | re.MULTILINE
    )
    if not m:
        raise SystemExit(f"function {name} not found in {INDEX_TS}")
    return m.group(0)


def _mutating_predicate(src: str) -> str:
    """Capture the `const mutating = toolCalls.some(...)` block from agent_end."""
    m = re.search(
        r"^      const mutating = toolCalls\.some\(.*?^      \}\);$",
        src,
        re.DOTALL | re.MULTILINE,
    )
    if not m:
        raise SystemExit(f"agent_end `mutating` predicate not found in {INDEX_TS}")
    return m.group(0)


# Claude Code's file-edit vocabulary, as hard-coded in CODE_MUTATING_TOOLS.
CLAUDE_EDIT_TOOLS = ("Edit", "Write", "NotebookEdit")
# Plausible spellings a non-Claude host would use for its edit tools. The exact
# OpenClaw names are the card's `unverified` axis; the point of the sweep is
# that NO spelling outside the Claude triple can ever satisfy the predicate.
OPENCLAW_EDIT_TOOLS = (
    "edit",
    "write",
    "edit_file",
    "write_file",
    "apply_patch",
    "str_replace_editor",
    "fileWrite",
    "patch",
)

PROBE_TAIL = """
const out = { claude_edit: {}, openclaw_edit: {}, shell_broad: {} };
for (const name of CLAUDE_EDIT_TOOLS) out.claude_edit[name] = detects([{ name }]);
for (const name of OPENCLAW_EDIT_TOOLS) out.openclaw_edit[name] = detects([{ name }]);
for (const name of ["exec", "Bash"]) {
  out.shell_broad[name] = detects([{ name, params: { command: "git add -A" } }]);
}
console.log(JSON.stringify(out));
"""


def main() -> int:
    node = shutil.which("node")
    if not node:
        print("SKIP: node not available")
        return 0

    src = INDEX_TS.read_text(encoding="utf-8")
    harness = "\n\n".join(
        [
            _const_block(src, "CODE_MUTATING_TOOLS"),
            _const_block(src, "BROAD_STAGING_FLAGS"),
            _function_block(src, "shellSplit"),
            _function_block(src, "isBroadGitMutation"),
            "function detects(toolCalls) {\n"
            + _mutating_predicate(src)
            + "\n      return mutating;\n}",
            f"const CLAUDE_EDIT_TOOLS = {json.dumps(list(CLAUDE_EDIT_TOOLS))};",
            f"const OPENCLAW_EDIT_TOOLS = {json.dumps(list(OPENCLAW_EDIT_TOOLS))};",
            PROBE_TAIL,
        ]
    )

    with tempfile.TemporaryDirectory() as tmp:
        script = Path(tmp) / "probe.ts"
        script.write_text(harness, encoding="utf-8")
        proc = subprocess.run(
            [node, "--experimental-strip-types", "--no-warnings", str(script)],
            capture_output=True,
            text=True,
        )
    if proc.returncode != 0:
        print("SKIP: node could not run the extracted TS harness")
        print(proc.stderr.strip()[:400])
        return 0

    res = json.loads(proc.stdout.strip())
    print("agent_end mutation detector — openclaw-plugin/index.ts")
    print()
    print("  SHELL branch (host-generalized: `exec` OR `Bash`):")
    for name, hit in res["shell_broad"].items():
        print(f"    {name:<20} git add -A  -> fires={hit}")
    print()
    print("  EDIT branch (CODE_MUTATING_TOOLS — Claude Code names only):")
    for name, hit in res["claude_edit"].items():
        print(f"    {name:<20} -> fires={hit}")
    print()
    print("  EDIT branch, OpenClaw-native spellings:")
    for name, hit in res["openclaw_edit"].items():
        print(f"    {name:<20} -> fires={hit}")
    print()

    shell_both = all(res["shell_broad"].values())
    claude_all = all(res["claude_edit"].values())
    openclaw_none = not any(res["openclaw_edit"].values())
    n_edit = len(res["openclaw_edit"])

    print(f"shell branch accepts both host spellings : {shell_both}")
    print(f"edit branch accepts all 3 Claude names   : {claude_all}")
    print(f"edit branch accepts 0/{n_edit} OpenClaw names : {openclaw_none}")
    print()
    if shell_both and claude_all and openclaw_none:
        print(
            "DEFECT PRESENT: the same predicate aliases the shell tool across "
            "hosts but hard-codes Claude Code's edit-tool vocabulary, so on "
            "OpenClaw the pattern-generalization reminder can only fire via a "
            "broad git command — never via a plain file edit."
        )
        return 0
    print("DEFECT ABSENT")
    return 1


if __name__ == "__main__":
    sys.exit(main())
