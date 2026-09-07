"""Reproduce: `goc migrate-list-style` reports (and rewrites) far more than list style.

The verb's user-facing scope is the four relation-edge list fields. Its
subparser help and its docstring both read "Re-emit every card to convert
relation-edge lists (advances/advanced_by/supersedes/superseded_by) to
block-style", and its no-op line reads "All cards already use block-style
for advances/advanced_by/supersedes/superseded_by — nothing to do."

But the predicate that decides which cards to rewrite is a *full* canonical
re-emit comparison — `emit_frontmatter(fm, body=body) != original` — so a
card differing from canonical form in ANY emitter-controlled way (scalar
quoting, block-scalar shape, the blank line after the frontmatter) is
reported under a heading that promises relation-list reformatting, and the
`--dry-run` card list gives the reader no way to tell the two apart.

Builds temporary decks from three cards:
  - card-alpha: canonical relation lists, bare `summary` the emitter
    would quote.
  - card-beta: canonical relation lists, no blank line after `---`.
  - card-gamma (control): inline-flow `advances`, i.e. genuine
    block-style drift the verb was introduced to migrate.

CHECK 1 — on a deck holding ONLY the two non-list-style drifters, the verb
must not report cards to rewrite without saying what actually differs.
CHECK 2 — the control must still be reported, so the fix cannot be
"report nothing".

Exits 1 while the defect fires, 0 once the report is actionable — either
the predicate is narrowed to the relation lists, or each reported card
names the non-relation-list reason it was picked.
"""

from __future__ import annotations

import os
import re
import subprocess
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


REPO_ROOT = _repo_root()
sys.path.insert(0, str(REPO_ROOT))

from goc.engine import _BLOCK_LIST_FIELDS, emit_frontmatter, parse_frontmatter  # noqa: E402

RELATION_FIELDS = tuple(_BLOCK_LIST_FIELDS)

# Canonical relation lists (empty -> `[]`) and a bare `summary` carrying a
# `: ` the emitter quotes. Nothing here is relation-list drift.
QUOTING_DRIFT = """---
title: card-alpha
summary: the board hard-caps a label: eight characters is a vestige
status: open
stage: null
contribution: low
created: "2026-01-01T00:00:00Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [ ] MECHANICAL: nothing
---

# card-alpha

Body.
"""

# Canonical relation lists and a summary the emitter leaves bare; the only
# drift is the missing blank line between the frontmatter and the body.
SPACING_DRIFT = """---
title: card-beta
summary: canonical everywhere except the blank line before the body
status: open
stage: null
contribution: low
created: "2026-01-01T00:00:00Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [ ] MECHANICAL: nothing
---
# card-beta

Body.
"""

# The control: a genuine inline-flow relation list, the migration's target.
REAL_LIST_DRIFT = """---
title: card-gamma
summary: "an inline-flow advances list, which is real block-style drift"
status: open
stage: null
contribution: low
created: "2026-01-01T00:00:00Z"
closed_at: null
human_gate: none
advances: [card-alpha]
advanced_by: []
tags: [bug]
definition_of_done: |
  - [ ] MECHANICAL: nothing
---

# card-gamma

Body.
"""


def _write_deck(root: Path, cards: dict) -> Path:
    deck = root / ".game-of-cards" / "deck"
    deck.mkdir(parents=True)
    for name, text in cards.items():
        d = deck / name
        d.mkdir()
        (d / "README.md").write_text(text)
        (d / "log.md").write_text("")
    return deck


def _dry_run(root: Path) -> str:
    env = dict(os.environ, PYTHONPATH=str(REPO_ROOT))
    proc = subprocess.run(
        [sys.executable, "-m", "goc.cli", "migrate-list-style", "--dry-run"],
        cwd=root, env=env, capture_output=True, text=True,
    )
    return proc.stdout + proc.stderr


def _reported(output: str) -> list:
    """Card names the dry run lists as would-be rewrites."""
    return re.findall(r"^ {2}(\S+)", output, re.MULTILINE)


def _labelled(output: str) -> dict:
    """{card name: the reason the report gives for picking it}."""
    return dict(re.findall(r"^ {2}(\S+)\s+[-\u2014]\s+(.+?)\s*$", output, re.MULTILINE))


def _relation_list_drift(readme: Path) -> bool:
    """True iff re-emitting changes how a RELATION-EDGE LIST renders."""
    original = readme.read_text()
    fm, body = parse_frontmatter(original)
    rewritten = emit_frontmatter(fm, body=body)

    def relation_lines(text: str) -> list:
        keep, active = [], False
        for line in text.splitlines():
            if re.match(r"^\S+:", line):
                active = line.split(":", 1)[0] in RELATION_FIELDS
            if active:
                keep.append(line)
        return keep

    return relation_lines(original) != relation_lines(rewritten)


def main() -> int:
    failures = []

    # ---- CHECK 1: a deck with zero relation-list drift ----
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        deck = _write_deck(root, {
            "card-alpha": QUOTING_DRIFT,
            "card-beta": SPACING_DRIFT,
        })
        out = _dry_run(root)
        reported = _reported(out)
        on_disk = sorted(p.name for p in deck.iterdir())
        drifted = [c for c in on_disk if _relation_list_drift(deck / c / "README.md")]

        print("CHECK 1 - deck with NO relation-edge-list drift")
        print(f"  cards on disk ............ {on_disk}")
        print(f"  relation-list drifters ... {drifted}")
        print(f"  verb reports to rewrite .. {reported}")
        print("  verb output:")
        for line in out.rstrip().splitlines():
            print(f"    | {line}")

        # The report is honest if it either picked nothing (predicate narrowed
        # to the relation lists) or told the reader what actually differs.
        # The report is honest if it either picked nothing (predicate narrowed
        # to the relation lists) or told the reader, per card, what differs.
        labelled = _labelled(out)
        print(f"  reasons given per card ... {labelled}")
        unlabelled = [c for c in reported if c not in labelled]
        if reported and unlabelled:
            failures.append(
                f"CHECK 1: {len(reported)} card(s) reported as list-style migrations "
                f"while {len(drifted)} have relation-list drift, and {len(unlabelled)} "
                f"of them carry no reason: {unlabelled}"
            )
        # A reason naming a relation-edge field for these cards would be a
        # second lie - none of them has relation-list drift.
        for card, reason in labelled.items():
            if any(field in reason for field in RELATION_FIELDS):
                failures.append(
                    f"CHECK 1: {card} has no relation-list drift, but the report "
                    f"blames a relation-edge field: {reason!r}"
                )

    # ---- CHECK 2: the control must still be reported ----
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_deck(root, {"card-gamma": REAL_LIST_DRIFT})
        out = _dry_run(root)
        reported = _reported(out)
        print()
        print("CHECK 2 - control: genuine inline-flow relation list")
        print(f"  verb reports to rewrite .. {reported}")
        if "card-gamma" not in reported:
            failures.append(
                "CHECK 2: the control card with genuine block-style drift was NOT "
                "reported - the fix must not be 'report nothing'"
            )

    print()
    if failures:
        for f in failures:
            print(f"[FAIL] {f}")
        return 1
    print("[PASS] migrate-list-style's report is actionable.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
