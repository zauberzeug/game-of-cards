"""Reproduce: _merge_claude_settings rewrites .claude/settings.json even when
the merge is a semantic no-op (all GoC hooks already present).

A repeat `goc install --local-skills` or every `goc upgrade
--keep-local-skills` calls _merge_claude_settings. When the three GoC hooks
are already registered, the function still re-serialises through
json.dumps(..., indent=2), reflowing the user's chosen indentation and
re-ordering top-level keys — a spurious diff in a checked-in user file.

Contrast the sibling _strip_goc_settings_entries, which threads a `changed`
flag and guards its write with `if changed:` (install.py).
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

from goc.install import GOC_CLAUDE_HOOKS, _merge_claude_settings


def _seed_with_all_hooks() -> dict:
    """A settings.json that already carries every GoC hook, plus user keys,
    formatted with 4-space indentation and the user's own key ordering."""
    hooks: dict = {}
    for event, command in GOC_CLAUDE_HOOKS.items():
        hooks.setdefault(event, []).append(
            {"hooks": [{"type": "command", "command": command}]}
        )
    return {
        "permissions": {"allow": ["Bash(uv run goc:*)"]},
        "hooks": hooks,
        "env": {"MY_VAR": "1"},
    }


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        settings_path = Path(td) / ".claude" / "settings.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)

        # User-authored file: 4-space indent, user's own key order.
        original = json.dumps(_seed_with_all_hooks(), indent=4) + "\n"
        settings_path.write_text(original)

        _merge_claude_settings(settings_path)

        after = settings_path.read_text()
        rewritten = after != original

        # Confirm nothing semantic changed: same parsed object both ways.
        semantically_equal = json.loads(after) == json.loads(original)

        print(f"semantically equal (no hook needed adding): {semantically_equal}")
        print(f"file rewritten (bytes differ):              {rewritten}")
        print()
        print("Expected on a no-op merge: file rewritten = False")
        print(f"Actual:                    file rewritten = {rewritten}")

        # The defect fires iff a semantically-identical file was rewritten.
        defect_fires = semantically_equal and rewritten
        if defect_fires:
            print("\nDEFECT CONFIRMED: idempotent merge churned a user-owned file.")
            return 1
        print("\nOK: idempotent merge left the file untouched.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
