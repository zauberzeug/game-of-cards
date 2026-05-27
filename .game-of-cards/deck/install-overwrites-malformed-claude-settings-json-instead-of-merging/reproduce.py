"""Reproduce: `goc install`/`upgrade` destroys a malformed .claude/settings.json.

When the existing settings.json fails to parse as JSON, `_merge_claude_settings`
swallows the JSONDecodeError and proceeds to write a file containing ONLY GoC
hooks — silently discarding every user key (permissions.allow, env, other hooks).

This contradicts the function's own docstring, which promises to add GoC hooks
"without removing unrelated keys or hooks that belong to the user."

Exit 0 == defect reproduced (user data was lost). Exit 1 == data preserved.
"""

import json
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

    after = json.loads(after_text)
    lost = []
    if "permissions" not in after:
        lost.append("permissions.allow")
    if "env" not in after:
        lost.append("env")

    if lost:
        print(f"DEFECT REPRODUCED: silently lost user keys: {', '.join(lost)}")
        print("The malformed file was overwritten with GoC hooks only; no backup written.")
        sys.exit(0)
    else:
        print("Data preserved — defect not present.")
        sys.exit(1)
