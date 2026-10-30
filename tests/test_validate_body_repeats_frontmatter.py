"""`goc validate` warns when a card body carries a copy of card text.

A rewrite that locates its edit in the whole README instead of in the body
splices the frontmatter into the body. The 2026-08-24 hygiene pass searched
for `## Decision required`, matched the DoD line quoting it first, and left a
DoD fragment, the `---` closer and a stale second body in
`goc-waiting-filter-drifts-from-engine-on-elapsed-and-bare-waits` for two months
while `goc validate` stayed green. The advisory `BODY_REPEATS_FRONTMATTER`
class reports the shapes only such a copy produces, outside fenced code blocks.

Per `static-source-guards-never-prove-they-can-catch-an-offender`, the check
must prove it catches real offenders, not only report a clean deck:
`HISTORICAL_OFFENDERS` holds both bodies the check found, as they sat on disk.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from goc import engine  # noqa: E402
from goc.engine import Card, frontmatter_copy_lines, validate_body_repeats_frontmatter  # noqa: E402

CLASS = "BODY_REPEATS_FRONTMATTER"

# The glued region of goc-waiting-filter-drifts-from-engine-on-elapsed-and-bare-waits
# at e8449764, verbatim; the unchanged sections between the two H1s are elided.
SPLICED_DECISION_REWRITE = (
    "\n# `goc --waiting` filter drifts from the engine on elapsed and bare waits\n"
    "\n"
    "## Reachability path\n"
    "\n"
    "Kept here because it is the reachability record for the closed defect.\n"
    "\n"
    '## Decision required") is recorded in `log.md` with the principle invoked.\n'
    "  - [ ] MECHANICAL: `--waiting` help text in `_build_parser` (`engine.py:2545-2546`) "
    "reads consistently with the chosen interpretation.\n"
    "  - [ ] PROCESS: `uv run goc validate` clean; `uv run python -m unittest "
    "discover -s tests` green.\n"
    "---\n"
    "\n"
    "# `goc --waiting` filter drifts from the engine on elapsed and bare waits\n"
    "\n"
    "## Location\n"
)

# The head of block-scalar-parser-collapses-whitespace-only-content-lines' body
# from 83c1408d to its 2026-10-30 restore, verbatim: a re-emit had dropped the
# H1, every section before a pasted reproducer output and that output's opening
# fence, so the body opened on the output's tail. The sections after the stray
# closing fence are elided.
DROPPED_BODY_TAIL = (
    "\n"
    "title: x\n"
    "summary: |-\n"
    "  first line\n"
    "     \n"
    "  third line\n"
    "status: open\n"
    "contribution: medium\n"
    "human_gate: none\n"
    "tags: [bug]\n"
    "advances: []\n"
    "advanced_by: []\n"
    "---\n"
    "\n"
    "=== round-trip of summary ===\n"
    "in : 'first line\\n   \\nthird line'\n"
    "out: 'first line\\n   \\nthird line'\n"
    "match: True\n"
    "\n"
    "OK: block-scalar round-trip is lossless.\n"
    "```\n"
)

HISTORICAL_OFFENDERS = {
    "spliced decision rewrite (e8449764)": SPLICED_DECISION_REWRITE,
    "dropped body (83c1408d)": DROPPED_BODY_TAIL,
}


def _card(title: str, body: str, *, status: str = "open") -> Card:
    return Card(
        title=title,
        path=Path("/nonexistent") / title,
        frontmatter={"title": title, "status": status},
        body=body,
        dod_open=0,
        dod_done=0,
    )


class FrontmatterCopyLinesTest(unittest.TestCase):
    def test_historical_offenders_are_caught(self) -> None:
        for name, body in HISTORICAL_OFFENDERS.items():
            with self.subTest(name):
                self.assertNotEqual([], frontmatter_copy_lines(body))

    def test_spliced_rewrite_reports_the_dod_fragment_and_the_second_h1(self) -> None:
        hits = frontmatter_copy_lines(SPLICED_DECISION_REWRITE)
        self.assertEqual(3, len(hits))
        self.assertTrue(hits[0].startswith("  - [ ] MECHANICAL: "))
        self.assertTrue(hits[1].startswith("  - [ ] PROCESS: "))
        self.assertTrue(hits[2].startswith("# `goc --waiting`"))

    def test_key_lines_are_reported(self) -> None:
        for line in (
            "title: some-card",
            'title: "some-card"',
            "human_gate: decision",
            "definition_of_done: |",
            "definition_of_done: |-",
            "definition_of_done: |2+",
            "definition_of_done: |  ",
        ):
            with self.subTest(line):
                self.assertEqual([line], frontmatter_copy_lines(f"\n# t\n\n{line}\n"))

    def test_dod_items_at_the_block_indent_are_reported(self) -> None:
        for line in (
            "  - [ ] TDD: a test",
            "  - [x] EMPIRICAL: a measurement",
            "  - [X] MECHANICAL: an edit",
            "  - [ ] PROCESS: a step",
        ):
            with self.subTest(line):
                self.assertEqual([line], frontmatter_copy_lines(f"\n# t\n\n{line}\n"))

    def test_fenced_copies_stay_silent(self) -> None:
        copy = "title: x\ndefinition_of_done: |\n  - [ ] TDD: a test\n---\n# t\n"
        for opener, closer in (("```", "```"), ("```yaml", "```"), ("~~~", "~~~"), ("````", "````")):
            with self.subTest(opener):
                body = f"\n# t\n\n{opener}\n{copy}{closer}\n"
                self.assertEqual([], frontmatter_copy_lines(body))

    def test_prose_and_body_checklists_stay_silent(self) -> None:
        # Real lines from this repo's deck: wrapped prose opening with a field
        # name, and checklists that belong to the body rather than to a DoD.
        for line in (
            "status: **a card may be `status: active` AND carry `waiting_on`.** So the",
            "waiting_until: 2099-01-01`). Assert `card_is_ready(dependent) is True` and",
            "title: the card's title names the symptom, not the fix",
            "human_gate: decision cards are the ones a human must read",
            "definition_of_done (replace after decision):",
            "- [ ] TDD: a body checklist at column 0",
            "    - [ ] TDD: an indented code block",
            "  - [ ] an untagged nested checklist item",
            "## Decision required",
            "---",
        ):
            with self.subTest(line):
                self.assertEqual([], frontmatter_copy_lines(f"\n# t\n\n{line}\n"))

    def test_only_a_repeated_h1_is_reported(self) -> None:
        self.assertEqual([], frontmatter_copy_lines("\n# One\n\ntext\n\n# Two\n"))
        self.assertEqual(["# One"], frontmatter_copy_lines("\n# One\n\ntext\n\n# One\n"))

    def test_validator_checks_terminal_cards_too(self) -> None:
        for status in ("open", "active", "done", "disproved", "superseded"):
            with self.subTest(status):
                warnings = validate_body_repeats_frontmatter(
                    [_card("spliced-card", SPLICED_DECISION_REWRITE, status=status)]
                )
                self.assertEqual([(CLASS, "spliced-card")], [(w.klass, w.card) for w in warnings])

    def test_clean_body_yields_no_warning(self) -> None:
        body = "\n# clean-card\n\n## Location\n\n- `goc/engine.py`\n"
        self.assertEqual([], validate_body_repeats_frontmatter([_card("clean-card", body)]))


class ValidateCliTest(unittest.TestCase):
    """The warning reaches `goc validate`'s output and stays advisory."""

    def run_validate(self, cwd: Path) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
        env.pop("GOC_WORKTREE_DECK", None)
        return subprocess.run(
            [sys.executable, "-m", "goc.cli", "validate", "--quiet"],
            cwd=cwd,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def write_card(self, cwd: Path, title: str, body: str, *, status: str = "open") -> None:
        card_dir = cwd / ".game-of-cards" / "deck" / title
        card_dir.mkdir(parents=True)
        box = "x" if status == "done" else " "
        closed_at = '"2026-10-30T00:00:00Z"' if status == "done" else "null"
        (card_dir / "README.md").write_text(
            "---\n"
            f"title: {title}\n"
            'summary: "A scratch card."\n'
            f"status: {status}\n"
            "stage: null\n"
            "contribution: low\n"
            'created: "2026-10-30T00:00:00Z"\n'
            f"closed_at: {closed_at}\n"
            "human_gate: none\n"
            "advances: []\n"
            "advanced_by: []\n"
            "tags: [bug]\n"
            "definition_of_done: |\n"
            f"  - [{box}] PROCESS: scratch\n"
            "---\n" + body,
            encoding="utf-8",
        )
        (card_dir / "log.md").write_text("", encoding="utf-8")

    def test_spliced_bodies_warn_and_fenced_ones_do_not(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.write_card(cwd, "spliced-open-card", SPLICED_DECISION_REWRITE)
            self.write_card(cwd, "dropped-body-done-card", DROPPED_BODY_TAIL, status="done")
            self.write_card(
                cwd,
                "fenced-example-card",
                "\n# fenced-example-card\n\n```\ntitle: x\ndefinition_of_done: |\n"
                "  - [ ] TDD: shown, not live\n---\n```\n",
            )
            result = self.run_validate(cwd)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn(f"WARN {CLASS} spliced-open-card: 3 body line(s)", result.stderr)
        self.assertIn(f"WARN {CLASS} dropped-body-done-card: 2 body line(s)", result.stderr)
        self.assertIn("repair it from the README's git history", result.stderr)
        self.assertNotIn("fenced-example-card", result.stderr)


class ThisDeckTest(unittest.TestCase):
    """This repo's deck carries no spliced body. The check's first deck-wide
    run found two cards — one body lost in 83c1408d, one unfenced proposed DoD
    — so a regression here is a card a rewrite has damaged since."""

    def test_no_card_body_repeats_card_text(self) -> None:
        offenders = []
        for readme in sorted((ROOT / ".game-of-cards" / "deck").glob("*/README.md")):
            fm, body = engine.parse_frontmatter(readme.read_text(encoding="utf-8"))
            if fm and frontmatter_copy_lines(body):
                offenders.append(readme.parent.name)
        self.assertEqual([], offenders)


class RefineDeckNamesTheWarningTest(unittest.TestCase):
    """Skill(refine-deck) tells a hygiene pass to edit only the body and names
    the warning a whole-file edit trips; the name must stay the one the
    engine emits."""

    def test_skill_names_the_emitted_class(self) -> None:
        [warning] = validate_body_repeats_frontmatter(
            [_card("spliced-card", SPLICED_DECISION_REWRITE)]
        )
        skill = (ROOT / "goc" / "templates" / "skills" / "refine-deck" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertTrue(
            f"`{warning.klass}`" in skill,
            f"refine-deck SKILL.md does not name `{warning.klass}`",
        )


if __name__ == "__main__":
    unittest.main()
