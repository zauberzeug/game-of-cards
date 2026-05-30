"""Reproduce: `_append_precommit_hook` corrupts a `.pre-commit-config.yaml`
that has any top-level key after `repos:`.

The installer's helper at `goc/install.py:941` calls `text + PRE_COMMIT_HOOK`,
which only produces valid YAML when `repos:` is the file's last block.
For real-world configs that carry `default_language_version`, `exclude`,
or other top-level keys *after* `repos:`, the appended `- repo: local`
block lands outside the `repos:` list — YAML cannot parse the result.
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


sys.path.insert(0, str(_repo_root()))

from goc.install import _append_precommit_hook  # noqa: E402

EXISTING_CONFIG = """\
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: trailing-whitespace

default_language_version:
  python: python3.11

exclude: '^vendor/'
"""


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / ".git").mkdir()
        target = root / ".pre-commit-config.yaml"
        target.write_text(EXISTING_CONFIG)

        _append_precommit_hook(target)
        after = target.read_text()
        print("--- file after _append_precommit_hook ---")
        print(after)
        print("--- structural verdict ---")
        # The defect: the new `- repo: local` block was appended AFTER the
        # last top-level key (`exclude:`), so it is not nested under `repos:`.
        # Detect this by checking that the appended block does not immediately
        # follow the `repos:` list. Robust to YAML parser availability.
        last_repos_idx = after.rfind("\nrepos:")
        last_appended_idx = after.rfind("\n  - repo: local")
        last_other_top_level = max(
            after.rfind("\ndefault_language_version:"),
            after.rfind("\nexclude:"),
            after.rfind("\nfail_fast:"),
        )
        appended_inside_repos = (
            last_appended_idx > last_repos_idx
            and last_appended_idx < last_other_top_level
        )
        if appended_inside_repos:
            print("OK: appended hook is inside the repos: block (fix in place).")
            return 0
        print("DEFECT REPRODUCED: appended hook lands AFTER another top-level key,")
        print("which means it is no longer a child of `repos:`. This is invalid YAML;")
        print("`pre-commit run` will fail with a parser error.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
