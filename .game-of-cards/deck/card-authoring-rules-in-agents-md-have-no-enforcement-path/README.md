---
title: card-authoring-rules-in-agents-md-have-no-enforcement-path
summary: "AGENTS.md § 'Card authoring rules' states four rules for cards filed in this repo; three of them (English only, no verbatim discussion quotes, no internal event/project/person names) have no enforcement anywhere — not in `goc new`, not in `goc move`, not in `goc validate`, not in `goc quality-pass`. Today's hygiene pass found a live English-only violation that had been in the deck nine days and passed every guard clean, because all eight `TITLE_ANTIPATTERNS` (goc/engine.py:5493-5502) are jargon and character-class regexes that a well-formed ASCII slug in another language satisfies. The other two rules were audited clean today, so this is a gap to close before it bites, not a recurring family."
status: open
stage: null
contribution: low
created: "2026-07-27T02:58:31Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, infra]
definition_of_done: |
  - [ ] PROCESS: pick the scope — enforce all three unguarded rules, or only English-only — and pick the surface (a `goc validate` check, a `goc quality-pass` dimension, or a repo-local `tests/` guard), recorded in log.md. The rules are project-local, so a goc-shipped check would need a project-local opt-in.
  - [ ] TDD: `reproduce.py` exits zero — some guard in the filing path flags the historical non-English title.
  - [ ] TDD: the new check proves its own sensitivity — a test feeds it a known offender and asserts it is caught, not only that the current deck is clean (per `static-source-guards-never-prove-they-can-catch-an-offender`).
  - [ ] TDD: no false positive on the 679 titles currently in the deck.
  - [ ] MECHANICAL: `uv run goc validate` passes and `python scripts/sync_plugin_assets.py --check` is green.
---

# AGENTS.md's card-authoring rules have no enforcement path

## Location

`AGENTS.md` § "Card authoring rules" states four rules for cards filed in this
repo. Only the fourth is enforced:

| Rule | Enforced by |
|---|---|
| English only — titles, summaries, body, DoD | **nothing** |
| No direct quotes from discussions | **nothing** |
| No references to internal events / projects / people by name | **nothing** |
| YAML block style for the four edge list fields | the frontmatter emitter |

The nearest thing to a guard is `goc/engine.py:5493-5502`:

```python
TITLE_ANTIPATTERNS = [
    (re.compile(r"\br\d+\b"), "internal investigation-round reference (rN); ..."),
    (re.compile(r"\bpath-\d+\b"), "sub-investigation step number; ..."),
    (re.compile(r"\bphase-\d+\b"), "internal sequence reference; ..."),
    (re.compile(r"\bbug-\d+\b"), "bug-tracker numbering; ..."),
    (re.compile(r"_md_|_py_"), "source-file infix; ..."),
    (re.compile(r"[a-z][A-Z]"), "camelCase token; ..."),
    (re.compile(r"[^a-zA-Z0-9\s_-]"), "math/symbol or non-ASCII character; ..."),
    (re.compile(r"_"), "underscore in slug; ..."),
]
```

`goc new` (`engine.py:5587`), `goc move` (`engine.py:6054`) and
`goc quality-pass` (`engine.py:4268`) all route through the single predicate
`_check_title_antipatterns` built from that list.

## What's broken

Every rule in the table is a jargon shape or a character class. None is about
*language*. Row 7 rejects non-ASCII characters, which is the closest miss —
it would catch `größe` — but a language written in plain ASCII sails through.
A well-formed lower-kebab slug in German, French or Spanish is, to this
predicate, indistinguishable from one in English.

That is not hypothetical. It is what actually happened.

## Empirical evidence

The card `openclaw-plugin-skills-erzwingen-mehrfach-reads-pro-session`
("OpenClaw plugin skills force multiple reads per session") was filed
2026-07-18 and sat in the deck until a refine-deck pass renamed it by hand on
2026-07-27 — nine days, with `goc quality-pass --status all` reporting "Title
antipatterns: clean" the whole time. `reproduce.py` in this directory replays
it against the live predicate, with a control title so a dead scanner cannot
masquerade as a passing one:

```
$ uv run python .game-of-cards/deck/card-authoring-rules-in-agents-md-have-no-enforcement-path/reproduce.py
antipattern rules defined:   8
control title 'r88-runSimulation-fails'
  -> 2 hit(s): ['internal investigation-round reference (rN); describe the *observable problem* instead', 'camelCase token; lower-kebab the intent']
offending title 'openclaw-plugin-skills-erzwingen-mehrfach-reads-pro-session'
  -> 0 hit(s): []

FAIL — the guard is alive (it flags the control) and still accepts a title that
breaks AGENTS.md's English-only rule.
```

The same pass audited the other two unguarded rules and both came back clean:
no deck card names the internal meeting or project that AGENTS.md calls out by
name, and the `> `-quote hits were all quotations of code and docs, which the
rule permits. So the live instance count is **one**, on one of three rules.

## Why it matters

The three unenforced rules are not stylistic in the same way. English-only is a
readability rule and its failure is visible and cheap to reverse — this one
took a `goc move`. The other two are confidentiality rules: they exist to keep
verbatim discussion, internal project names and individual attributions out of
a permanent artifact that ships in a public repository. A violation of those is
found the same way this one was — by somebody happening to read the card — and
by then it is in the git history.

That asymmetry is the argument for a guard even at one observed instance: the
rule whose violation was cheap is the one that got caught, and it got caught by
luck rather than by a check.

## Scope note — what this card is *not*

This is a single-instance finding, deliberately filed narrow. It is **not** a
member of the family tracked by
[doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them](../doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them/),
which is about prose claims that restate tree-derived facts and go stale; the
rules here are authoring conventions with no tree state to derive from, and a
guard for them would look nothing like a `test_guidance_accuracy.py` pin. It is
adjacent to that card, not an eighth instance of it.

It does inherit one requirement from
[static-source-guards-never-prove-they-can-catch-an-offender](../static-source-guards-never-prove-they-can-catch-an-offender/):
whatever check lands must be tested against a known offender, not merely
asserted to find nothing in a clean tree. The `reproduce.py` here is written
that way already — it fails loudly if its own control stops being flagged.

The instance that surfaced this is
[openclaw-plugin-skills-force-repeated-reads-every-session](../openclaw-plugin-skills-force-repeated-reads-every-session/)
(the renamed card); its `log.md` carries the rename rationale.

## Decision (deferred, gate left at `none`)

Two independent questions, both carried by the first DoD box:

1. **Scope** — all three rules, or English-only? A language check is a
   dependency-free heuristic (stop-word lists, or a wordlist intersection over
   slug tokens) with a real false-positive budget to spend on 679 existing
   titles. A no-internal-names check needs a project-local denylist, which is
   easy but must live somewhere that is not itself public.
2. **Surface** — these are *project-local* rules from this repo's AGENTS.md,
   not goc semantics, so a goc-shipped `validate` check would need an opt-in
   (`.game-of-cards/` config or canonical-tags-style registration). The
   cheapest honest option may be a repo-local guard in `tests/`, which needs no
   engine change and no consumer-facing surface at all.
