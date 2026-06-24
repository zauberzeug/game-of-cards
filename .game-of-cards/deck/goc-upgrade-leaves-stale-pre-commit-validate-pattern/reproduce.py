"""Reproduce: goc upgrade leaves a stale pre-commit goc-validate `files:` glob.

A repo installed before the deck moved from deck/ to .game-of-cards/deck/ has a
.pre-commit-config.yaml whose goc-validate hook pins `files: ^deck/.*$`. On
`goc upgrade`, `_append_precommit_hook` sees `id: goc-validate` present and
returns without migrating the stale glob, so the hook never matches a real card
path. Exits non-zero while the bug is present.
"""

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

LEGACY = """\
repos:
  - repo: local
    hooks:
      - id: goc-validate
        name: goc validate
        entry: goc validate
        language: system
        pass_filenames: false
        files: ^deck/.*$
"""

NEW_PATTERN = r"^\.game-of-cards/deck/.*$"
LEGACY_PATTERN = r"files: ^deck/.*$"


def main() -> int:
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        (root / ".git").mkdir()
        cfg = root / ".pre-commit-config.yaml"
        cfg.write_text(LEGACY)

        before = cfg.read_text()
        _append_precommit_hook(cfg)
        after = cfg.read_text()

        changed = before != after
        still_legacy = LEGACY_PATTERN in after
        has_new = ".game-of-cards/deck" in after

        print(f"CHANGED: {changed}")
        print(f"still legacy ^deck/: {still_legacy}")
        print(f"has new .game-of-cards/deck: {has_new}")

        ok = has_new and not still_legacy
        if ok:
            print("PASS: upgrade migrated the stale validate files: glob.")
            return 0
        print("FAIL: stale validate files: glob survives upgrade — hook is dead.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
