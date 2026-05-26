"""Reproduce: a mutual supersession pair (A.superseded_by=[B],
B.superseded_by=[A], both status: superseded) passes every goc
validator, yet a forward walk through `superseded_by` cycles forever.

The end-state built here is exactly what
    goc status A superseded --by B
    goc status B superseded --by A
produces: at the second call B.status is still `open` (only B.supersedes
was touched by the first call), so the terminal-status guard never fires
and nothing rejects superseding back.

Exit 0 == validators reject/flag the cycle OR the forward walk terminates
          (defect fixed).
Exit 1 == validators pass clean AND the forward walk cycles (defect fires).
"""
import sys
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


def _card_fm(title, successor):
    return {
        "title": title,
        "summary": "x",
        "contribution": "medium",
        "status": "superseded",
        "stage": None,
        "created": "2026-05-26",
        "closed_at": "2026-05-26",
        "human_gate": "none",
        "advances": [],
        "advanced_by": [],
        "superseded_by": [successor],
        "supersedes": [successor],
        "tags": [],
        "definition_of_done": "- [ ] x\n",
    }


def _walk_has_cycle(by_title, start):
    seen = set()
    cur = start
    while cur is not None:
        if cur in seen:
            return True
        seen.add(cur)
        nxt = by_title.get(cur)
        if nxt is None:
            return False
        sb = nxt.frontmatter.get("superseded_by") or []
        cur = sb[0] if sb else None
    return False


with TemporaryDirectory() as d:
    deck = Path(d) / "deck"
    deck.mkdir()
    for title, successor in [("aaa", "bbb"), ("bbb", "aaa")]:
        cdir = deck / title
        cdir.mkdir()
        (cdir / "README.md").write_text(
            engine.emit_frontmatter(_card_fm(title, successor), body="body\n")
        )
        (cdir / "log.md").write_text("")

    engine.DECK_DIR = deck
    schema = engine.load_schema()
    cards = engine.load_all_cards()
    all_titles = {c.title for c in cards}

    errors = []
    for c in cards:
        errors += engine.validate_card(c, schema, all_titles)
    errors += engine.detect_advance_cycles(cards)
    errors += engine.validate_bidirectional_edges(cards)
    errors += engine.validate_supersedes_targets(cards)

    by_title = {c.title: c for c in cards}
    cycle = _walk_has_cycle(by_title, "aaa")

    print(f"cards built:           {sorted(all_titles)}")
    print(f"aaa.superseded_by:     {by_title['aaa'].frontmatter.get('superseded_by')}")
    print(f"bbb.superseded_by:     {by_title['bbb'].frontmatter.get('superseded_by')}")
    print(f"validator errors:      {errors}")
    print(f"forward-walk cycles:   {cycle}")
    print()

    if not errors and cycle:
        print("DEFECT: validators pass clean but the superseded_by walk cycles")
        sys.exit(1)
    print("OK: cycle is rejected/flagged or the walk terminates")
    sys.exit(0)
