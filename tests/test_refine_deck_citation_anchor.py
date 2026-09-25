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

A third gap in the same recipe gets the same treatment, and needs a
functional half as well:
`citation-repair-pass-maps-range-endpoints-independently-and-corrupts-the-range`
found that a range cite's two endpoints were mapped as independent
single-line lookups, with nothing asking afterwards whether the pair
still bounded a block. Endpoints usually move together, so the rule
reads correct until the day one endpoint relocates and the other reads
`current` at its own line — and from then on the wreck is invisible,
because both numbers anchor cleanly in isolation and no pass ever
declines it. Twelve such cites sat across eight open cards. So the prose
classifier below is paired with a fixture reproducing exactly that
divergence, and the guard proves the shipped recipe DECLINES the repair
it must decline rather than only proving the words changed.

A fourth gap in the recipe, and the only one on the DECIDE side:
`citation-repair-pass-calls-a-cite-current-when-its-anchor-line-is-a-brace-or-blank`
found the non-triviality predicate running on the relocate step alone.
The same line the recipe refuses as evidence FOR a rewrite — a blank, a
bare brace, "anything under roughly 12 characters, which match
everywhere" — was accepted as evidence AGAINST one, because step 3 was a
bare text comparison with no predicate on what it compared. So `}` at
the cited offset in HEAD matching `}` at the anchor commit verdicted
`current`, and a `current` verdict is silence: no decline line, no
residue row, nothing a reader could notice. Measured on this deck, 46 of
413 such verdicts over 28 open cards rested on a line the recipe's own
guard called unusable. The fixture below is the worst shape of it,
because a blank line cannot decay: an author's off-by-one is frozen into
a permanent `current` that every later pass re-certifies.

A fifth gap sits one level under the anchor rule itself:
`citation-repair-pass-gives-two-cites-in-one-card-the-same-anchor-when-their-numbers-collide`
found that the walk identifies a cite by its TOKEN and tests presence
with a substring search, neither of which pins the OCCURRENCE being
repaired. So `path:N` reads as present inside a `path:N-M` the same card
carries and inherits the range's older anchor; and where a past repair
has landed one cite on a number another already held, the two
occurrences share one history and no walk can anchor them apart at all.
Either way the cite is anchored on text it never named, verdicted
defunct while correct, and moved. The last fixture below is the first
half — a card carrying a range and a single-line cite, where the two
readings each produce a confident unique relocation onto a different
line — and the decline is the second, because occurrence-awareness in
the presence test cannot rescue a token the card holds twice.

A later gap sits in no per-cite rule at all, but in WHEN the closing
re-run runs:
`citation-idempotence-re-run-reports-false-repairs-until-the-pass-commits`
found the fixed-point check reading the card's history out of `git log`
while the rewrites it was checking sat uncommitted in the working tree. A
cite the pass had just written therefore anchored on the last COMMITTED
turn of its number — on a renumbering pass, a retired occurrence that
named a different cite — and the check proposed moving a correct cite
onto that cite's code: three such proposals over one pass's 269 repairs,
and zero once the same pass had committed. The classifier pins the order
and its reason, and the fixture replays that second pass both ways.
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

# Range-repair verdicts. PAIR_UNCHECKED is the recipe as it shipped from
# 2026-08-10 to 2026-09-07: two endpoints mapped, nothing asked afterwards
# about what they bound.
COHERENCE_GUARDED = "pair-checked-after-both-endpoints-map"
PAIR_UNCHECKED = "endpoints-mapped-independently"

# Decide-step verdicts. DECIDE_UNGUARDED is the recipe as it shipped from
# 2026-08-10 to 2026-09-14: compare the two texts and believe the answer,
# with the non-triviality predicate reserved for the relocate step below it.
DECIDE_GUARDED = "trivial-anchor-refused-before-comparing"
DECIDE_UNGUARDED = "compared-whatever-the-anchor-line-held"

# Anchor-walk verdicts. TOKEN_WALK is the recipe as it shipped from
# 2026-08-17 to 2026-09-14: presence tested as a substring of the README
# text, with a cite identified by its token and nothing else.
OCCURRENCE_GUARDED = "token-exact-and-repeats-declined"
TOKEN_WALK = "substring-presence-on-a-bare-token"

# Relocate-step verdicts. EXACT_LINE_ONLY is the recipe as it shipped from
# 2026-08-10 to 2026-09-14: full-line equality, which makes the anchor LINE
# the unit of identity even where the line is a definition.
NAME_GUARDED = "definition-relocated-by-its-name"
EXACT_LINE_ONLY = "exact-full-line-equality"

# Re-run ordering verdicts. RERUN_UNORDERED is the recipe as it shipped from
# 2026-09-14 to 2026-09-25: apply the rewrites, then re-run, with the commit
# named nowhere — so a pass reading it literally re-runs over a working tree
# the history walk cannot see.
COMMIT_THEN_RERUN = "rewrites-committed-before-the-re-run"
RERUN_UNORDERED = "re-run-with-the-commit-unplaced"

# What the recipe answers about one cited line.
CURRENT = "current"
DEFUNCT = "defunct"
DECLINE_TRIVIAL = "decline-trivial-anchor"
DECLINE_OCCURRENCE = "decline-ambiguous-occurrence"

# How the pass finds the cites in a card — reused as the membership test the
# fixed presence rule prescribes, so the fixture cannot drift into a second
# extractor the way the prose drifted into a second predicate.
CITE_TOKEN = re.compile(r"[\w./-]+\.py:\d+(?:-\d+)?")

# A definition line, and the name that identifies it. Mirrors the shape the
# shipped prose names — `def <name>(` / `class <name>(` — so the fixture
# cannot drift into a looser matcher than the one the recipe prescribes.
DEFN = re.compile(r"^\s*(?:async\s+)?(def|class)\s+([A-Za-z_]\w*)\s*\(")

# A repaired pair wider than this is no longer addressing a block. Mirrors
# the threshold the shipped prose names and the one the card's reproduce.py
# scans the deck with.
MAX_PLAUSIBLE_SPAN = 500

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

# The range fixture, and the one coincidence the defect needs. The cited
# block is lines 6-8. Line 8's text is a repeated idiom that also sits at
# line 4, so inserting exactly that gap — four lines — above the module
# leaves the END anchor reading unchanged AT ITS OWN NUMBER while the START
# anchor has moved down. Each endpoint is then correct in isolation and the
# pair is inverted, the same coincidence that broke twelve cites on this
# deck. The insert is sized to the gap deliberately: a shorter or longer
# one makes the end endpoint defunct too, and it relocates ambiguously.
RANGE_V1 = [
    '"""Fixture module."""',
    "",
    "def alpha():",
    "    return compute(payload)",
    "",
    "def target(payload):",
    "    value = payload * 2",
    "    return compute(payload)",
    "",
    "def omega():",
    "    return None",
]
RANGE_INSERT = ["import os", "import sys", "", "CONST_A = 1"]
RANGE_CITED = (6, 8)
RANGE_START_IN_HEAD = 10  # `def target(payload):` after the insert
RANGE_END_UNMOVED = 8  # line 8 in HEAD is the idiom from old line 4

# The blank-anchor fixture reuses V1 and INSERT_1, because between them they
# already hold the coincidence the defect needs. Line 5 of V1 is the blank
# directly above `def target(payload):` — the off-by-one a card author writes
# once and no pass can catch. INSERT_1 is five lines ending in a blank, so
# line 5 of HEAD is blank as well: anchor and HEAD agree, the cite verdicts
# `current`, and the function it names has moved to line 11.
TRIVIAL_CITED = 5
TRIVIAL_TARGET_IN_HEAD = 11

# The colliding-anchor fixture. The card carries TWO cites — a range over the
# target block and a single line inside the helper above it — and the story is
# the one the deck produced: the file grows, a pass repairs both, and the
# number the single-line cite lands on is one the RANGE already spelled at an
# older commit. A substring presence test therefore sees that token as present
# from the range's own filing and anchors the helper cite on whatever sat at
# that offset back then, which here is the target's `def` line. Both readings
# then relocate uniquely and confidently, onto different lines: this is the
# shape that WRITES rather than mis-verdicts.
COLLIDE_V1 = [
    '"""Fixture module."""',
    "",
    "def alpha():",
    '    return "alpha sentinel value"',
    "",
    "def target(payload):",
    "    value = payload * 2",
    "    return value",
    "",
    "def omega():",
    "    return None",
]
COLLIDE_INSERT_1 = ["import os", "import sys"]
COLLIDE_INSERT_2 = ["import json", "import re", "CONST_B = 2"]

COLLIDE_BLOCK_FILED = (6, 8)  # the target block at the filing commit
COLLIDE_BLOCK_REPAIRED = (8, 10)  # the same block after the first insert
COLLIDE_SINGLE_LINE = 6  # the helper's return, after the first insert
COLLIDE_SINGLE_CITE = f"{CITED_FILE}:{COLLIDE_SINGLE_LINE}"
ALPHA_LINE_IN_COLLIDE_HEAD = 9  # where the helper's return actually went
TARGET_LINE_IN_COLLIDE_HEAD = 11  # where the RANGE's anchor text went


# The signature-drift fixture. The card cites a function by its `def` line;
# the file then grows AND the function gains a keyword-only parameter, so the
# anchor text is nowhere in HEAD while the function it names is one grep away
# and uniquely named. This is the shape one refactor produces in families —
# five install-time writers on this repo gained `*, probe: bool = False` in a
# single commit and every card citing any of them lost its anchor at once.
SIG_V1 = [
    '"""Fixture module."""',
    "",
    "def helper():",
    '    return "helper result"',
    "",
    "def target(payload):",
    "    return payload * 2",
    "",
    "def omega():",
    "    return None",
]
SIG_INSERT = ["import os", "import sys", "", "CONST_A = 1", ""]
SIG_HEAD_DEF = "def target(payload, *, probe: bool = False):"
SIG_CITED = 6
SIG_TARGET_IN_HEAD = 11  # `def target(...)` after the insert

# The range half, built on the same coincidence the earlier range fixture
# needs: line 8's text is a repeated idiom that also sits at line 4, so an
# insert of exactly that gap leaves the END anchor reading unchanged AT ITS
# OWN NUMBER while the START — a `def` line whose signature also changed —
# only the NAME rule can map. The pair the mapper then hands over is
# inverted, which is what makes the pair check the deciding step.
SIG_RANGE_V1 = [
    '"""Fixture module."""',
    "",
    "def alpha():",
    "    return compute(payload)",
    "",
    "def target(payload):",
    "    value = payload * 2",
    "    return compute(payload)",
    "",
    "def omega():",
    "    return None",
]
SIG_RANGE_INSERT = ["import os", "import sys", "", "CONST_A = 1"]
SIG_RANGE_CITED = (6, 8)
SIG_RANGE_START_IN_HEAD = 10  # where the name rule maps the start
SIG_RANGE_END_UNMOVED = 8  # line 8 in HEAD is the idiom from old line 4

# The retired-occurrence fixture reuses V1 and INSERT_1. The card carries two
# single-line cites, both correct when filed: `:6` on the target's `def` and
# `:11` on the decoy's return. The file first grows BETWEEN them, so only the
# decoy cite rots, and a first pass moves it to `:16` — retiring the token
# `:11` from the card. The file then grows above both, and a second pass
# repairs the target cite onto `:11`: correct, and the very number the decoy
# cite carried two passes ago. Until that second pass commits, `:11`'s newest
# absent-to-present turn is the FILING commit, where line 11 was the decoy.
RETIRE_MID_INSERT = ["LIMIT_A = 1", "LIMIT_B = 2", "LIMIT_C = 3", "LIMIT_D = 4", ""]
RETIRE_FILED = (6, 11)  # (target, decoy) at the filing commit
RETIRE_PASS_1 = (6, 16)  # the first pass repairs the decoy cite only
RETIRE_PASS_2 = (11, 21)  # the second pass: both correct in HEAD
RETIRED_TOKEN = f"{CITED_FILE}:11"


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


def _flat(prose: str) -> str:
    """Hard-wrapped prose as one lowercase line, so rules survive rewrapping."""
    return " ".join(prose.split()).lower()


def documented_range_coherence(prose: str) -> str | None:
    """Which range-repair rule does this stretch of skill prose prescribe?

    A pass needs two things the endpoint recipe cannot supply on its own.
    First, a check on the PAIR it is about to write — ordered, and still
    narrow enough to be a block — because two individually valid
    relocations can bound nothing. Second, a refusal to re-map a range
    that ARRIVES incoherent, whose endpoints anchor to whatever an earlier
    pass moved them onto, so running the recipe launders the corruption
    into a fresh one that looks repaired.

    Prose that says nothing about ranges is unclassifiable and returns
    None. Prose that describes ranges without both rules is
    PAIR_UNCHECKED — the shipped text the defect was filed against, which
    reads as a complete instruction and is exactly why no pass went
    looking for the missing half.
    """
    flat = _flat(prose)
    if "range" not in flat:
        return None
    pair_checked = "start <= end" in flat and "span still fits a block" in flat
    declines = "decline" in flat
    keeps_hands_off = "arrives incoherent" in flat and "launder" in flat
    if pair_checked and declines and keeps_hands_off:
        return COHERENCE_GUARDED
    return PAIR_UNCHECKED


def documented_decide_guard(prose: str) -> str | None:
    """Does this stretch of skill prose guard the DECIDE step, or only relocate?

    A pass needs the non-triviality predicate applied BEFORE the anchor
    text is compared to HEAD, not after. The ordering is the whole rule:
    a line that "matches everywhere" matches at the cited offset too, so
    using it to certify a cite is the same unsound step as using it to
    move one — and the certification is the dangerous half, because it
    prints nothing.

    Prose that never reaches a defunct/current verdict is not the
    deciding rule and returns None. Prose that decides without naming the
    predicate at all, or names it only downstream of the comparison, is
    DECIDE_UNGUARDED — the shipped text this was filed against, which
    reads as complete precisely because the guard IS in it, one step too
    late.
    """
    flat = _flat(prose)
    if "defunct" not in flat:
        return None
    if "bare brace" not in flat:
        return DECIDE_UNGUARDED
    guarded = (
        flat.index("bare brace") < flat.index("defunct")
        and "decline" in flat
        and "never `current`" in flat
    )
    return DECIDE_GUARDED if guarded else DECIDE_UNGUARDED


def documented_occurrence_rule(prose: str) -> str | None:
    """Does this stretch of skill prose tie the anchor walk to an OCCURRENCE?

    Two rules, and a pass needs both. Presence has to be SET MEMBERSHIP
    over the version's own extracted cite tokens, because a substring
    search reads `path:N` as present inside a `path:N-M` the same card
    carries, and the single-line cite then inherits the range's older
    anchor. And a token the card holds at two or more occurrences has to
    be DECLINED, because those occurrences share one history and no walk
    separates them — token-exactness cannot rescue that one, since the
    token genuinely WAS present at the earlier commit, at the other
    occurrence.

    Prose that never walks the history is not the anchor rule and
    returns None. Prose that walks it without both rules is TOKEN_WALK —
    the shipped text this was filed against, which called the token
    "exact" and so read as precise already: the word modified the token
    while the test around it was still a substring `in`.
    """
    flat = _flat(prose)
    if "absent to present" not in flat:
        return None
    token_exact = "set membership" in flat and "substring" in flat
    repeats_declined = (
        "two or more" in flat or "more than one" in flat
    ) and "decline" in flat
    return OCCURRENCE_GUARDED if token_exact and repeats_declined else TOKEN_WALK


def documented_definition_rule(prose: str) -> str | None:
    """Does this stretch of skill prose relocate a DEFINITION by its name?

    Exact full-line equality makes the anchor LINE the unit of identity.
    For a statement inside a body that is right — the line is all the card
    ever meant. For a `def` or `class` line it is wrong: the card means the
    definition, and the line is only how it announced itself on the day the
    cite was written, so a keyword-only parameter appended to the signature
    turns a uniquely named function that is one grep away into "anchor text
    absent", permanently.

    Three things have to be in the prose, and a pass needs all three. The
    retry itself, on a unique `def <name>(` / `class <name>(` match. The
    DECLINE when HEAD holds that name twice, since nearest-match is no more
    available here than to the exact rule. And the subordination to the pair
    check, because seven of the twelve cites this was filed for are range
    endpoints and relocating a start while the end stays put is the
    corruption the range card closed.

    Prose that never relocates is not this rule and returns None. Prose that
    relocates without all three is EXACT_LINE_ONLY — the shipped text this
    was filed against, which reads as complete because its refusal to guess
    IS complete; what it gets wrong is what the anchor identifies.
    """
    flat = _flat(prose)
    if "relocate" not in flat and "look for the anchor text" not in flat:
        return None
    by_name = "def <name>(" in flat and "class <name>(" in flat
    ambiguity_declined = "definitions of that name" in flat and "decline" in flat
    pair_still_governs = "pair check still" in flat
    if by_name and ambiguity_declined and pair_still_governs:
        return NAME_GUARDED
    return EXACT_LINE_ONLY


def documented_idempotence_check(prose: str) -> bool:
    """Does this stretch of skill prose close the pass by re-running it?

    The colliding-anchor class is invisible per cite: every second-round
    proposal it produces is individually well-formed — a real anchor, a
    unique match, a confident rewrite — so no per-cite rule declines it.
    Re-running the decision phase over what the pass just wrote and
    finding it EMPTY is the only check that sees the class at all, and
    it is how this one was found.
    """
    flat = _flat(prose)
    return ("re-run" in flat or "re-running" in flat) and (
        "zero further repairs" in flat
    )


def documented_rerun_order(prose: str) -> str | None:
    """Does this stretch of skill prose commit the rewrites BEFORE re-running?

    The re-run's anchor walk reads `git log`, so it sees a rewrite only once
    the rewrite is committed. Re-run over the working tree instead and a cite
    the pass has just written anchors on the last commit that carried its
    number — on a renumbering pass, routinely a RETIRED occurrence that named
    a different cite — so the fixed-point check proposes moving a correct cite
    onto that cite's code. Two things have to be in the prose: the order
    itself, commit and THEN re-run, and the reason for it, because a pass
    holding the order without the reason has no ground to refuse a pre-commit
    re-run that looks like extra diligence.

    Prose with no re-run in it is not the idempotence rule and returns None.
    Prose that re-runs without both is RERUN_UNORDERED — the shipped text this
    was filed against, which reads as complete because the re-run IS in it,
    and never says when.
    """
    if not documented_idempotence_check(prose):
        return None
    flat = _flat(prose)
    ordered = (
        re.search(r"\bcommit(?:ting)?(?: the rewrites)?, then re-run", flat)
        is not None
    )
    reason = "git log" in flat and "uncommitted" in flat
    return COMMIT_THEN_RERUN if ordered and reason else RERUN_UNORDERED


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


def skill_step_one() -> str:
    """Step 1 of the core skill's per-cite recipe — path and range resolution."""
    body = SKILL.read_text(encoding="utf-8")
    match = re.search(r"^1\. Resolve the path .*?(?=^2\. )", body, re.S | re.M)
    if match is None:
        raise AssertionError(
            "refine-deck SKILL.md no longer has a step 1 starting "
            "'1. Resolve the path ' in the defunct-citation check"
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


def skill_step_three() -> str:
    """Step 3 of the core skill's per-cite recipe — the defunct/current verdict.

    Scoped to the citation subsection first, so the numbered-list match
    cannot wander into another step list elsewhere in the skill body.
    """
    match = re.search(r"^3\. .*?(?=^4\. )", skill_citation_section(), re.S | re.M)
    if match is None:
        raise AssertionError(
            "refine-deck SKILL.md no longer has a step 3 in the "
            "defunct-citation check"
        )
    return match.group(0)


def skill_step_four() -> str:
    """Step 4 of the core skill's per-cite recipe — the relocate rule.

    Scoped to the citation subsection first, then to the numbered item: the
    list's items carry no blank line of their own, so the first one ends it.
    """
    match = re.search(r"^4\. .*?(?=\n\n)", skill_citation_section(), re.S | re.M)
    if match is None:
        raise AssertionError(
            "refine-deck SKILL.md no longer has a step 4 in the "
            "defunct-citation check"
        )
    return match.group(0)


def reference_deciding_paragraph() -> str:
    """The reference sibling's **Deciding.** paragraph, that paragraph only."""
    match = re.search(
        r"^\*\*Deciding\.\*\* .*?(?=\n\n\*\*)", reference_anchor_section(), re.S | re.M
    )
    if match is None:
        raise AssertionError(
            "refine-deck reference.md § Citation anchor check no longer has a "
            "'**Deciding.**' paragraph"
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


def residue_rows() -> list[str]:
    """The decline reasons the reference's residue table actually carries."""
    rows = []
    for line in reference_anchor_section().splitlines():
        if not line.startswith("|"):
            continue
        cell = line.split("|")[1].strip()
        if cell in ("Decline", "") or set(cell) <= {"-"}:
            continue
        rows.append(cell)
    return rows


def card_cite_tokens(text: str) -> list[str]:
    """Every cite token in a card body, in order — the pass's own extractor."""
    return CITE_TOKEN.findall(text)


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


def write_range_card(repo: Path, start: int, end: int) -> None:
    (repo / card_readme()).write_text(
        f"# {CARD}\n\n"
        f"`{CITED_FILE}:{start}-{end}` is the block this card is about.\n",
        encoding="utf-8",
    )


def build_range_repo(repo: Path) -> None:
    """File a range cite over a block, then grow the file above it."""
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "test@example.com")
    git(repo, "config", "user.name", "Test")
    (repo / CITED_FILE).parent.mkdir(parents=True)
    (repo / card_readme()).parent.mkdir(parents=True)

    write_source(repo, RANGE_V1)
    write_range_card(repo, *RANGE_CITED)  # correct at this commit
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "file the card citing src/app.py:6-8")

    write_source(repo, RANGE_INSERT + RANGE_V1)  # block moves; line 8 does not
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "grow the source above the block")


def build_trivial_anchor_repo(repo: Path) -> None:
    """File a cite on the blank line above the target, then grow the file."""
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "test@example.com")
    git(repo, "config", "user.name", "Test")
    (repo / CITED_FILE).parent.mkdir(parents=True)
    (repo / card_readme()).parent.mkdir(parents=True)

    write_source(repo, V1)
    write_card(repo, TRIVIAL_CITED)  # one line off from the start it meant
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "file the card citing src/app.py:5")

    write_source(repo, INSERT_1 + V1)  # target moves 6 -> 11; line 5 stays blank
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "grow the source; the cite rots unnoticed")


def write_two_cite_card(repo: Path, block: tuple[int, int], single: int) -> None:
    (repo / card_readme()).write_text(
        f"# {CARD}\n\n"
        f"`{CITED_FILE}:{block[0]}-{block[1]}` is the block this card is about,\n"
        f"and `{CITED_FILE}:{single}` is the helper it returns from.\n",
        encoding="utf-8",
    )


def write_repeated_cite_card(repo: Path, line: int) -> None:
    """The convergence shape: one token, two in-scope occurrences."""
    (repo / card_readme()).write_text(
        f"# {CARD}\n\n"
        f"`{CITED_FILE}:{line}` is the helper this card is about.\n\n"
        f"Its only caller is at `{CITED_FILE}:{line}` as well, since the last\n"
        f"repair pass moved the two onto the same number.\n",
        encoding="utf-8",
    )


def build_collision_repo(repo: Path) -> None:
    """File a range and a single-line cite, grow the file, repair both, grow again.

    The single-line cite is repaired ONTO a number the range spelled at the
    filing commit, which is the whole coincidence: from that commit on, a
    substring presence test can no longer see the single-line token turn
    from absent to present.
    """
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "test@example.com")
    git(repo, "config", "user.name", "Test")
    (repo / CITED_FILE).parent.mkdir(parents=True)
    (repo / card_readme()).parent.mkdir(parents=True)

    write_source(repo, COLLIDE_V1)
    write_two_cite_card(repo, COLLIDE_BLOCK_FILED, 4)  # both correct here
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "file the card citing src/app.py:6-8 and :4")

    write_source(repo, COLLIDE_INSERT_1 + COLLIDE_V1)  # everything shifts +2
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "grow the source; both cites rot")

    write_two_cite_card(repo, COLLIDE_BLOCK_REPAIRED, COLLIDE_SINGLE_LINE)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "hygiene pass: repair both cites")

    write_source(repo, COLLIDE_INSERT_2 + COLLIDE_INSERT_1 + COLLIDE_V1)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "grow the source again; both cites rot again")


def build_signature_drift_repo(repo: Path) -> None:
    """File a cite on a `def` line, then grow the file AND the signature."""
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "test@example.com")
    git(repo, "config", "user.name", "Test")
    (repo / CITED_FILE).parent.mkdir(parents=True)
    (repo / card_readme()).parent.mkdir(parents=True)

    write_source(repo, SIG_V1)
    write_card(repo, SIG_CITED)  # correct at this commit
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "file the card citing src/app.py:6")

    grown = SIG_INSERT + SIG_V1
    grown[len(SIG_INSERT) + SIG_CITED - 1] = SIG_HEAD_DEF
    write_source(repo, grown)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "grow the file; target gains a probe parameter")


def build_signature_range_repo(repo: Path) -> None:
    """The same drift under a RANGE cite, with the end endpoint left unmoved."""
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "test@example.com")
    git(repo, "config", "user.name", "Test")
    (repo / CITED_FILE).parent.mkdir(parents=True)
    (repo / card_readme()).parent.mkdir(parents=True)

    write_source(repo, SIG_RANGE_V1)
    write_range_card(repo, *SIG_RANGE_CITED)  # correct at this commit
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "file the card citing src/app.py:6-8")

    grown = SIG_RANGE_INSERT + SIG_RANGE_V1
    grown[len(SIG_RANGE_INSERT) + SIG_RANGE_CITED[0] - 1] = SIG_HEAD_DEF
    write_source(repo, grown)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "grow the file above the block; signature changes")


def write_retire_card(repo: Path, target: int, decoy: int) -> None:
    (repo / card_readme()).write_text(
        f"# {CARD}\n\n"
        f"`{CITED_FILE}:{target}` is the entry point this card is about,\n"
        f"and `{CITED_FILE}:{decoy}` is the sentinel it must never return.\n",
        encoding="utf-8",
    )


def build_retired_occurrence_repo(repo: Path) -> None:
    """File two cites, repair one, then grow the file above both.

    Ends at the second pass's INPUT state: the pass has not run yet, and the
    token it is about to write for the target cite is one the card retired.
    """
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "test@example.com")
    git(repo, "config", "user.name", "Test")
    (repo / CITED_FILE).parent.mkdir(parents=True)
    (repo / card_readme()).parent.mkdir(parents=True)

    write_source(repo, V1)
    write_retire_card(repo, *RETIRE_FILED)  # both correct at this commit
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "file the card citing src/app.py:6 and :11")

    grown = V1[:8] + RETIRE_MID_INSERT + V1[8:]  # the decoy moves 11 -> 16
    write_source(repo, grown)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "grow the source between the two cites")

    write_retire_card(repo, *RETIRE_PASS_1)  # `:11` leaves the card here
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "hygiene pass: repair the decoy cite to 16")

    write_source(repo, INSERT_1 + grown)  # target 6 -> 11, decoy 16 -> 21
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "grow the source above both cites")


def anchor_commit(
    repo: Path, cite_token: str, mode: str, *, exact: bool = False
) -> str:
    """Run the anchor rule `mode` names over the card's README history.

    `exact=False` is the presence test as it shipped — a substring search
    over the README text. `exact=True` is the fixed rule: membership in
    that version's own extracted cite tokens.
    """
    history = git(
        repo, "log", "--follow", "--format=%H", "--", card_readme()
    ).split()
    history.reverse()  # oldest first
    if mode == CREATING:
        return history[0]
    intro, present_before = history[0], False
    for commit in history:
        version = git(repo, "show", f"{commit}:{card_readme()}")
        present = (
            cite_token in card_cite_tokens(version)
            if exact
            else cite_token in version
        )
        if present and not present_before:
            intro = commit
        present_before = present
    return intro


def trivial_anchor(line: str | None) -> bool:
    """The recipe's non-triviality predicate — blanks, bare braces, <~12 chars.

    One predicate, used at both steps: the fix this file guards is that it
    runs at the DECIDE step as well, not only when relocating.
    """
    if line is None:
        return True
    stripped = line.strip()
    return len(stripped) < 12 or bool(re.fullmatch(r"[{}()\[\],;:]+", stripped))


def decide(
    anchored: list[str], head: list[str], cited_line: int, *, guard: bool
) -> str:
    """Step 3 for ONE endpoint: is the cite current, defunct, or undecidable?

    `guard=False` is the recipe as it shipped: compare the anchor text to
    HEAD's text at the same offset and believe the answer. `guard=True`
    adds the rule the fixed prose prescribes — refuse the comparison when
    the anchor line is one that matches everywhere, and report it.
    """
    anchor = anchored[cited_line - 1] if cited_line <= len(anchored) else None
    if anchor is None:
        return DEFUNCT
    if guard and trivial_anchor(anchor):
        return DECLINE_TRIVIAL
    at_head = head[cited_line - 1] if cited_line <= len(head) else None
    return CURRENT if at_head == anchor else DEFUNCT


def relocate_by_name(anchor: str, head: list[str]) -> int | None:
    """Where a DEFINITION went, identified by its name rather than its line.

    None when the anchor is not a definition at all, and None when HEAD
    holds that name more than once — an ambiguous match is a decline here
    for the same reason it is one for the exact rule.
    """
    match = DEFN.match(anchor)
    if match is None:
        return None
    kind, name = match.groups()
    pattern = re.compile(
        r"^\s*(?:async\s+)?" + kind + r"\s+" + re.escape(name) + r"\s*\("
    )
    hits = [i + 1 for i, line in enumerate(head) if pattern.match(line)]
    return hits[0] if len(hits) == 1 else None


def relocate(
    anchored: list[str], head: list[str], cited_line: int, *, by_name: bool = False
) -> int | None:
    """Steps 3-4 for ONE endpoint: compare to HEAD, relocate the anchor text.

    `by_name=False` is the recipe as it shipped: exact full-line equality,
    so any edit to the anchor line itself reads as "the code is gone".
    `by_name=True` adds the rule the fixed prose prescribes — when the
    anchor is a definition and its exact text is ABSENT, retry on a unique
    match of that definition's name.

    Returns the line number the pass would write, or None where step 4
    declines (anchor gone, ambiguous, or trivial).
    """
    if cited_line > len(anchored):
        return None
    anchor = anchored[cited_line - 1]
    if cited_line <= len(head) and head[cited_line - 1] == anchor:
        return cited_line  # not defunct
    if trivial_anchor(anchor):
        return None  # matches everywhere: never guess
    hits = [i + 1 for i, line in enumerate(head) if line == anchor]
    if len(hits) == 1:
        return hits[0]
    if by_name and not hits:
        return relocate_by_name(anchor, head)
    return None  # gone, or ambiguous on the exact text: never guess


def repair(repo: Path, mode: str, *, by_name: bool = False) -> int | None:
    """The skill's per-cite recipe on a single-line cite."""
    readme = (repo / card_readme()).read_text(encoding="utf-8")
    cited_line = int(re.search(rf"{re.escape(CITED_FILE)}:(\d+)", readme).group(1))
    cite_token = f"{CITED_FILE}:{cited_line}"

    commit = anchor_commit(repo, cite_token, mode)
    anchored = git(repo, "show", f"{commit}:{CITED_FILE}").splitlines()
    head = (repo / CITED_FILE).read_text(encoding="utf-8").splitlines()
    return relocate(anchored, head, cited_line, by_name=by_name)


def repair_token(repo: Path, cite_token: str, *, occurrence: bool):
    """The recipe on ONE single-line cite token, occurrence rule on or off.

    `occurrence=False` is the recipe as it shipped: a substring presence
    test over the README text, with the cite identified by its token and
    nothing else. `occurrence=True` adds the two rules the fixed prose
    prescribes — presence is membership in the version's extracted cite
    tokens, and a token the card holds at two or more in-scope
    occurrences is DECLINED, since no walk can anchor them apart.

    Returns the line number the pass would write, None where step 4
    declines, or DECLINE_OCCURRENCE.
    """
    readme = (repo / card_readme()).read_text(encoding="utf-8")
    cited_line = int(cite_token.rsplit(":", 1)[1])
    if occurrence and card_cite_tokens(readme).count(cite_token) > 1:
        return DECLINE_OCCURRENCE
    commit = anchor_commit(repo, cite_token, AUTHORING, exact=occurrence)
    anchored = git(repo, "show", f"{commit}:{CITED_FILE}").splitlines()
    head = (repo / CITED_FILE).read_text(encoding="utf-8").splitlines()
    return relocate(anchored, head, cited_line)


def coherent(start: int, end: int) -> bool:
    """Does this pair still address a block?"""
    return start <= end and end - start <= MAX_PLAUSIBLE_SPAN


def repair_range(
    repo: Path, *, coherence: bool, by_name: bool = False
) -> tuple[int, int] | None:
    """The recipe on a RANGE cite, with the pair check switched on or off.

    `coherence=False` is the recipe as it shipped: map both endpoints,
    write whatever comes back. `coherence=True` adds the two rules the
    fixed prose prescribes — refuse a range that arrives incoherent, and
    refuse to write a repaired pair that no longer bounds a block.
    Returns the pair the pass would write, or None where it declines.
    """
    readme = (repo / card_readme()).read_text(encoding="utf-8")
    match = re.search(rf"{re.escape(CITED_FILE)}:(\d+)-(\d+)", readme)
    start, end = int(match.group(1)), int(match.group(2))
    if coherence and not coherent(start, end):
        return None  # arrived broken: report it, never re-map it

    commit = anchor_commit(repo, f"{CITED_FILE}:{start}-{end}", AUTHORING)
    anchored = git(repo, "show", f"{commit}:{CITED_FILE}").splitlines()
    head = (repo / CITED_FILE).read_text(encoding="utf-8").splitlines()
    mapped = [relocate(anchored, head, n, by_name=by_name) for n in (start, end)]
    if any(n is None for n in mapped):
        return None  # an endpoint declined; a half-mapped range is not a repair
    new_start, new_end = mapped
    if coherence and not coherent(new_start, new_end):
        return None  # both endpoints resolved, and together they bound nothing
    return new_start, new_end


def cite_rewrites(repo: Path) -> dict[str, int]:
    """One round of the decision phase over the card as it stands on disk.

    Maps every single-line cite token the round would rewrite to the number
    it would write. A cite verdicted current, or declined, proposes nothing.
    The card is read from the working tree and its history from `git log`,
    which is the whole defect: the two disagree until the pass commits.
    """
    readme = (repo / card_readme()).read_text(encoding="utf-8")
    rewrites = {}
    for token in card_cite_tokens(readme):
        new = repair_token(repo, token, occurrence=True)
        if isinstance(new, int) and new != int(token.rsplit(":", 1)[1]):
            rewrites[token] = new
    return rewrites


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


class DocumentedRangeCoherenceTest(unittest.TestCase):
    """A range names a block; two valid endpoints need not still bound one."""

    def test_core_skill_checks_the_repaired_pair(self) -> None:
        self.assertEqual(
            COHERENCE_GUARDED,
            documented_range_coherence(skill_step_one()),
            "refine-deck SKILL.md step 1 must check the PAIR a range repair "
            "is about to write (ordered, span still a block) and must refuse "
            "to re-map a range that arrives incoherent; without both, a pass "
            "emits a range that names nothing and the next pass certifies it",
        )

    def test_reference_sibling_prescribes_the_same_rule(self) -> None:
        self.assertEqual(
            documented_range_coherence(skill_step_one()),
            documented_range_coherence(reference_anchor_section()),
            "refine-deck's core skill and its reference sibling disagree on "
            "range repair; a pass following either would write a different "
            "set of ranges",
        )

    def test_the_shipped_rule_this_replaced_is_classified_as_unchecked(
        self,
    ) -> None:
        # The classifier's own proof that it can fail: the sentence the recipe
        # shipped from 2026-08-10 to 2026-09-07, which reads like a complete
        # instruction and is the whole of the defect.
        self.assertEqual(
            PAIR_UNCHECKED,
            documented_range_coherence(
                "A range (`file.py:120-140`) maps its endpoints independently "
                "and is rewritten only when both resolve."
            ),
        )

    def test_prose_that_never_mentions_a_range_is_unclassifiable(self) -> None:
        self.assertIsNone(
            documented_range_coherence(
                "Resolve the path — cards write `engine.py:N` for "
                "`goc/engine.py:N`; prefer a non-mirror match."
            )
        )


class RangeRepairTest(unittest.TestCase):
    """The endpoint divergence the deck census found, reproduced."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        build_range_repo(self.repo)
        self.addCleanup(self._tmp.cleanup)

    def test_documented_recipe_declines_the_incoherent_repair(self) -> None:
        self.assertEqual(
            COHERENCE_GUARDED,
            documented_range_coherence(skill_step_one()),
            "refine-deck SKILL.md step 1 no longer prescribes the pair check",
        )
        self.assertIsNone(
            repair_range(self.repo, coherence=True),
            "the recipe refine-deck ships must DECLINE a range repair whose "
            "endpoints would no longer bound a block, and report it — "
            "leaving the drifted cite, which at least points somewhere",
        )

    def test_unguarded_recipe_writes_an_inverted_range(self) -> None:
        # Not a spec — the fixture's own proof that it exercises the defect.
        # Both endpoints resolve, each is right on its own, and the pair the
        # pass writes runs backwards.
        self.assertEqual(
            (RANGE_START_IN_HEAD, RANGE_END_UNMOVED),
            repair_range(self.repo, coherence=False),
        )
        start, end = repair_range(self.repo, coherence=False)
        self.assertGreater(start, end)

    def test_a_range_that_arrives_broken_is_not_re_mapped(self) -> None:
        # The second rule: once a pass has written an inverted pair, its
        # endpoints anchor to whatever they were moved onto, so re-running
        # the recipe would launder the corruption into a fresh one.
        write_range_card(self.repo, RANGE_START_IN_HEAD, RANGE_END_UNMOVED)
        self.assertIsNone(repair_range(self.repo, coherence=True))

    def test_a_blown_out_span_is_not_a_block(self) -> None:
        # The other half of the pair check, which the deck census caught as
        # a 50-line body repaired into a 2512-line one.
        self.assertTrue(coherent(120, 140))
        self.assertFalse(coherent(120, 121 + MAX_PLAUSIBLE_SPAN))
        self.assertFalse(coherent(140, 120))


class DocumentedDecideGuardTest(unittest.TestCase):
    """The predicate that refuses a rewrite must also refuse a certification."""

    def test_core_skill_refuses_a_trivial_anchor_before_comparing(self) -> None:
        self.assertEqual(
            DECIDE_GUARDED,
            documented_decide_guard(skill_step_three()),
            "refine-deck SKILL.md step 3 must apply the non-triviality "
            "predicate BEFORE comparing the anchor to HEAD and DECLINE rather "
            "than verdict `current`; a blank or a brace matching at the cited "
            "offset is not evidence, and the verdict it produces is silent",
        )

    def test_reference_sibling_prescribes_the_same_rule(self) -> None:
        self.assertEqual(
            documented_decide_guard(skill_step_three()),
            documented_decide_guard(reference_deciding_paragraph()),
            "refine-deck's core skill and its reference sibling decide a cite "
            "differently; a pass following either would certify a different "
            "set of cites as current",
        )

    def test_the_shipped_rule_this_replaced_is_classified_as_unguarded(
        self,
    ) -> None:
        # The classifier's own proof that it can fail: the paragraph the
        # recipe shipped from 2026-08-10 to 2026-09-14. It NAMES the
        # predicate — which is why it read as complete — one step after the
        # comparison that needed it.
        self.assertEqual(
            DECIDE_UNGUARDED,
            documented_decide_guard(
                "Anchor text \u2260 the text at that line in HEAD \u2192 defunct. Then "
                "look for the anchor text in HEAD and rewrite the number only "
                "when the match is UNIQUE and the line is NON-TRIVIAL: skip "
                "blanks, bare braces, and anything under roughly 12 "
                "characters, which match everywhere."
            ),
        )

    def test_prose_that_reaches_no_verdict_is_unclassifiable(self) -> None:
        self.assertIsNone(
            documented_decide_guard(
                "Resolve the path \u2014 cards write `engine.py:N` for "
                "`goc/engine.py:N`; prefer a non-mirror match."
            )
        )

    def test_residue_table_carries_the_undecidable_decline(self) -> None:
        # The verdict has to land somewhere a human reads. Absorbed back into
        # `current` it is the silence the whole anchored recipe replaced.
        rows = [
            line
            for line in reference_anchor_section().splitlines()
            if line.startswith("|") and "trivial anchor" in line
        ]
        self.assertEqual(
            1,
            len(rows),
            "refine-deck reference.md § Citation anchor check must carry "
            "exactly one residue row for the trivial-anchor decline",
        )
        row = _flat(rows[0])
        self.assertIn("undecidable", row)
        self.assertIn(
            "no evidence the cite is current",
            row,
            "the residue row must say what the decline means on the DECIDE "
            "side, not only that the address cannot be relocated",
        )


class TrivialAnchorDecideTest(unittest.TestCase):
    """A blank anchor cannot decay, so its false clean is permanent."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        build_trivial_anchor_repo(self.repo)
        self.addCleanup(self._tmp.cleanup)

    def verdict(self, *, guard: bool) -> str:
        readme = (self.repo / card_readme()).read_text(encoding="utf-8")
        cited = int(
            re.search(rf"{re.escape(CITED_FILE)}:(\d+)", readme).group(1)
        )
        commit = anchor_commit(self.repo, f"{CITED_FILE}:{cited}", AUTHORING)
        anchored = git(self.repo, "show", f"{commit}:{CITED_FILE}").splitlines()
        head = (self.repo / CITED_FILE).read_text(encoding="utf-8").splitlines()
        return decide(anchored, head, cited, guard=guard)

    def test_documented_recipe_declines_the_undecidable_cite(self) -> None:
        self.assertEqual(
            DECIDE_GUARDED,
            documented_decide_guard(skill_step_three()),
            "refine-deck SKILL.md step 3 no longer refuses a trivial anchor",
        )
        self.assertEqual(
            DECLINE_TRIVIAL,
            self.verdict(guard=True),
            "the recipe refine-deck ships must DECLINE a cite whose anchor "
            "line is blank and report it, rather than certify it `current` "
            "on a match that carries no information",
        )

    def test_unguarded_recipe_certifies_a_cite_that_names_nothing(self) -> None:
        # Not a spec \u2014 the fixture's own proof that it exercises the defect.
        # The anchor is "", HEAD's line 5 is "", the texts match, and the
        # function the card is about sits six lines further down.
        self.assertEqual(CURRENT, self.verdict(guard=False))
        head = (self.repo / CITED_FILE).read_text(encoding="utf-8").splitlines()
        self.assertEqual("", head[TRIVIAL_CITED - 1])
        self.assertEqual(
            "def target(payload):", head[TRIVIAL_TARGET_IN_HEAD - 1]
        )

    def test_a_bare_brace_is_refused_like_a_blank(self) -> None:
        # The predicate is one predicate; the blank is only its worst case.
        self.assertTrue(trivial_anchor(""))
        self.assertTrue(trivial_anchor("    }"))
        self.assertTrue(trivial_anchor("        });"))
        self.assertTrue(trivial_anchor("    return 0"))
        self.assertFalse(trivial_anchor("def target(payload):"))


class DocumentedOccurrenceRuleTest(unittest.TestCase):
    """A cite is an occurrence in a card, not a token the card contains."""

    def test_core_skill_anchors_per_occurrence(self) -> None:
        self.assertEqual(
            OCCURRENCE_GUARDED,
            documented_occurrence_rule(skill_step_two()),
            "refine-deck SKILL.md step 2 must test presence by MEMBERSHIP in "
            "the version's extracted cite tokens (so `path:N` does not read "
            "as present inside `path:N-M`) and must DECLINE a token the card "
            "holds at two or more occurrences; without both, the walk hands a "
            "cite an anchor decided by a different cite's history",
        )

    def test_reference_sibling_prescribes_the_same_rule(self) -> None:
        self.assertEqual(
            documented_occurrence_rule(skill_step_two()),
            documented_occurrence_rule(reference_anchor_section()),
            "refine-deck's core skill and its reference sibling anchor cites "
            "differently; a pass following either would read a different "
            "commit for the same cite",
        )

    def test_the_shipped_rule_this_replaced_is_classified_as_token_only(
        self,
    ) -> None:
        # The classifier's own proof that it can fail: the sentence the recipe
        # shipped from 2026-08-17 to 2026-09-14. It calls the token "exact",
        # which is why it read as precise — the word modifies the token, while
        # the test around it is still a substring search.
        self.assertEqual(
            TOKEN_WALK,
            documented_occurrence_rule(
                "Find it by walking the card's own history: list `git log "
                "--follow --format=%H -- <deck>/<card>/README.md` oldest to "
                "newest, read the README at each commit, and take the newest "
                "commit at which the exact cite token turns from absent to "
                "present."
            ),
        )

    def test_prose_that_never_walks_the_history_is_unclassifiable(self) -> None:
        self.assertIsNone(
            documented_occurrence_rule(
                "Resolve the path \u2014 cards write `engine.py:N` for "
                "`goc/engine.py:N`; prefer a non-mirror match."
            )
        )

    def test_a_range_token_does_not_contain_the_single_line_token(self) -> None:
        # The substring half in one line: the same text answers the two
        # presence tests differently, and only one of the answers is a cite.
        prose = f"`{CITED_FILE}:6-8` is the block this card is about."
        self.assertIn(COLLIDE_SINGLE_CITE, prose)
        self.assertNotIn(COLLIDE_SINGLE_CITE, card_cite_tokens(prose))

    def test_residue_table_carries_the_ambiguous_occurrence_decline(self) -> None:
        rows = [row for row in residue_rows() if "ambiguous occurrence" in row]
        self.assertEqual(
            1,
            len(rows),
            "refine-deck reference.md \u00a7 Citation anchor check must carry "
            "exactly one residue row for the repeated-token decline; a "
            "decline absorbed back into a rewrite is the silence the anchored "
            "recipe replaced",
        )


class ResidueAccountingTest(unittest.TestCase):
    """Both surfaces must count the declines the table actually carries.

    The core skill's summary line had been naming three reasons since the
    range card added a fourth, which is the failure mode this guards: a
    decline reason lands in the reference table and the surface an agent
    reads never mentions it.
    """

    WORDS = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7}

    def test_reference_counts_its_own_residue_rows(self) -> None:
        match = re.search(
            r"declines split (\w+) ways", reference_anchor_section()
        )
        self.assertIsNotNone(
            match,
            "refine-deck reference.md \u00a7 Citation anchor check no longer "
            "says how many ways the declines split",
        )
        self.assertEqual(
            len(residue_rows()),
            self.WORDS.get(match.group(1)),
            "the reference's decline count and its residue table disagree",
        )

    def test_core_skill_names_every_decline_the_table_carries(self) -> None:
        match = re.search(
            r"Cites the recipe declines \u2014 (.+?) \u2014 are REPORTED",
            skill_citation_section(),
            re.S,
        )
        self.assertIsNotNone(
            match,
            "refine-deck SKILL.md no longer lists what the citation recipe "
            "declines",
        )
        named = [part.strip() for part in match.group(1).split(",")]
        self.assertEqual(
            len(residue_rows()),
            len(named),
            "refine-deck SKILL.md names {} decline reasons while the "
            "reference's residue table carries {}; an agent reads the core "
            "skill and would never learn the missing one".format(
                len(named), len(residue_rows())
            ),
        )


class DocumentedIdempotenceCheckTest(unittest.TestCase):
    """The only guard that sees the class rather than the instances."""

    def test_core_skill_closes_the_step_with_a_re_run(self) -> None:
        self.assertTrue(
            documented_idempotence_check(skill_citation_section()),
            "refine-deck SKILL.md \u00a7 Defunct file:line citations must end "
            "by re-running the decision phase over what the pass just wrote "
            "and asserting zero further repairs; every per-cite rule passes "
            "on a pass repairing its own output",
        )

    def test_reference_sibling_prescribes_the_same_check(self) -> None:
        self.assertEqual(
            documented_idempotence_check(skill_citation_section()),
            documented_idempotence_check(reference_anchor_section()),
            "refine-deck's core skill and its reference sibling disagree on "
            "whether the citation pass has to prove itself a fixed point",
        )

    def test_prose_without_the_re_run_is_classified_as_missing(self) -> None:
        # The classifier's own proof that it can fail: the closing sentence
        # the recipe shipped with, which stops at reporting the declines.
        self.assertFalse(
            documented_idempotence_check(
                "Cites the recipe declines \u2014 trivial anchor, anchor gone, "
                "ambiguous, incoherent pair \u2014 are REPORTED for a human to "
                "read, never silently skipped."
            )
        )


class CollidingCiteAnchorTest(unittest.TestCase):
    """Two cites, one number: whose history decides the anchor?"""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        build_collision_repo(self.repo)
        self.addCleanup(self._tmp.cleanup)

    def test_documented_recipe_repairs_the_cite_onto_the_code_it_named(
        self,
    ) -> None:
        self.assertEqual(
            OCCURRENCE_GUARDED,
            documented_occurrence_rule(skill_step_two()),
            "refine-deck SKILL.md step 2 no longer pins the walk to an "
            "occurrence",
        )
        self.assertEqual(
            ALPHA_LINE_IN_COLLIDE_HEAD,
            repair_token(self.repo, COLLIDE_SINGLE_CITE, occurrence=True),
            "the recipe refine-deck ships must anchor a cite on the commit "
            "that wrote THAT cite, not on the older commit where a range in "
            "the same card happened to spell its number",
        )

    def test_token_walk_moves_the_cite_onto_the_other_cites_code(self) -> None:
        # Not a spec \u2014 the fixture's own proof that it exercises the defect.
        # The substring walk anchors the helper cite at the filing commit,
        # where line 6 held the target's `def`, and relocates it there:
        # unique, confident, and the wrong function.
        self.assertEqual(
            TARGET_LINE_IN_COLLIDE_HEAD,
            repair_token(self.repo, COLLIDE_SINGLE_CITE, occurrence=False),
        )
        head = (self.repo / CITED_FILE).read_text(encoding="utf-8").splitlines()
        self.assertEqual(
            "def target(payload):", head[TARGET_LINE_IN_COLLIDE_HEAD - 1]
        )
        self.assertEqual(
            '    return "alpha sentinel value"',
            head[ALPHA_LINE_IN_COLLIDE_HEAD - 1],
        )

    def test_a_token_the_card_holds_twice_is_declined(self) -> None:
        # Convergence: a later pass lands the second cite on the same number.
        # Both occurrences now share one history, so token-exactness buys
        # nothing and the honest answer is a decline.
        write_repeated_cite_card(self.repo, COLLIDE_SINGLE_LINE)
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "a pass lands both cites on :6")
        self.assertEqual(
            DECLINE_OCCURRENCE,
            repair_token(self.repo, COLLIDE_SINGLE_CITE, occurrence=True),
            "the recipe refine-deck ships must DECLINE a token the card holds "
            "at two or more in-scope occurrences and report it, rather than "
            "rewrite both from one occurrence's history",
        )
        self.assertEqual(
            TARGET_LINE_IN_COLLIDE_HEAD,
            repair_token(self.repo, COLLIDE_SINGLE_CITE, occurrence=False),
            "fixture check: the unguarded recipe rewrites both occurrences "
            "and reports a successful repair",
        )


class DocumentedDefinitionNameRuleTest(unittest.TestCase):
    """A cite naming a function means the FUNCTION, not the line it sat on."""

    def test_core_skill_relocates_a_definition_by_its_name(self) -> None:
        self.assertEqual(
            NAME_GUARDED,
            documented_definition_rule(skill_step_four()),
            "refine-deck SKILL.md step 4 must retry a `def`/`class` anchor on "
            "a unique match of its NAME when the exact line is gone, DECLINE "
            "when HEAD holds that name twice, and leave the range pair check "
            "deciding; without the retry a function that gained a parameter "
            "reads as refactored away on this pass and on every later one",
        )

    def test_reference_sibling_prescribes_the_same_rule(self) -> None:
        self.assertEqual(
            documented_definition_rule(skill_step_four()),
            documented_definition_rule(reference_anchor_section()),
            "refine-deck's core skill and its reference sibling relocate a "
            "moved definition differently; a pass following either would "
            "repair a different set of cites",
        )

    def test_the_shipped_rule_this_replaced_is_classified_as_line_only(
        self,
    ) -> None:
        # The classifier's own proof that it can fail: step 4 as the recipe
        # shipped from 2026-08-10 to 2026-09-14. It reads as complete because
        # its refusal to guess IS complete; what it gets wrong is what the
        # anchor identifies.
        self.assertEqual(
            EXACT_LINE_ONLY,
            documented_definition_rule(
                "Relocate the anchor text in HEAD and rewrite the number "
                "**only** on a UNIQUE match \u2014 step 3 already refused the "
                "lines that match everywhere. Never guess."
            ),
        )

    def test_prose_that_never_relocates_is_unclassifiable(self) -> None:
        self.assertIsNone(
            documented_definition_rule(
                "Resolve the path \u2014 cards write `engine.py:N` for "
                "`goc/engine.py:N`; prefer a non-mirror match."
            )
        )

    def test_residue_table_stops_reading_an_absent_anchor_as_a_refactor(
        self,
    ) -> None:
        # The decline is honest, and its advice has to be too: a reader told
        # the code was refactored away goes looking for a defect that is
        # still live, finds nothing at the address, and may close the card.
        rows = [
            line
            for line in reference_anchor_section().splitlines()
            if line.startswith("|") and "anchor text absent" in line
        ]
        self.assertEqual(
            1,
            len(rows),
            "refine-deck reference.md \u00a7 Citation anchor check must carry "
            "exactly one residue row for the absent-anchor decline",
        )
        row = _flat(rows[0])
        self.assertIn(
            "unique `def`/`class` of that name",
            row,
            "the absent-anchor row must say the name test ran too, or the "
            "decline reads as stronger evidence than it is",
        )
        self.assertIn(
            "renamed",
            row,
            "the absent-anchor row must offer a reading other than 'the code "
            "was refactored away', which is what sent readers looking for a "
            "defect that is still live",
        )

    def test_residue_table_carries_the_ambiguous_name_match(self) -> None:
        rows = [row for row in residue_rows() if "ambiguous match" in row]
        self.assertEqual(1, len(rows))
        full = [
            line
            for line in reference_anchor_section().splitlines()
            if line.startswith("|") and "ambiguous match" in line
        ]
        self.assertIn(
            "definition name head holds more than once",
            _flat(full[0]),
            "the name rule's own decline has to land in the residue table; "
            "a second definition of the name is where it declines",
        )


class SignatureDriftRelocateTest(unittest.TestCase):
    """The anchor line changed; the function it named did not move away."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        build_signature_drift_repo(self.repo)
        self.addCleanup(self._tmp.cleanup)

    def test_documented_recipe_finds_the_function_that_gained_a_parameter(
        self,
    ) -> None:
        self.assertEqual(
            NAME_GUARDED,
            documented_definition_rule(skill_step_four()),
            "refine-deck SKILL.md step 4 no longer relocates by definition name",
        )
        mode = documented_anchor(skill_step_two())
        self.assertEqual(
            SIG_TARGET_IN_HEAD,
            repair(self.repo, mode, by_name=True),
            "the recipe refine-deck ships must move a cite whose `def` line "
            "gained a keyword-only parameter onto the function it names",
        )

    def test_exact_equality_declines_a_function_one_grep_away(self) -> None:
        # Not a spec \u2014 the fixture's own proof that it exercises the defect.
        # The anchor text is nowhere in HEAD, so the exact rule reports it
        # gone; the function is right there, uniquely named, four lines below
        # where the cite points.
        self.assertIsNone(repair(self.repo, AUTHORING))
        head = (self.repo / CITED_FILE).read_text(encoding="utf-8").splitlines()
        self.assertEqual(SIG_HEAD_DEF, head[SIG_TARGET_IN_HEAD - 1])
        self.assertEqual(
            1, sum(1 for line in head if line.startswith("def target("))
        )

    def test_a_name_head_holds_twice_is_declined(self) -> None:
        # The constraint that keeps the relaxation honest: an overload in a
        # mirror tree, or a method beside a module-level function, and the
        # matcher has nothing to choose with. Nearest-match is not available.
        head = (self.repo / CITED_FILE).read_text(encoding="utf-8").splitlines()
        write_source(
            self.repo,
            head + ["", "def target(payload, *, probe=True):", "    return None"],
        )
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "a second definition of that name")
        self.assertIsNone(
            repair(self.repo, AUTHORING, by_name=True),
            "the recipe refine-deck ships must DECLINE a definition name HEAD "
            "holds more than once and report it, rather than take the first",
        )


class SignatureDriftRangeTest(unittest.TestCase):
    """The name rule feeds the endpoint mapper; the pair check still decides."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        build_signature_range_repo(self.repo)
        self.addCleanup(self._tmp.cleanup)

    def test_documented_recipe_declines_the_range_the_name_rule_inverts(
        self,
    ) -> None:
        self.assertEqual(
            NAME_GUARDED,
            documented_definition_rule(skill_step_four()),
            "refine-deck SKILL.md step 4 no longer relocates by definition name",
        )
        self.assertEqual(
            COHERENCE_GUARDED,
            documented_range_coherence(skill_step_one()),
            "refine-deck SKILL.md step 1 no longer prescribes the pair check",
        )
        self.assertIsNone(
            repair_range(self.repo, coherence=True, by_name=True),
            "the recipe refine-deck ships must DECLINE a range whose start "
            "the name rule relocates past an end that stayed put \u2014 seven of "
            "the twelve cites this rule was written for are range endpoints",
        )

    def test_the_name_rule_is_what_makes_the_pair_check_load_bearing_here(
        self,
    ) -> None:
        # Not a spec \u2014 the fixture's own proof. With the pair check off, the
        # mapped pair IS emitted and runs backwards, so the decline above came
        # from the pair check rather than from an endpoint that never mapped.
        self.assertEqual(
            (SIG_RANGE_START_IN_HEAD, SIG_RANGE_END_UNMOVED),
            repair_range(self.repo, coherence=False, by_name=True),
        )
        start, end = repair_range(self.repo, coherence=False, by_name=True)
        self.assertGreater(start, end)
        self.assertIsNone(
            repair_range(self.repo, coherence=False, by_name=False),
            "fixture check: without the name rule the start never maps, so "
            "the same range declines one step earlier and for a reason that "
            "hides the moved function",
        )


class DocumentedRerunOrderTest(unittest.TestCase):
    """The re-run reads history, so it has to come after the commit."""

    # The closing paragraphs as they shipped from 2026-09-14: each re-runs,
    # and neither says when the commit happens.
    SHIPPED_SKILL = (
        "End the step by RE-RUNNING the decision phase over the cards you just "
        "wrote: a correctly repaired deck is a FIXED POINT, so it must propose "
        "ZERO further repairs. A non-empty second round is a recipe defect to "
        "file, not more rewrites to apply."
    )
    SHIPPED_REFERENCE = (
        "**Close the step by re-running it.** After applying the rewrites, run "
        "the decision phase again over the cards just written and assert it "
        "proposes ZERO further repairs."
    )

    def test_core_skill_commits_before_it_re_runs(self) -> None:
        self.assertEqual(
            COMMIT_THEN_RERUN,
            documented_rerun_order(skill_citation_section()),
            "refine-deck SKILL.md § Defunct file:line citations must commit "
            "the rewrites BEFORE re-running the decision phase, and say why: "
            "the walk reads `git log`, so over an uncommitted rewrite the "
            "re-run anchors a correct cite on a retired occurrence and "
            "proposes moving it",
        )

    def test_reference_sibling_prescribes_the_same_order(self) -> None:
        self.assertEqual(
            documented_rerun_order(skill_citation_section()),
            documented_rerun_order(reference_anchor_section()),
            "refine-deck's core skill and its reference sibling disagree on "
            "whether the rewrites are committed before the re-run",
        )

    def test_the_shipped_order_this_replaced_is_classified_as_unordered(
        self,
    ) -> None:
        # The classifier's own proof that it can fail.
        for prose in (self.SHIPPED_SKILL, self.SHIPPED_REFERENCE):
            with self.subTest(prose=prose[:40]):
                self.assertEqual(RERUN_UNORDERED, documented_rerun_order(prose))

    def test_the_order_without_its_reason_is_classified_as_unordered(
        self,
    ) -> None:
        self.assertEqual(
            RERUN_UNORDERED,
            documented_rerun_order(
                "Commit the rewrites, then re-run the decision phase and "
                "assert it proposes ZERO further repairs."
            ),
        )

    def test_prose_without_a_re_run_is_unclassifiable(self) -> None:
        self.assertIsNone(
            documented_rerun_order(
                "Commit the rewrites as a `chore(deck): hygiene pass` commit."
            )
        )

    def test_residue_table_carries_the_retired_occurrence_decline(self) -> None:
        rows = [row for row in residue_rows() if "retired occurrence" in row]
        self.assertEqual(
            1,
            len(rows),
            "refine-deck reference.md § Citation anchor check must carry "
            "exactly one residue row for the retired-occurrence shape, so a "
            "pass that meets one before its commit reads it as a known "
            "decline rather than as a repair to apply",
        )


class RetiredOccurrenceRerunTest(unittest.TestCase):
    """A second pass writes a number the card retired: when may it re-run?"""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        build_retired_occurrence_repo(self.repo)
        self.addCleanup(self._tmp.cleanup)

    def run_pass(self, *, commit_before_rerun: bool) -> dict[str, int]:
        """Round one, apply it, commit or not, then return round two."""
        self.assertEqual(
            {
                f"{CITED_FILE}:{RETIRE_PASS_1[0]}": RETIRE_PASS_2[0],
                f"{CITED_FILE}:{RETIRE_PASS_1[1]}": RETIRE_PASS_2[1],
            },
            cite_rewrites(self.repo),
            "fixture check: round one must repair both cites correctly, so "
            "whatever round two proposes is the pass repairing its own output",
        )
        write_retire_card(self.repo, *RETIRE_PASS_2)
        if commit_before_rerun:
            git(self.repo, "add", "-A")
            git(self.repo, "commit", "-q", "-m", "hygiene pass: repair both cites")
        return cite_rewrites(self.repo)

    def test_documented_order_re_runs_to_a_fixed_point(self) -> None:
        order = documented_rerun_order(skill_citation_section())
        self.assertIsNotNone(
            order, "refine-deck SKILL.md no longer closes the step with a re-run"
        )
        self.assertEqual(
            {},
            self.run_pass(commit_before_rerun=order == COMMIT_THEN_RERUN),
            "the re-run refine-deck ships must find a correctly repaired card "
            "a fixed point; a proposal here moves a cite the pass just wrote "
            "correctly onto the code of the cite that held its number before",
        )

    def test_re_run_before_the_commit_proposes_a_false_repair(self) -> None:
        # Not a spec — the fixture's own proof that it exercises the defect.
        # The fresh `:11` is right, and the proposal moves it onto the decoy:
        # the sentinel the card's OTHER cite names, which is why it is unique.
        self.assertEqual(
            {RETIRED_TOKEN: RETIRE_PASS_2[1]},
            self.run_pass(commit_before_rerun=False),
        )
        head = (self.repo / CITED_FILE).read_text(encoding="utf-8").splitlines()
        self.assertEqual("def target(payload):", head[RETIRE_PASS_2[0] - 1])
        self.assertEqual(
            '    return "decoy sentinel that is long and unique"',
            head[RETIRE_PASS_2[1] - 1],
        )

    def test_the_colliding_occurrence_is_in_the_cards_past(self) -> None:
        # Neither occurrence guard can see it: the proposal came through the
        # set-membership presence test, and the token occurs once in the card.
        # The walk collides with the FILING commit, where `:11` was the decoy
        # cite's number until the first pass moved it.
        self.run_pass(commit_before_rerun=False)
        readme = (self.repo / card_readme()).read_text(encoding="utf-8")
        self.assertEqual(1, card_cite_tokens(readme).count(RETIRED_TOKEN))
        history = git(self.repo, "log", "--format=%H", "--", card_readme()).split()
        self.assertEqual(
            history[-1],
            anchor_commit(self.repo, RETIRED_TOKEN, AUTHORING, exact=True),
        )
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "hygiene pass: repair both cites")
        self.assertEqual(
            git(self.repo, "rev-parse", "HEAD").strip(),
            anchor_commit(self.repo, RETIRED_TOKEN, AUTHORING, exact=True),
            "once committed, the fresh cite anchors on the commit that wrote it",
        )


if __name__ == "__main__":
    unittest.main()
