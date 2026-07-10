"""Prove every GoC hook command registration word-splits when the project
(or plugin) path contains a space.

`GOC_CLAUDE_HOOKS` in goc/install.py (and the hand-maintained
claude-plugin/hooks/hooks.json, codex-plugin/hooks/hooks.json, plus this
repo's dogfood .claude/settings.json) registers hook commands with an
unquoted `${CLAUDE_PROJECT_DIR}` / `${CLAUDE_PLUGIN_ROOT}` expansion.
Claude Code runs hook commands through a shell, so a repo checked out at
a path with a space (`~/My Project`, Google Drive's `My Drive`, ...)
splits the expansion into two words and python3 exits 2 with
"can't open file". Exit 2 from a Stop hook is Claude Code's *block*
channel, so the broken registration actively blocks the agent's stop.

Exits non-zero while any registered command fails under a spaced path;
exits zero once every command survives (i.e. the expansion is quoted).
"""

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

from goc.install import GOC_CLAUDE_HOOKS  # noqa: E402

failures = []
with tempfile.TemporaryDirectory() as td:
    project = Path(td) / "My Project"
    hooks_dir = project / ".claude" / "hooks"
    hooks_dir.mkdir(parents=True)
    for template in (ROOT / "goc" / "templates" / "hooks").glob("*.py"):
        shutil.copy(template, hooks_dir / template.name)

    for event, command in GOC_CLAUDE_HOOKS.items():
        proc = subprocess.run(
            ["sh", "-c", command],
            input="{}",
            capture_output=True,
            text=True,
            env={
                "PATH": "/usr/bin:/bin:/usr/local/bin",
                "CLAUDE_PROJECT_DIR": str(project),
            },
        )
        if proc.returncode != 0:
            failures.append((event, command, proc.returncode, proc.stderr.strip()))

if failures:
    for event, command, code, stderr in failures:
        print(f"DEFECT: {event} hook exits {code} under a spaced project path")
        print(f"  command: {command}")
        print(f"  stderr:  {stderr}")
    print(
        "note: exit 2 from a Stop hook is Claude Code's block channel — "
        "the Stop registration blocks the agent's stop with this garbled error"
    )
    sys.exit(1)

print("OK: every GOC_CLAUDE_HOOKS command survives a project path with a space")
