"""Reproduce: `goc install`/`upgrade` destroys a malformed .claude/settings.json.

When the existing settings.json fails to parse as JSON, `_merge_claude_settings`
used to swallow the JSONDecodeError and write a file containing ONLY GoC hooks —
silently discarding every user key (permissions.allow, env, other hooks).

The fix preserves the user's original bytes in a timestamped `.bak` sibling and
prints a warning, so the data is recoverable and the loss is visible.

Exit 0 == defect reproduced (user data lost with no backup). Exit 1 == data preserved.
"""

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


sys.path.insert(0, str(_repo_root()))

from goc.install import _merge_claude_settings  # noqa: E402

# A realistic hand-edited-but-malformed settings.json: trailing comma after env.
MALFORMED = """{
  "permissions": {
    "allow": ["Bash(ls:*)", "Bash(uv run goc:*)"]
  },
  "env": {"FOO": "bar"},
}
"""

with tempfile.TemporaryDirectory() as d:
    settings_path = Path(d) / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(MALFORMED)

    print("BEFORE (user's malformed file):")
    print(settings_path.read_text())

    _merge_claude_settings(settings_path)

    after_text = settings_path.read_text()
    print("AFTER _merge_claude_settings:")
    print(after_text)

    # The malformed file can't be merged in place, so the user's bytes survive
    # in a timestamped `.bak` sibling rather than in the rewritten settings.json.
    backups = [
        p
        for p in settings_path.parent.iterdir()
        if p.name.startswith(settings_path.name + ".") and p.name.endswith(".bak")
    ]

    if backups and any(b.read_text() == MALFORMED for b in backups):
        print(f"Data preserved — original bytes backed up to {backups[0].name}.")
        sys.exit(1)
    else:
        print("DEFECT REPRODUCED: malformed file overwritten with GoC hooks only; no backup written.")
        sys.exit(0)
