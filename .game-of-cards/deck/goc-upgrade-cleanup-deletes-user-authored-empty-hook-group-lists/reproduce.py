"""Reproduce: `_strip_goc_settings_entries` silently destroys a
user-authored placeholder group `{"matcher": "startup", "hooks": []}`.

Exits 0 once the bug is fixed (user state survives the strip pass).
Exits 1 on the buggy code (user state is gone after strip).
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

from goc.install import _strip_goc_settings_entries


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        settings_path = Path(tmp) / "settings.json"
        before = {
            "hooks": {
                "SessionStart": [
                    {"matcher": "startup", "hooks": []},
                ],
            },
        }
        settings_path.write_text(json.dumps(before))

        _strip_goc_settings_entries(settings_path)

        after = json.loads(settings_path.read_text())

        print(f"BEFORE: {json.dumps(before, separators=(', ', ': '))}")
        print(f"AFTER : {json.dumps(after, separators=(', ', ': '))}")

        expected_group = {"matcher": "startup", "hooks": []}
        survived = (
            after.get("hooks", {}).get("SessionStart") == [expected_group]
        )
        if not survived:
            print(
                "ASSERTION FAILED: user-authored group "
                '{"matcher": "startup", "hooks": []} was silently destroyed.'
            )
            return 1
        print("OK: user-authored group survived the strip pass.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
