"""Reproduce: pattern-generalization opt-out regex over-matches outside YAML structure.

The Stop hook at goc/templates/hooks/pattern_generalization_check.py uses an
unanchored `re.search` whose pattern matches the literal string
`pattern_generalization_check: false` anywhere in `.game-of-cards/config.yaml`.

This script writes three config files in which the literal opt-out string
appears in a position that is NOT a real opt-out key under `hooks:`:

  1. Under a different parent key (a `notes:` block-string).
  2. Inside a quoted scalar value as part of a longer sentence.
  3. Inside a YAML comment.

In each case, the real `hooks:` block either sets opt-out to True or omits the
key entirely — so the correct behavior is `_opted_out() -> False` (the hook
should fire). The current implementation returns True for all three.

Run from repo root via `uv run python deck/<title>/reproduce.py`.
"""

from __future__ import annotations

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


sys.path.insert(0, str(_repo_root() / "goc" / "templates" / "hooks"))

from pattern_generalization_check import _opted_out  # noqa: E402


CASES = {
    "under_unrelated_parent_key": """\
notes: |
  Reminder for new contributors: do not set
  pattern_generalization_check: false
  in this repo's config — we want the Stop reminder on every turn.

hooks:
  pattern_generalization_check: true
""",
    "inside_quoted_scalar_value": """\
description: "Set pattern_generalization_check: false to silence the Stop hook."

hooks:
  pattern_generalization_check: true
""",
    "inside_yaml_comment": """\
# Historically we tried pattern_generalization_check: false here;
# we now leave the hook on for every code-mutating turn.
hooks:
  pattern_generalization_check: true
""",
}


def main() -> int:
    failed = []
    with tempfile.TemporaryDirectory() as td:
        for label, payload in CASES.items():
            project = Path(td) / label
            (project / ".game-of-cards").mkdir(parents=True)
            (project / ".game-of-cards" / "config.yaml").write_text(payload)

            result = _opted_out(str(project))
            verdict = "FAIL" if result else "PASS"
            if result:
                failed.append(label)
            print(f"[{verdict}] {label}: _opted_out() -> {result} (expected False)")

    print()
    if failed:
        print(
            f"DEFECT REPRODUCED: {len(failed)}/{len(CASES)} non-key occurrences "
            f"silently opt the repo out: {failed}"
        )
        return 1
    print("All cases correctly recognized as NOT opt-out.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
