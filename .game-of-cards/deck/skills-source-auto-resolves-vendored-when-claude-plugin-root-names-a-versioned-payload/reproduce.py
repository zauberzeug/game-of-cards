#!/usr/bin/env python3
"""Reproduce: `skills_source: auto` resolves to `vendored` when
CLAUDE_PLUGIN_ROOT points at a versioned payload root.

Claude Code sets CLAUDE_PLUGIN_ROOT to the running plugin's payload root,
which on a marketplace install is named for the version (e.g.
.../game-of-cards/0.0.25). `_claude_plugin_present()` should accept
`<CLAUDE_PLUGIN_ROOT>/skills/` regardless of the root's basename.

Prints PASS/FAIL and exits non-zero while the bug is present.

Run from the repo root:  uv run python .game-of-cards/deck/<this-card>/reproduce.py
"""
import os
import sys
import tempfile
from pathlib import Path


def main() -> int:
    # Empty HOME so the ~/.claude/plugins candidate cannot mask the bug.
    os.environ["HOME"] = tempfile.mkdtemp()

    base = Path(tempfile.mkdtemp())
    payload = base / "game-of-cards" / "0.0.25"  # versioned payload root
    (payload / "skills" / "deck").mkdir(parents=True)
    (payload / "skills" / "deck" / "SKILL.md").write_text("x")
    os.environ["CLAUDE_PLUGIN_ROOT"] = str(payload)

    from goc.engine import _claude_plugin_present, effective_skills_source

    present = _claude_plugin_present()
    print("payload root basename     :", payload.name)
    print("payload/skills exists      :", (payload / "skills").is_dir())
    print("_claude_plugin_present()   :", present, "  (expected True)")

    # effective_skills_source() reads the configured value; with no config it
    # treats the value as 'auto' and falls through to detection.
    resolved = effective_skills_source()
    print("effective_skills_source()  :", resolved, "  (expected plugin)")

    ok = present is True
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
