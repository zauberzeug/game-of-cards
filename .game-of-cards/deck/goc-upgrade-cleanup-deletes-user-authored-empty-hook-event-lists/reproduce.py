"""Reproduce: `_strip_goc_settings_entries` deletes user-authored empty event lists.

Run from the repo root:

    uv run python .game-of-cards/deck/goc-upgrade-cleanup-deletes-user-authored-empty-hook-event-lists/reproduce.py

Expected output before the fix:

    BEFORE: {...user placeholder...}
    AFTER:  {}

Expected output after the fix:

    BEFORE: {...user placeholder...}
    AFTER:  {...user placeholder...}

The script exits 0 when the user placeholder survives, 1 otherwise.
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

from goc.install import _strip_goc_settings_entries  # noqa: E402


def main() -> int:
    user_settings = {"hooks": {"MyUserEvent": []}}
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "settings.json"
        path.write_text(json.dumps(user_settings, indent=2))
        before = path.read_text()
        _strip_goc_settings_entries(path)
        after = path.read_text()

    print(f"BEFORE: {before}")
    print(f"AFTER:  {after}")

    survived = json.loads(after) == user_settings
    if survived:
        print("PASS: user-authored placeholder survived the strip pass.")
        return 0
    print("FAIL: user-authored placeholder was deleted by the strip pass.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
