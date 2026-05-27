"""Reproduce: `goc migrate` destroys card files other than README.md / log.md.

A card present in BOTH the legacy `deck/` tree and the canonical
`.game-of-cards/deck/` tree is classified `identical` using only a
README.md + log.md byte comparison. Identical cards are skipped from
the copy loop, then `shutil.rmtree(legacy)` deletes the whole legacy
tree — so any legacy-only file in that card dir (reproduce.py, notes,
attachments) is silently destroyed.

This script drives `_cmd_migrate` against a throwaway temp tree and
checks whether a legacy-only `reproduce.py` survives.
"""
import sys
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


sys.path.insert(0, str(_repo_root()))

import tempfile
import types
from goc import engine


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        legacy = root / "deck"
        canonical = root / ".game-of-cards" / "deck"

        # Card "foo" exists in BOTH trees with byte-identical README + log,
        # but the legacy copy also carries a reproduce.py the canonical lacks.
        (legacy / "foo").mkdir(parents=True)
        (canonical / "foo").mkdir(parents=True)
        for tree in (legacy, canonical):
            (tree / "foo" / "README.md").write_text("same readme\n")
            (tree / "foo" / "log.md").write_text("same log\n")
        (legacy / "foo" / "reproduce.py").write_text("# precious bug proof\n")

        # Point the engine's module-level path constants at our temp tree.
        engine.REPO_ROOT = root
        engine.DECK_DIR = canonical

        args = types.SimpleNamespace(dry_run=False, auto_yes=True)
        try:
            engine._cmd_migrate(args)
        except SystemExit:
            pass

        survivor = canonical / "foo" / "reproduce.py"
        legacy_gone = not legacy.exists()

        print(f"legacy tree removed: {legacy_gone}")
        print(f"canonical foo/reproduce.py exists: {survivor.exists()}")

        if legacy_gone and not survivor.exists():
            print()
            print("FAIL: reproduce.py was destroyed by goc migrate")
            print("expected: .game-of-cards/deck/foo/reproduce.py exists")
            print("actual:   missing (legacy tree deleted, card classified "
                  "'identical', never copied)")
            return 1

        print("PASS: legacy-only files preserved across migrate")
        return 0


if __name__ == "__main__":
    sys.exit(main())
