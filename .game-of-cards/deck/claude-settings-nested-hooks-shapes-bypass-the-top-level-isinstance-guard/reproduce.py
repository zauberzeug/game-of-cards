"""Reproduce the nested-hooks-shape defects in `_merge_claude_settings` and
`_strip_goc_settings_entries`.

The closed sibling `claude-settings-json-that-parses-to-a-non-dict-crashes-
install-with-attributeerror` guards the TOP-LEVEL shape of
`.claude/settings.json`. This script exercises three nested shapes that get
past that guard:

  1. `{"hooks": []}` — merge crashes with AttributeError (list has no setdefault).
  2. `{"hooks": {"SessionStart": "oops"}}` — merge crashes with AttributeError
     (str has no append).
  3. Same shape under the strip path — *no* crash, but the user's "oops" string
     is silently rewritten as `["o", "o", "p", "s"]`.
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


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)

        # Shape #1: hooks is a list (merge path)
        s1 = root / "s1" / "settings.json"
        _write(s1, {"hooks": []})
        print("shape #1: hooks is a list")
        try:
            _merge_claude_settings(s1)
            print("  merge result: OK (no exception)")
        except AttributeError as e:
            print(f"  merge result: CRASH — AttributeError: {e}")
        print()

        # Shape #2: hooks.SessionStart is a string (merge path)
        s2 = root / "s2" / "settings.json"
        _write(s2, {"hooks": {"SessionStart": "oops"}})
        print("shape #2: hooks.SessionStart is a string (merge path)")
        try:
            _merge_claude_settings(s2)
            print("  merge result: OK (no exception)")
        except AttributeError as e:
            print(f"  merge result: CRASH — AttributeError: {e}")
        print()

        # Shape #3: hooks.SessionStart is a string (strip path) — silent corruption
        s3 = root / "s3" / "settings.json"
        original = {"hooks": {"SessionStart": "oops"}}
        _write(s3, original)
        before = s3.read_text()
        print("shape #3: hooks.SessionStart is a string (strip path) — SILENT CORRUPTION")
        try:
            _strip_goc_settings_entries(s3)
            print("  strip result: OK (no exception)")
            after = s3.read_text()
            print(f"  file before strip: {before}")
            print(f"  file after strip:  {after}")
            after_obj = json.loads(after)
            event_value = after_obj.get("hooks", {}).get("SessionStart")
            if isinstance(event_value, list) and event_value == ["o", "o", "p", "s"]:
                print(
                    '  --> the user\'s "oops" string was char-exploded into a list '
                    "with no warning"
                )
        except AttributeError as e:
            print(f"  strip result: CRASH — AttributeError: {e}")


if __name__ == "__main__":
    main()
