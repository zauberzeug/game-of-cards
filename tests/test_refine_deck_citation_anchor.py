"""Regression guard: refine-deck's citation repair survives a SECOND pass.

The hygiene pass repairs a rotted `file:line` cite by reading the cited
line's text at some earlier commit (the ANCHOR) and relocating that text
in HEAD. Which commit to anchor at is the whole question, and it only
becomes visible on the second pass: while a cite still carries the number
the card was filed with, the card's creating commit and the commit that
wrote the number are the same commit. Once a repair pass has rewritten
the number — its entire job — they diverge, and reading the new number at
the creating commit resolves whatever unrelated code sat at that offset
back then. The recipe then finds that text elsewhere in HEAD and moves
the cite onto it, passing its own uniqueness guard because the wrong
anchor is genuinely unique.

Measured on this project's deck one week after its first repair pass, the
creating-commit anchor would have moved 165 of 850 correct open-card
cites onto unrelated code (the card
`second-citation-repair-pass-moves-correct-cites-onto-unrelated-code`
carries the replay). That measurement can only ever be taken on a deck
that has already been repaired once, so the fixture below builds the
two-pass shape directly: a cite is filed, drifts, is repaired, and drifts
again. Both recipes agree on every commit but the last.

The recipe under test is the one the skill PROSE specifies — parsed out
of `SKILL.md` — not a copy of it, so the guard fails when the shipped
instructions regress, which is where the defect lived.

The same file also guards the recipe's SCOPE, for the same reason at one
remove: `citation-repair-pass-has-no-rule-for-cites-inside-fenced-code-blocks`
found that the recipe said whether a number could be relocated and
nothing about whether it should be, so a cite inside a fenced block was
left to each pass's invention. The two defensible inventions — every
fenced cite is evidence, skip it; a fence means nothing, rewrite it —
disagree on every fenced cite in the deck, and each is wrong on one of
the two shapes a fence holds (49 comment labels that must be repaired,
17 pasted-output records that must not). Prose that names the fence
without naming both dispositions leaves the invention open, so the
guard classifies rather than greps.
"""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "goc" / "templates" / "skills" / "refine-deck" / "SKILL.md"
REFERENCE = ROOT / "goc" / "templates" / "skills" / "refine-deck" / "reference.md"

CREATING = "creating-commit"
AUTHORING = "authoring-commit"

# Fenced-cite scope verdicts. BLANKET covers both inventions the silence
# allowed: they differ only in which shape they damage, and neither states
# a disposition per shape, so the prose reads the same to the classifier.
SPLIT_BY_CLAIM = "split-by-what-the-cite-claims"
BLANKET = "one-rule-for-every-fenced-cite"

CARD = "a-card-whose-cite-was-repaired-once"
CITED_FILE = "src/app.py"

# Line 6 is `def target(payload):` — what the card is about.
# Line 11 is the decoy's return — unrelated code that the creating-commit
# anchor lands on once the cite has been repaired to 11.
V1 = [
    '"""Fixture module."""',
    "",
    "def helper():",
    '    return "helper result"',
    "",
    "def target(payload):",
    "    return payload * 2",
    "",
    "",
    "def decoy():",
    '    return "decoy sentinel that is long and unique"',
    "",
    "def tail():",
    "    return None",
]
INSERT_1 = ["import os", "import sys", "", "CONST_A = 1", ""]
INSERT_2 = ["import json", "import re", "", "CONST_B = 2", ""]

TARGET_LINE_IN_HEAD = 16  # `def target(payload):` after both inserts
DECOY_LINE_IN_HEAD = 21  # the decoy return after both inserts


def documented_anchor(prose: str) -> str | None:
    """Which anchor commit does this stretch of skill prose prescribe?

    The two recipes are told apart by the git incantation each one needs:
    the creating-commit rule exists only to find the README's ADD commit
    (`--diff-filter=A`), while the authoring rule walks the README's own
    history (`--follow`) for the commit where the cite token turns from
    absent to present. Prose naming both, or neither, is unclassifiable —
    a finding in itself, so this returns None rather than guessing.
    """
    walk = "--follow" in prose and "absent to present" in prose
    add_commit = "--diff-filter=A" in prose
    if walk and not add_commit:
        return AUTHORING
    if add_commit and not walk:
        return CREATING
    return None


def documented_fenced_scope(prose: str) -> str | None:
    """Which fenced-cite rule does this stretch of skill prose prescribe?

    A pass needs three things from the prose to avoid inventing one: that
    a fence is not itself decisive, the shape inside a fence that IS an
    assertion about HEAD (a comment label), and the shape that is a dated
    record it must never rewrite. Prose that names no fence at all is
    SILENT — returns None, the state the defect was filed for. Prose that
    names the fence but not both dispositions is BLANKET, which is the
    invention restated rather than a rule.
    """
    lower = prose.lower()
    if "fenced" not in lower and "code block" not in lower:
        return None
    labels_repaired = "comment label" in lower
    records_excluded = "transcript" in lower and (
        "out of scope" in lower or "leave the records" in lower
    )
    if labels_repaired and records_excluded:
        return SPLIT_BY_CLAIM
    return BLANKET


def skill_citation_section() -> str:
    """The core skill's § Defunct file:line citations, that subsection only."""
    body = SKILL.read_text(encoding="utf-8")
    match = re.search(
        r"^### Defunct file:line citations$.*?(?=^#{1,3} \S)", body, re.S | re.M
    )
    if match is None:
        raise AssertionError(
            "refine-deck SKILL.md no longer has a "
            "'### Defunct file:line citations' section"
        )
    return match.group(0)


def skill_step_two() -> str:
    """Step 2 of the core skill's per-cite recipe."""
    body = SKILL.read_text(encoding="utf-8")
    match = re.search(r"^2\. Anchor = .*?(?=^3\. )", body, re.S | re.M)
    if match is None:
        raise AssertionError(
            "refine-deck SKILL.md no longer has a step 2 starting "
            "'2. Anchor = ' in the defunct-citation check"
        )
    return match.group(0)


def reference_anchor_section() -> str:
    """The reference sibling's § Citation anchor check."""
    body = REFERENCE.read_text(encoding="utf-8")
    match = re.search(
        r"^## Citation anchor check$.*?(?=^## )", body, re.S | re.M
    )
    if match is None:
        raise AssertionError(
            "refine-deck reference.md no longer has a "
            "'## Citation anchor check' section"
        )
    return match.group(0)


def git(repo: Path, *args: str) -> str:
    env = {**os.environ, "PRE_COMMIT_ALLOW_NO_CONFIG": "1"}
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True,
        text=True, env=env,
    ).stdout


def write_source(repo: Path, lines: list[str]) -> None:
    (repo / CITED_FILE).write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_card(repo: Path, cited_line: int) -> None:
    (repo / card_readme()).write_text(
        f"# {CARD}\n\n"
        f"`{CITED_FILE}:{cited_line}` is the entry point this card is about.\n",
        encoding="utf-8",
    )


def card_readme() -> str:
    return f".game-of-cards/deck/{CARD}/README.md"


def build_two_pass_repo(repo: Path) -> None:
    """File a cite, drift it, repair it, drift it again."""
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "test@example.com")
    git(repo, "config", "user.name", "Test")
    (repo / CITED_FILE).parent.mkdir(parents=True)
    (repo / card_readme()).parent.mkdir(parents=True)

    write_source(repo, V1)
    write_card(repo, 6)  # correct at this commit
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "file the card citing src/app.py:6")

    write_source(repo, INSERT_1 + V1)  # target moves 6 -> 11
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "grow the source; the cite rots")

    write_card(repo, 11)  # first repair pass: correct again
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "hygiene pass: repair the cite to 11")

    write_source(repo, INSERT_2 + INSERT_1 + V1)  # target moves 11 -> 16
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "grow the source again; the cite rots again")


def anchor_commit(repo: Path, cite_token: str, mode: str) -> str:
    """Run the anchor rule `mode` names over the card's README history."""
    history = git(
        repo, "log", "--follow", "--format=%H", "--", card_readme()
    ).split()
    history.reverse()  # oldest first
    if mode == CREATING:
        return history[0]
    intro, present_before = history[0], False
    for commit in history:
        present = cite_token in git(repo, "show", f"{commit}:{card_readme()}")
        if present and not present_before:
            intro = commit
        present_before = present
    return intro


def repair(repo: Path, mode: str) -> int | None:
    """The skill's per-cite recipe: anchor, compare to HEAD, relocate.

    Returns the line number the pass would write, or None where step 4
    declines (anchor gone, ambiguous, or trivial).
    """
    readme = (repo / card_readme()).read_text(encoding="utf-8")
    cited_line = int(re.search(rf"{re.escape(CITED_FILE)}:(\d+)", readme).group(1))
    cite_token = f"{CITED_FILE}:{cited_line}"

    commit = anchor_commit(repo, cite_token, mode)
    anchored = git(repo, "show", f"{commit}:{CITED_FILE}").splitlines()
    if cited_line > len(anchored):
        return None
    anchor = anchored[cited_line - 1]

    head = (repo / CITED_FILE).read_text(encoding="utf-8").splitlines()
    if cited_line <= len(head) and head[cited_line - 1] == anchor:
        return cited_line  # not defunct
    if len(anchor.strip()) < 12:
        return None  # trivial line: never guess
    hits = [i + 1 for i, line in enumerate(head) if line == anchor]
    return hits[0] if len(hits) == 1 else None


class DocumentedAnchorRuleTest(unittest.TestCase):
    def test_core_skill_anchors_at_the_commit_that_wrote_the_number(self) -> None:
        self.assertEqual(
            AUTHORING,
            documented_anchor(skill_step_two()),
            "refine-deck SKILL.md step 2 must anchor at the commit that last "
            "WROTE the cited number (the `git log --follow` walk), not at the "
            "commit that created the card",
        )

    def test_reference_sibling_prescribes_the_same_anchor(self) -> None:
        self.assertEqual(
            documented_anchor(skill_step_two()),
            documented_anchor(reference_anchor_section()),
            "refine-deck's core skill and its reference sibling prescribe "
            "different anchor commits; an agent following either would get a "
            "different repair",
        )


class SecondRepairPassTest(unittest.TestCase):
    """The shape the live-deck replay can only measure after the fact."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        build_two_pass_repo(self.repo)
        self.addCleanup(self._tmp.cleanup)

    def test_documented_recipe_repairs_a_repaired_cite_to_the_right_line(
        self,
    ) -> None:
        mode = documented_anchor(skill_step_two())
        self.assertIsNotNone(
            mode, "refine-deck SKILL.md step 2 no longer names an anchor commit"
        )
        self.assertEqual(
            TARGET_LINE_IN_HEAD,
            repair(self.repo, mode),
            "the recipe refine-deck ships must move a once-repaired cite onto "
            "the code the card is about",
        )

    def test_creating_commit_anchor_moves_the_cite_onto_unrelated_code(
        self,
    ) -> None:
        # Not a spec — the fixture's own proof that it exercises the defect.
        # The cite is correct for the code at line 11 of the FIRST pass's
        # output; anchoring at the card's creating commit reads the decoy
        # that happened to sit at line 11 when the card was filed, and moves
        # the cite there.
        self.assertEqual(DECOY_LINE_IN_HEAD, repair(self.repo, CREATING))


class DocumentedFencedScopeTest(unittest.TestCase):
    """A cite's scope is what it claims, not whether a fence surrounds it."""

    def test_core_skill_splits_fenced_cites_by_what_they_claim(self) -> None:
        self.assertEqual(
            SPLIT_BY_CLAIM,
            documented_fenced_scope(skill_citation_section()),
            "refine-deck SKILL.md § Defunct file:line citations must say "
            "which cites inside a fenced block are repaired (comment labels, "
            "which assert where code lives now) and which are left and "
            "reported (pasted output and transcripts, which are dated "
            "records); silence there is re-invented differently every pass",
        )

    def test_reference_sibling_prescribes_the_same_scope(self) -> None:
        self.assertEqual(
            documented_fenced_scope(skill_citation_section()),
            documented_fenced_scope(reference_anchor_section()),
            "refine-deck's core skill and its reference sibling scope fenced "
            "cites differently; a pass following either would repair a "
            "different set",
        )

    def test_both_surfaces_give_a_mechanical_test_for_the_label_shape(
        self,
    ) -> None:
        # "comment label" is the name of the shape; a pass also needs to be
        # able to recognise one without re-deriving the deck census.
        for label, prose in (
            ("SKILL.md", skill_citation_section()),
            ("reference.md", reference_anchor_section()),
        ):
            with self.subTest(surface=label):
                self.assertTrue(
                    "`#`" in prose and "`//`" in prose and "marker" in prose,
                    f"refine-deck {label} names the comment-label shape but "
                    "not the marker test that identifies it",
                )

    def test_silent_prose_is_classified_as_silent(self) -> None:
        # The fixture's own proof that the classifier can fail: the recipe as
        # it shipped before this rule existed named no fence at all.
        self.assertIsNone(
            documented_fenced_scope(
                "Relocate the anchor text in HEAD and rewrite the number only "
                "on a unique match of a non-trivial line. Never guess."
            )
        )


if __name__ == "__main__":
    unittest.main()
