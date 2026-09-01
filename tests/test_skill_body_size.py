"""Regression guard: hot-path skill bodies stay lean.

Skill bodies load into the conversation on every invocation and persist
for the rest of the session, so their size is a per-invocation tax on
every consuming repo (measured downstream: 31% of a project's session
usage went to this plugin, finish-card alone 15%). The workhorse skills
are restructured for progressive disclosure — the happy path lives in
SKILL.md, edge-case material in a sibling ``reference.md`` that the
model reads only when the situation arises. This guard keeps future
edits from re-fattening the hot path: new edge-case prose belongs in
the sibling, not the core.
"""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_SKILLS = ROOT / "goc" / "templates" / "skills"

# Bytes of SKILL.md (frontmatter + body). The capped set is the hot path
# (the per-card-cycle verbs plus the cross-referenced schema skill) and the
# occasional skills that got the same progressive-disclosure split later.
# kickoff's cap is higher because its body is mostly verbatim dialog text
# delivered to the user, which cannot move to the reference sibling.
#
# card-schema and refine-deck were raised on 2026-08-03 by the card
# `meta-fix-predicate-cannot-fire-on-a-newly-filed-umbrella-card`: the
# canonical-tags table gained a per-row `check` column plus the two-line rule
# saying what `judgment` implies for a sweep, and both had been sitting within
# 5 bytes of their cap. The rationale (three measured failures of the old
# single-predicate rule) went to the reference siblings as this guard
# prescribes; what stayed is the contract itself, which a reader of the table
# cannot act on from a pointer.
#
# refine-deck was raised again on 2026-08-10 by the card
# `refine-deck-citation-check-cannot-detect-line-drift-in-a-growing-file`: the
# defunct-citation check was specified as a `line <= EOF` bounds test with
# measured recall 0 of 482, and its replacement is an anchor comparison plus a
# four-step repair recipe. The long form (why bounds fails, the resolution
# rules, the residue table) went to the reference sibling; the rule and the
# recipe stayed in the core because an agent that has to follow a pointer to
# learn the test will run the bounds test it already remembers.
#
# refine-deck was raised a third time on 2026-08-17 by the card
# `second-citation-repair-pass-moves-correct-cites-onto-unrelated-code`: step 2
# of that same recipe anchored on the card's creating commit, which is correct
# exactly once — a repair pass rewrites the number, and reading a rewritten
# number at the creating commit resolves unrelated code (measured: 165 of 850
# correct cites would have been moved on this deck's second pass). Its
# replacement is the history walk that finds the commit which last wrote the
# number. The measurement and the why went to the reference sibling; the walk
# itself stayed in the core for the reason above — an agent that has to follow
# a pointer to learn the anchor will use the one-liner in front of it.
#
# create-card and finish-card were raised on 2026-08-24 by the card
# `parked-decision-cards-are-never-re-checked-against-the-code-that-moved-under-them`:
# dedup ran on titles only, and a title is written in the filer's vocabulary
# while the symbol sits in the body. Measured on this deck, three cards
# described one `goc --waiting` defect; two sat at `human_gate: decision` for
# 61 days after the third was fixed and closed, with no edge between them.
# The two skills now carry the body-grep at both ends of a card's life —
# create-card before filing, finish-card before the close. The measurement,
# the worked instance and the gated-card etiquette went to the reference
# siblings; what stayed in each core is the one-line rule plus the grep,
# because an agent that has to follow a pointer to learn that titles are
# insufficient will run the title grep it already remembers. create-card was
# at 9996 of 10000 before this, so no addition of any size would have fit.
#
# refine-deck was raised a fourth time on 2026-09-01 by the card
# `citation-repair-pass-has-no-rule-for-cites-inside-fenced-code-blocks`: the
# repair recipe said whether a number CAN be relocated and nothing about
# whether it SHOULD be, so a cite inside a fenced block was left to each
# pass's invention — and the two defensible inventions disagree on every
# fenced cite in the deck (measured: 49 comment labels, which must be
# repaired, against 17 pasted-output records, which must not). The 2026-08-31
# pass invented "skip every fenced cite" and left 28 defunct labels it had
# already computed valid relocations for. What stayed in the core is the
# scope rule and its marker test; the census, the failed pass and the
# reporting shape went to the reference sibling. A pointer would not have
# worked here for a sharper reason than the earlier three raises: the defect
# IS a pass inventing the missing rule rather than going to look for it.
BODY_CAPS = {
    "create-card": 10_500,
    "finish-card": 10_500,
    "advance-card": 10_000,
    "decide-card": 10_000,
    "next-card": 10_000,
    "pull-card": 10_000,
    "card-schema": 12_800,
    "deck": 10_000,
    "refine-deck": 12_300,
    "kickoff": 11_000,
    "audit-deck": 10_000,
}


# Bytes of the marker-bounded briefing block template injected into every
# consumer's AGENTS.md / CLAUDE.md. Consumers' bootstrap files have hard
# char budgets (OpenClaw trims at bootstrapMaxChars, default 20k), so the
# goc-owned block must stay a pointer surface: discovery signal, skill
# list, one-line rules. Methodology prose belongs in the skills.
BRIEFING_CAP = 2_500
BRIEFING_TEMPLATE = ROOT / "goc" / "templates" / "AGENTS_GOC.md"


class SkillBodySizeTest(unittest.TestCase):
    def test_hot_path_skill_bodies_fit_their_caps(self) -> None:
        over_cap: list[str] = []
        for name, cap in sorted(BODY_CAPS.items()):
            path = TEMPLATE_SKILLS / name / "SKILL.md"
            size = path.stat().st_size
            if size > cap:
                rel = path.relative_to(ROOT)
                over_cap.append(f"{rel}: {size} > {cap}")
        self.assertEqual([], over_cap)

    def test_capped_skills_exist(self) -> None:
        for name in BODY_CAPS:
            self.assertTrue(
                (TEMPLATE_SKILLS / name / "SKILL.md").is_file(),
                f"capped skill vanished: {name}",
            )


class BriefingBlockSizeTest(unittest.TestCase):
    def test_briefing_template_fits_its_cap(self) -> None:
        size = BRIEFING_TEMPLATE.stat().st_size
        self.assertLessEqual(
            size,
            BRIEFING_CAP,
            f"{BRIEFING_TEMPLATE.relative_to(ROOT)}: {size} > {BRIEFING_CAP}; "
            "the marker block is always-loaded in every consumer — move new "
            "prose into a skill and leave a one-line pointer.",
        )


if __name__ == "__main__":
    unittest.main()
