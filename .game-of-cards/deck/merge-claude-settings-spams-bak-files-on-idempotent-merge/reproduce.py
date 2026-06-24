"""Reproduce: _merge_claude_settings spawns a .bak on every idempotent merge.

A settings.json that already carries every GoC hook AND contains one
non-object item inside a hooks[event][].hooks list is fully idempotent
under merge — GoC has nothing to add. Yet each merge writes a fresh
timestamped .bak sibling. Run three merges and count the backups.

Expected after fix: 0 .bak files, settings.json byte-for-byte unchanged.
Now (buggy): one .bak per merge.
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

from goc.install import GOC_CLAUDE_HOOKS, _merge_claude_settings  # noqa: E402


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        settings_path = Path(tmp) / ".claude" / "settings.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)

        # Already carries every GoC hook; one event group also holds a
        # non-object (string) item the user hand-authored.
        hooks: dict = {}
        for event, command in GOC_CLAUDE_HOOKS.items():
            hooks.setdefault(event, []).append(
                {"hooks": [{"type": "command", "command": command}]}
            )
        first_event = next(iter(GOC_CLAUDE_HOOKS))
        hooks[first_event][0]["hooks"].append("literal-user-item")

        original = json.dumps({"hooks": hooks}, indent=2) + "\n"
        settings_path.write_text(original)

        for _ in range(3):
            _merge_claude_settings(settings_path)

        backups = sorted(Path(tmp, ".claude").glob("settings.json.*.bak"))
        unchanged = settings_path.read_text() == original

        print(f"distinct .bak files created across 3 idempotent merges: {len(backups)}")
        print(f"settings.json byte-for-byte unchanged:                  {unchanged}")
        print()
        if backups:
            print("FAIL: an idempotent merge created backup file(s) and warned;")
            print("      expected 0 backups when GoC changes nothing.")
            return 1
        print("PASS: no backup created on a no-op merge.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
