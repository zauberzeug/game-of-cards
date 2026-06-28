"""Exercise the three nested-hooks-shape sub-defects in `_merge_claude_settings`
and `_strip_goc_settings_entries`. Pre-fix the script crashed with raw
`AttributeError` on shapes #1 and #2 and silently char-exploded a string into a
list on shape #3; post-fix all three surface a coherent warning and either
coerce to a safe default (merge path) or leave the file untouched (strip path).

The script exits zero only when every shape behaves as designed post-fix.
"""

from __future__ import annotations

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

from goc.install import _merge_claude_settings, _strip_goc_settings_entries  # noqa: E402


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload))


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)

        # Shape #1: hooks is a list (merge path) — must not crash; file
        # coerced to a valid GoC-hooks dict and original bytes backed up.
        s1 = root / "s1" / "settings.json"
        _write(s1, {"hooks": []})
        print("shape #1: hooks is a list (merge path)")
        try:
            _merge_claude_settings(s1)
            merged = json.loads(s1.read_text())
            if not isinstance(merged.get("hooks"), dict):
                failures.append("shape #1: hooks not coerced to dict")
            if not list(s1.parent.glob("settings.json.*.bak")):
                failures.append("shape #1: no backup file created")
            print("  merge result: OK")
        except AttributeError as e:
            failures.append(f"shape #1: AttributeError {e}")
            print(f"  merge result: CRASH — AttributeError: {e}")
        print()

        # Shape #2: hooks.SessionStart is a string (merge path) — must not
        # crash; event value reset to [] with a backup; GoC hook then added.
        s2 = root / "s2" / "settings.json"
        _write(s2, {"hooks": {"SessionStart": "oops"}})
        print("shape #2: hooks.SessionStart is a string (merge path)")
        try:
            _merge_claude_settings(s2)
            merged = json.loads(s2.read_text())
            event_value = merged.get("hooks", {}).get("SessionStart")
            if not isinstance(event_value, list):
                failures.append("shape #2: event value not coerced to list")
            backups = list(s2.parent.glob("settings.json.*.bak"))
            if not backups:
                failures.append("shape #2: no backup file created")
            elif '"oops"' not in backups[0].read_text():
                failures.append("shape #2: backup missing original 'oops' value")
            print("  merge result: OK")
        except AttributeError as e:
            failures.append(f"shape #2: AttributeError {e}")
            print(f"  merge result: CRASH — AttributeError: {e}")
        print()

        # Shape #3: hooks.SessionStart is a string (strip path) — must NOT
        # char-explode the string; file is left untouched and a warning is
        # surfaced.
        s3 = root / "s3" / "settings.json"
        _write(s3, {"hooks": {"SessionStart": "oops"}})
        before = s3.read_text()
        print("shape #3: hooks.SessionStart is a string (strip path)")
        try:
            _strip_goc_settings_entries(s3)
            after = s3.read_text()
            if before != after:
                failures.append(
                    f"shape #3: strip rewrote file (before={before!r}, after={after!r})"
                )
            print(f"  file before strip: {before}")
            print(f"  file after strip:  {after}")
        except AttributeError as e:
            failures.append(f"shape #3: AttributeError {e}")
            print(f"  strip result: CRASH — AttributeError: {e}")

    if failures:
        print()
        print("FAIL:")
        for line in failures:
            print(f"  - {line}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
