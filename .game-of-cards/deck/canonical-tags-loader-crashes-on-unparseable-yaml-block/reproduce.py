"""Reproduce: an unparseable fenced YAML block in canonical-tags.md
crashes `_load_consuming_repo_tags` (and thus every goc command, since
`load_schema()` runs at import time).

Run on a clean checkout:

    uv run python .game-of-cards/deck/canonical-tags-loader-crashes-on-unparseable-yaml-block/reproduce.py

Before the fix: prints the ParseError and exits non-zero.
After the fix: prints that the malformed block was skipped and the
well-formed sibling block still contributed its tag, then exits zero.
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

from unittest import mock

from goc import engine

# A user-authored canonical-tags.md: one well-formed block that should
# contribute `real-tag`, and one illustrative block using a folded (`>`)
# scalar that the vendored yaml_lite parser cannot parse.
BODY = (
    "# Project canonical tags\n\n"
    "```yaml\n"
    "canonical_tags:\n"
    "  - real-tag\n"
    "```\n\n"
    "Example of a description block:\n\n"
    "```yaml\n"
    "canonical_tags:\n"
    "  - example-tag\n"
    "description: >\n"
    "  folded example text\n"
    "```\n"
)

with tempfile.TemporaryDirectory() as tmp:
    game_dir = Path(tmp) / ".game-of-cards"
    game_dir.mkdir()
    (game_dir / "canonical-tags.md").write_text(BODY)
    with mock.patch.object(engine, "DECK_ROOT", Path(tmp)):
        try:
            tags = engine._load_consuming_repo_tags()
        except Exception as exc:  # noqa: BLE001 — this IS the defect
            print("DEFECT REPRODUCED: _load_consuming_repo_tags raised")
            print(f"  {type(exc).__module__}.{type(exc).__name__}: {exc}")
            print(
                "  A hand-authored canonical-tags.md with an unsupported "
                "YAML feature crashes every goc command via load_schema() "
                "at import time."
            )
            sys.exit(1)

    print("FIX CONFIRMED: malformed block skipped, no exception raised.")
    print(f"  loaded tags = {sorted(tags)}")
    assert "real-tag" in tags, (
        "well-formed sibling block must still contribute its tag"
    )
    print("  well-formed sibling block still contributed 'real-tag'.")
    sys.exit(0)
