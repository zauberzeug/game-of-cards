"""The zero-match line's hidden-draft clause disappears at `--status all`.

Two decks, one draft card each, rendered twice — once with an explicit
`--status open` and once with the status the command line actually resolves
to. `--waiting` / `--closed-since` / `--board` auto-extend an unset `--status`
to `all` (`engine._cmd_default`), and the recount is guarded on
`status != "all"`, so the second rendering drops a clause the first prints.

The control at the end publishes the draft and re-runs the same query: the
card appears, which is what makes the omitted clause a false negative rather
than a correctly-withheld one.

Exits 0 while the defect is present, non-zero once it is fixed.
"""

from __future__ import annotations

import io
import sys
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


sys.path.insert(0, str(_repo_root()))

from goc import engine  # noqa: E402

CARD = """---
title: {title}
summary: "Summary for {title}."
status: open
stage: null
contribution: medium
created: "2026-08-01T00:00:00Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug]
{extra}definition_of_done: |
  - [ ] TDD: something
---

# {title}

Body.
"""

CLAUSE = "unauthored draft scaffold"


class _Args:
    """Stand-in for the argparse namespace `_cmd_default` reads."""

    def __init__(self, **kw):
        defaults = dict(
            done_flag=False, status_flag=None, closed_since=None, waiting=False,
            board=False, as_json=False, slim=False, since=None, stage_flag=None,
            contribution=None, human_gate=None, tags=[], advances=None,
            advanced_by=None, worker=None, ready=False, verbose=0,
            no_color=True, max_rows=20,
        )
        defaults.update(kw)
        for k, v in defaults.items():
            setattr(self, k, v)


def render(**kw) -> str:
    buf = io.StringIO()
    with redirect_stdout(buf):
        engine._cmd_default(_Args(**kw))
    return buf.getvalue().strip()


def build_deck(root: Path, name: str, *, waiting: bool, draft: bool = True) -> None:
    deck = root / name / ".game-of-cards" / "deck"
    deck.mkdir(parents=True, exist_ok=True)
    card = deck / "alpha"
    card.mkdir(exist_ok=True)
    extra = ""
    if waiting:
        extra += "waiting_on: external\n"
    if draft:
        extra += "draft: true\n"
    (card / "README.md").write_text(CARD.format(title="alpha", extra=extra))
    engine.DECK_DIR = deck


def main() -> int:
    prev = engine.DECK_DIR
    failures: list[str] = []
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        try:
            # ---- shape 1: --waiting, whose default status resolves to `all` --
            build_deck(root, "impeded", waiting=True)
            explicit = render(waiting=True, status_flag="open")
            default = render(waiting=True)

            print("shape 1 — an impeded draft, queried two ways")
            print(f"  goc --waiting --status open : {explicit}")
            print(f"  goc --waiting               : {default}")

            # The card really is only hidden by its draft flag: publish it and
            # the very same default query lists it.
            build_deck(root, "published", waiting=True, draft=False)
            after_publish = render(waiting=True)
            listed = [ln for ln in after_publish.splitlines() if ln.startswith("alpha")]
            print(f"  ...after `goc publish`      : {listed[0] if listed else after_publish}")

            if CLAUSE not in explicit:
                failures.append("shape 1: explicit --status open lost the clause too")
            if CLAUSE in default:
                failures.append("shape 1 FIXED: default --waiting now names the draft")
            if "alpha" not in after_publish:
                failures.append("shape 1: publishing did not surface the card")

            # ---- shape 2: --ready with an explicit --status all --------------
            build_deck(root, "ready", waiting=False)
            ready_open = render(ready=True)
            ready_all = render(ready=True, status_flag="all")

            print()
            print("shape 2 — a queueable draft, queried two ways")
            print(f"  goc --ready                 : {ready_open}")
            print(f"  goc --ready --status all    : {ready_all}")

            if CLAUSE not in ready_open:
                failures.append("shape 2: plain --ready lost the clause too")
            if CLAUSE in ready_all:
                failures.append("shape 2 FIXED: --status all now names the draft")
        finally:
            engine.DECK_DIR = prev

    print()
    if failures:
        for line in failures:
            print(f"[FIXED/UNEXPECTED] {line}")
        print("defect no longer reproduces")
        return 1
    print("[DEFECT] adding `--status all` (or letting --waiting resolve it) "
          "silently drops a true hidden-draft clause")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
