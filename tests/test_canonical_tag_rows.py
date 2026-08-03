"""Regression guard for the `Skill(card-schema)` § "Canonical tags" table.

Twice the table gave a *judgment* property a text predicate, and twice a
refine-deck sweep measured most of the tagged population as mistagged — the
`meta-fix` row on 2026-07-08 (37 of 45) and the `story` row on 2026-07-27 (67
of 102). Both were resolved by widening the search surface, and on 2026-08-03
`meta-fix` failed a third time on cards no widening could reach: an umbrella is
filed because a family was noticed, and neither a literal in the prose nor a
wired roster follows from that.

So the table now declares a `check` class per row, and this suite is what keeps
that classification honest:

- every row declares `state` or `judgment`, and the table's tag set matches the
  schema enum, so a new tag cannot arrive unclassified;
- every `state` row has a scorer here and every scorer has a `state` row, so
  reclassifying a row in the doc without moving its scorer fails loudly;
- the live tagged population satisfies every `state` row, so the next drift is
  caught by CI instead of by the next hygiene pass;
- the sweep's action on a non-firing row stays `report`, never `strip` — the
  half that makes a misclassification recoverable rather than destructive.

Per the card `static-source-guards-never-prove-they-can-catch-an-offender`, a
guard must demonstrate it can catch an offender rather than merely reporting a
clean tree. `test_each_state_scorer_rejects_an_offender` and the `OFFENDERS`
table are that demonstration: a scorer that silently stopped discriminating
fails them instead of passing quietly on a deck that happens to comply.
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from goc import engine  # noqa: E402

SKILL = ROOT / "goc" / "templates" / "skills" / "card-schema" / "SKILL.md"
REFINE_SKILL = ROOT / "goc" / "templates" / "skills" / "refine-deck" / "SKILL.md"
REFINE_REFERENCE = ROOT / "goc" / "templates" / "skills" / "refine-deck" / "reference.md"

CHECK_CLASSES = {"state", "judgment"}

# Wording that prescribed the destructive action. Each phrase shipped in the
# refine-deck skill before 2026-08-03 and turned a non-firing predicate into a
# frontmatter edit; the sweep now reports instead.
STRIP_INSTRUCTIONS = [
    "strip only where a row plainly fails",
    "mistagged, strip",
    "→ stripped tag",
]


def tag_rows() -> dict[str, str]:
    """Parse the "Canonical tags" table into {tag: check-class}.

    The table is `| tag | applies iff | check |`. Rows are matched on the
    leading backticked tag so the prose column may contain pipes-free markdown
    freely; a malformed row surfaces as a missing tag rather than a crash.
    """
    text = SKILL.read_text()
    start = text.index("## Canonical tags")
    next_heading = text.find("\n## ", start + 1)
    section = text[start:] if next_heading == -1 else text[start:next_heading]

    rows: dict[str, str] = {}
    row_re = re.compile(r"^\|\s*`([a-z0-9-]+)`\s*\|(.*)\|([^|]*)\|\s*$")
    for line in section.splitlines():
        match = row_re.match(line)
        if match:
            rows[match.group(1)] = match.group(3).strip()
    return rows


# --- `state` row scorers -------------------------------------------------
#
# One per `state` row, transcribing that row and nothing else. A row is only
# `state` when its satisfier is readable out of frontmatter, edge arrays, or
# files in the card directory, which is what keeps these short enough to audit
# against the table by eye.


def _edge_field(card, field: str) -> list[str]:
    value = card.frontmatter.get(field) or []
    return [str(x) for x in value] if isinstance(value, list) else []


def _score_bug(card) -> bool:
    """`bug` | not `epic` and not `story`."""
    return not ({"epic", "story"} & set(card.tags or []))


def _score_epic(card) -> bool:
    """`epic` | multiple cards block its closure (>=2 `advanced_by`) OR carry
    its epic-grouping tag."""
    if len(_edge_field(card, "advanced_by")) >= 2:
        return True
    shipped = engine.load_schema().canonical_tags
    return bool(set(card.tags or []) - shipped - {"epic"})


def _score_unverified(card) -> bool:
    """`unverified` | no working `reproduce.py` AND tagged at filing.

    Only the first clause is card state; "tagged at filing" needs git history
    and is left to the author. A present-but-empty script is not working.
    """
    script = Path(card.path) / "reproduce.py"
    return not (script.exists() and script.stat().st_size > 0)


STATE_SCORERS = {
    "bug": _score_bug,
    "epic": _score_epic,
    "unverified": _score_unverified,
}


class _FakeCard:
    """Minimal stand-in carrying only what the `state` scorers read."""

    def __init__(self, tags, frontmatter=None, path=None):
        self.tags = tags
        self.frontmatter = frontmatter or {}
        self.path = path or "/nonexistent"


# Each entry must be REJECTED by its scorer. These are the shapes the sweep
# exists to surface, so a scorer that stopped discriminating fails here.
OFFENDERS = [
    ("bug carrying epic", "bug", _FakeCard(["bug", "epic"])),
    ("bug carrying story", "bug", _FakeCard(["bug", "story"])),
    ("epic with one blocking child", "epic", _FakeCard(["epic"], {"advanced_by": ["a"]})),
    ("epic with zero edges", "epic", _FakeCard(["epic"], {"advanced_by": []})),
    ("epic with a non-list edge field", "epic", _FakeCard(["epic"], {"advanced_by": "a"})),
]


def live_cards():
    return [c for c in engine.load_all_cards() if c.status not in engine.TERMINAL_STATUSES]


class CanonicalTagRowsTest(unittest.TestCase):
    def test_every_row_declares_a_check_class(self) -> None:
        rows = tag_rows()
        self.assertTrue(rows, msg=f"{SKILL.relative_to(ROOT)}: parsed no tag rows")
        for tag, check in sorted(rows.items()):
            self.assertIn(
                check,
                CHECK_CLASSES,
                msg=(
                    f"`{tag}` row declares check={check!r}; must be one of "
                    f"{sorted(CHECK_CLASSES)}. A row whose satisfier is not readable "
                    "out of frontmatter, edges, or card files is `judgment`."
                ),
            )

    def test_table_covers_the_schema_enum(self) -> None:
        rows = set(tag_rows())
        shipped = set(engine.load_schema().canonical_tags)
        self.assertEqual(
            rows,
            shipped,
            msg=(
                "the canonical-tags table and goc/schema.yaml's enum disagree: "
                f"table-only={sorted(rows - shipped)}, enum-only={sorted(shipped - rows)}. "
                "A tag with no row cannot be swept; a row with no tag cannot be applied."
            ),
        )

    def test_state_rows_and_scorers_are_in_lockstep(self) -> None:
        state_rows = {t for t, check in tag_rows().items() if check == "state"}
        self.assertEqual(
            state_rows,
            set(STATE_SCORERS),
            msg=(
                "`state` rows in the table and scorers in this file disagree: "
                f"unscored={sorted(state_rows - set(STATE_SCORERS))}, "
                f"stale={sorted(set(STATE_SCORERS) - state_rows)}. Promoting a row to "
                "`state` requires a scorer here; demoting it to `judgment` requires "
                "removing one."
            ),
        )

    def test_live_cards_satisfy_every_state_row(self) -> None:
        """The measurement the three predecessor cards had to make by hand.

        Scoped to live cards: terminal cards are the record axis, no sweep
        touches them, and three closed epics predate the >=2-children rule.
        """
        cards = live_cards()
        self.assertGreater(len(cards), 100, msg="deck did not load; scoring would be vacuous")

        failures = []
        for tag, scorer in sorted(STATE_SCORERS.items()):
            for card in cards:
                if tag in (card.tags or []) and not scorer(card):
                    failures.append(f"{card.title}: carries `{tag}` but fails its row")
        self.assertEqual(
            [],
            failures,
            msg=(
                "live cards carry a `state` tag whose row they cannot satisfy:\n  "
                + "\n  ".join(failures)
                + "\nEither the card is mistagged or the row is wrong — pick one "
                "deliberately. Do not widen the row to make this pass; that is the "
                "move that failed three times (Skill(card-schema) reference.md "
                '§ "Why rows split into `state` and `judgment`").'
            ),
        )

    def test_each_state_scorer_rejects_an_offender(self) -> None:
        """A guard that only ever reports a clean tree has two passing states."""
        for label, tag, card in OFFENDERS:
            with self.subTest(offender=label):
                self.assertFalse(
                    STATE_SCORERS[tag](card),
                    msg=f"the `{tag}` scorer accepted {label} — it no longer discriminates",
                )

    def test_each_state_scorer_accepts_a_compliant_card(self) -> None:
        self.assertTrue(_score_bug(_FakeCard(["bug", "api-contract"])))
        self.assertTrue(_score_epic(_FakeCard(["epic"], {"advanced_by": ["a", "b"]})))
        self.assertTrue(_score_unverified(_FakeCard(["unverified"], path="/nonexistent")))

    def test_meta_fix_is_a_judgment_row(self) -> None:
        """The specific regression: `meta-fix` asserts scope, not a literal.

        An umbrella is named by shape and wires its roster later or never, so
        every text-or-edge predicate for this row is unsatisfiable at filing
        time and a compliant sweep aimed at exactly the umbrellas the tag exists
        to group.
        """
        self.assertEqual(
            "judgment",
            tag_rows().get("meta-fix"),
            msg=(
                "`meta-fix` is back to a scorable predicate. Its satisfier is what the "
                "card is about, which no literal or edge implies; scoring it strips "
                "umbrellas. See Skill(card-schema) reference.md § 'Why rows split into "
                "`state` and `judgment`'."
            ),
        )

    def test_sweep_does_not_strip_on_a_non_firing_row(self) -> None:
        for path in (REFINE_SKILL, REFINE_REFERENCE):
            text = path.read_text()
            for phrase in STRIP_INSTRUCTIONS:
                self.assertNotIn(
                    phrase,
                    text,
                    msg=(
                        f"{path.relative_to(ROOT)}: {phrase!r} makes a non-firing "
                        "predicate delete curated grouping. The documented action is "
                        "report; stripping is a per-card judgment, never mechanical."
                    ),
                )

        skill = REFINE_SKILL.read_text()
        start = skill.index("### Tags without firing predicates")
        end = skill.index("\n### ", start + 1)
        self.assertIn(
            "Report, never strip",
            skill[start:end],
            msg=(
                f"{REFINE_SKILL.relative_to(ROOT)}: the tag sweep no longer states its "
                "non-destructive action, so the next reader has no instruction to follow."
            ),
        )


if __name__ == "__main__":
    unittest.main()
