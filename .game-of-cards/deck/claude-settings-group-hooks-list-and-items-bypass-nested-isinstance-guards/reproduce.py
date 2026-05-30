"""Reproduce the layer-4 nested-shape crash in goc/install.py.

Both `_merge_claude_settings` and `_strip_goc_settings_entries` crash
when `.claude/settings.json` has a wrong-shape value at
`hooks[event][i]["hooks"]` — the closed sibling guarded layers 2 and 3
(the `hooks` dict and the per-event list) but stopped one layer short.

Exits 0 once both functions handle every layer-4 sub-shape coherently
(no AttributeError / TypeError escapes, user file preserved or backed
up). Currently exits nonzero with the offending traceback class for
each shape.
"""

from __future__ import annotations

import json
import sys
import tempfile
import traceback
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

CASES = {
    "inner_hooks_string": {"hooks": {"SessionStart": [{"hooks": "oops"}]}},
    "inner_hooks_int": {"hooks": {"SessionStart": [{"hooks": 42}]}},
    "inner_hooks_dict": {"hooks": {"SessionStart": [{"hooks": {"x": 1}}]}},
    "inner_hooks_list_with_non_dict_item": {
        "hooks": {"SessionStart": [{"hooks": [{"command": "ls"}, "literal"]}]}
    },
}


def _try(fn, path: Path) -> tuple[bool, str]:
    try:
        fn(path)
        return True, ""
    except Exception as exc:  # noqa: BLE001
        return False, f"{type(exc).__name__}: {exc}"


def main() -> int:
    crashes = 0
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        for label, payload in CASES.items():
            print(f"=== {label}: hooks={payload['hooks']} ===")
            settings_path = tmp_dir / f"settings_{label}.json"
            original = json.dumps(payload)

            settings_path.write_text(original)
            ok, err = _try(_merge_claude_settings, settings_path)
            print(f"  merge: {'OK' if ok else err}")
            if not ok:
                crashes += 1

            settings_path.write_text(original)
            ok, err = _try(_strip_goc_settings_entries, settings_path)
            print(f"  strip: {'OK' if ok else err}")
            if not ok:
                crashes += 1

    expected = 2 * len(CASES)
    print(f"{crashes} / {expected} cases crash before any GoC hook entries are merged or stripped.")
    return 0 if crashes == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
