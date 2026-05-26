"""Demonstrate the three coordinating-card shapes against the engine.

Shape 1 — canonical aggregation epic: child.advances:[epic]
    → advanced-by-closed PASS on the child (no advanced_by entries)
    → BACKWARDS_EPIC_EDGE lint: silent (epic.advances is empty)

Shape 2 — backwards aggregation epic: epic.advances:[children]
    → advanced-by-closed FAIL on each child (each child reads as gated
      on the open epic that is meant to outlive it)
    → BACKWARDS_EPIC_EDGE lint: fires on the epic and names the fix

Shape 3 — governing cluster encoded with an edge (both directions
shown to be broken): a decision card and its instances. Either edge
direction mismodels the relationship; the faithful encoding is a
shared tag with no edge.

The reproducer constructs the cards in a temp directory and calls the
engine's pure functions directly — no `goc` subprocess, no committed
deck mutation.
"""

import sys
import tempfile
import textwrap
from datetime import datetime, timezone
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


sys.path.insert(0, str(_repo_root()))

import goc.engine as engine  # noqa: E402


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_card(
    deck: Path,
    title: str,
    *,
    contribution: str = "medium",
    status: str = "open",
    human_gate: str = "none",
    advances: list[str] | None = None,
    advanced_by: list[str] | None = None,
    dod_ticked: bool = True,
) -> None:
    """Drop a minimal valid card under deck/<title>/."""
    advances = advances or []
    advanced_by = advanced_by or []
    card_dir = deck / title
    card_dir.mkdir(parents=True, exist_ok=True)
    fm = [
        "---",
        f"title: {title}",
        f"summary: {title} (reproducer fixture)",
        f"status: {status}",
        "stage: null",
        f"contribution: {contribution}",
        f"created: {_now()}",
        "closed_at: null",
        f"human_gate: {human_gate}",
    ]
    if advances:
        fm.append("advances:")
        for a in advances:
            fm.append(f"  - {a}")
    else:
        fm.append("advances: []")
    if advanced_by:
        fm.append("advanced_by:")
        for a in advanced_by:
            fm.append(f"  - {a}")
    else:
        fm.append("advanced_by: []")
    fm.append("tags: []")
    fm.append("definition_of_done: |")
    mark = "x" if dod_ticked else " "
    fm.append(f"  - [{mark}] reproducer placeholder")
    fm.append("---")
    fm.append("")
    fm.append(f"# {title}")
    fm.append("")
    (card_dir / "README.md").write_text("\n".join(fm) + "\n")
    (card_dir / "log.md").write_text("")


def _load(deck: Path) -> list:
    """Load every card under `deck/` using the engine's parser."""
    engine.DECK_DIR = deck
    return engine.load_all_cards()


def shape_canonical_passes_clean() -> None:
    print("=" * 72)
    print("SHAPE 1 — canonical aggregation: child.advances:[epic]")
    print("=" * 72)
    with tempfile.TemporaryDirectory() as tmp:
        deck = Path(tmp)
        _write_card(deck, "epic-c1", contribution="high", advanced_by=["child-c1"])
        _write_card(deck, "child-c1", contribution="medium", advances=["epic-c1"])
        cards = _load(deck)
        by_title = {c.title: c for c in cards}

        child = by_title["child-c1"]
        passed, summary = engine._run_derived_check(
            {"name": "advanced-by-closed"}, child, cards, _now()
        )
        print(f"  attest advanced-by-closed on child-c1: {'PASS' if passed else 'FAIL'} — {summary}")

        lint = engine.validate_epic_edge_direction(cards)
        print(f"  BACKWARDS_EPIC_EDGE warnings: {len(lint)} (expected 0)")
        assert passed, "canonical shape: child should pass advanced-by-closed"
        assert not lint, f"canonical shape: lint should be silent; got {lint}"


def shape_backwards_fires_lint_and_attest_fail() -> None:
    print()
    print("=" * 72)
    print("SHAPE 2 — backwards aggregation: epic.advances:[children]")
    print("=" * 72)
    with tempfile.TemporaryDirectory() as tmp:
        deck = Path(tmp)
        _write_card(
            deck,
            "epic-b1",
            contribution="high",
            advances=["child-b1", "child-b2"],
        )
        _write_card(deck, "child-b1", contribution="medium", advanced_by=["epic-b1"])
        _write_card(deck, "child-b2", contribution="low", advanced_by=["epic-b1"])
        cards = _load(deck)
        by_title = {c.title: c for c in cards}

        child = by_title["child-b1"]
        passed, summary = engine._run_derived_check(
            {"name": "advanced-by-closed"}, child, cards, _now()
        )
        print(f"  attest advanced-by-closed on child-b1: {'PASS' if passed else 'FAIL'} — {summary}")

        lint = engine.validate_epic_edge_direction(cards)
        print(f"  BACKWARDS_EPIC_EDGE warnings: {len(lint)} (expected 1, naming epic-b1)")
        for w in lint:
            print(f"    {w.message}")
        assert not passed, "backwards shape: child should FAIL advanced-by-closed"
        assert len(lint) == 1 and lint[0].card == "epic-b1", (
            f"backwards shape: lint should fire once on epic-b1; got {lint}"
        )

        print()
        print("  → Fix by flipping the edge (goc unadvance + goc advance):")
        _write_card(
            deck,
            "epic-b1",
            contribution="high",
            advances=[],
            advanced_by=["child-b1", "child-b2"],
        )
        _write_card(deck, "child-b1", contribution="medium", advances=["epic-b1"])
        _write_card(deck, "child-b2", contribution="low", advances=["epic-b1"])
        cards = _load(deck)
        by_title = {c.title: c for c in cards}
        child = by_title["child-b1"]
        passed, summary = engine._run_derived_check(
            {"name": "advanced-by-closed"}, child, cards, _now()
        )
        lint = engine.validate_epic_edge_direction(cards)
        print(f"    after flip: attest on child-b1 = {'PASS' if passed else 'FAIL'} ({summary})")
        print(f"    after flip: BACKWARDS_EPIC_EDGE warnings = {len(lint)}")
        assert passed, "after flip: child should PASS advanced-by-closed"
        assert not lint, "after flip: lint should be silent"


def shape_govern_cluster_either_edge_is_wrong() -> None:
    print()
    print("=" * 72)
    print("SHAPE 3 — governing cluster: decision card + instance cluster")
    print("=" * 72)

    # Edge direction A: decision.advances:[instances] → instances deadlock
    # behind the open decision.
    print()
    print("  3a) decision.advances:[instances]")
    with tempfile.TemporaryDirectory() as tmp:
        deck = Path(tmp)
        _write_card(
            deck,
            "decision-g1",
            contribution="high",
            human_gate="decision",
            advances=["instance-g1", "instance-g2"],
        )
        _write_card(
            deck,
            "instance-g1",
            contribution="medium",
            advanced_by=["decision-g1"],
        )
        _write_card(
            deck,
            "instance-g2",
            contribution="low",
            advanced_by=["decision-g1"],
        )
        cards = _load(deck)
        by_title = {c.title: c for c in cards}
        instance = by_title["instance-g1"]
        passed, summary = engine._run_derived_check(
            {"name": "advanced-by-closed"}, instance, cards, _now()
        )
        lint = engine.validate_epic_edge_direction(cards)
        print(f"    attest on instance-g1: {'PASS' if passed else 'FAIL'} — {summary}")
        print(f"    BACKWARDS_EPIC_EDGE on decision-g1: {len(lint)} warning(s)")
        for w in lint:
            print(f"      {w.message}")
        print("    → instances deadlocked; lint recommends shared tag (decision gate)")
        assert not passed, "edge dir A: instances should be gated on open decision"
        assert (
            len(lint) == 1
            and lint[0].card == "decision-g1"
            and "shared tag" in lint[0].detail
        ), "edge dir A: lint should fire on decision and recommend a tag"

    # Edge direction B: instance.advances:[decision] → decision blocked
    # behind every instance, contradicting the decision's own DoD (closes
    # when *decided*).
    print()
    print("  3b) instance.advances:[decision]")
    with tempfile.TemporaryDirectory() as tmp:
        deck = Path(tmp)
        _write_card(
            deck,
            "decision-g2",
            contribution="high",
            human_gate="decision",
            advanced_by=["instance-h1", "instance-h2"],
        )
        _write_card(
            deck,
            "instance-h1",
            contribution="medium",
            advances=["decision-g2"],
        )
        _write_card(
            deck,
            "instance-h2",
            contribution="low",
            advances=["decision-g2"],
        )
        cards = _load(deck)
        by_title = {c.title: c for c in cards}
        decision = by_title["decision-g2"]
        passed, summary = engine._run_derived_check(
            {"name": "advanced-by-closed"}, decision, cards, _now()
        )
        print(f"    attest on decision-g2: {'PASS' if passed else 'FAIL'} — {summary}")
        print("    → decision can't close until every instance does — contradicts its DoD")
        assert not passed, "edge dir B: decision should be gated on its instances"

    # Faithful encoding: shared tag, no edge in either direction.
    print()
    print("  3c) shared tag, no edge (faithful encoding)")
    with tempfile.TemporaryDirectory() as tmp:
        deck = Path(tmp)
        _write_card(
            deck,
            "decision-g3",
            contribution="high",
            human_gate="decision",
        )
        _write_card(deck, "instance-i1", contribution="medium")
        _write_card(deck, "instance-i2", contribution="low")
        cards = _load(deck)
        by_title = {c.title: c for c in cards}
        instance = by_title["instance-i1"]
        passed, summary = engine._run_derived_check(
            {"name": "advanced-by-closed"}, instance, cards, _now()
        )
        lint = engine.validate_epic_edge_direction(cards)
        print(f"    attest on instance-i1: {'PASS' if passed else 'FAIL'} — {summary}")
        print(f"    BACKWARDS_EPIC_EDGE warnings: {len(lint)} (expected 0)")
        assert passed, "tag encoding: instance should pass — no advanced_by entries"
        assert not lint, "tag encoding: lint should be silent (no edges)"


def main() -> None:
    shape_canonical_passes_clean()
    shape_backwards_fires_lint_and_attest_fail()
    shape_govern_cluster_either_edge_is_wrong()
    print()
    print("All three shapes behaved as documented.")


if __name__ == "__main__":
    main()
