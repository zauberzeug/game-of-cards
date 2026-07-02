"""Reproduce: `_load_consuming_repo_tags` crashes on a fenced YAML block
that parses to a non-mapping (e.g. a bare list). The loader assumes every
` ```yaml ` block is a mapping and calls `block.get("canonical_tags")`
unconditionally.

Before the fix this prints a CRASH line and exits 1. After the fix the
loader skips the non-mapping block and returns set(), so this exits 0.
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

from unittest import mock  # noqa: E402

from goc import engine  # noqa: E402

LIST_BLOCK = "```yaml\n- frontend\n- backend\n```\n"

with tempfile.TemporaryDirectory() as tmp:
    game_dir = Path(tmp) / ".game-of-cards"
    game_dir.mkdir()
    (game_dir / "canonical-tags.md").write_text(LIST_BLOCK)
    with mock.patch.object(engine, "DECK_ROOT", Path(tmp)):
        print("list-shaped fenced yaml block:")
        try:
            result = engine._load_consuming_repo_tags()
        except Exception as ex:  # noqa: BLE001
            print(f"  CRASH: {type(ex).__name__} {ex}")
            print("expected: set()  (block is not a mapping -> skip it)")
            sys.exit(1)
        print(f"  result: {result!r}")
        assert result == set(), f"expected set(), got {result!r}"
        print("  OK: non-mapping block skipped, returned set()")

sys.exit(0)
