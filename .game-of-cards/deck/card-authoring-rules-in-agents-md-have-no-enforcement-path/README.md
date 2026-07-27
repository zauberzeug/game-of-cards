---
title: card-authoring-rules-in-agents-md-have-no-enforcement-path
summary: "RESOLVED for the English-only rule. AGENTS.md § 'Card authoring rules' states four rules for cards filed in this repo; three of them (English only, no verbatim discussion quotes, no internal event/project/person names) had no enforcement anywhere, because all eight `TITLE_ANTIPATTERNS` (goc/engine.py:5493-5502) are jargon and character-class regexes that a well-formed ASCII slug in another language satisfies — a live violation sat in the deck nine days and passed every guard clean. `scripts/check_card_language.py` now scans every card's title, summary and DoD from a pre-commit hook and from the regression suite; it is repo-local because the rule is this repo's convention, not goc semantics. The two confidentiality rules stay unguarded on the record: both audited clean, and mechanizing them needs a decision nobody has made."
status: done
stage: null
contribution: low
created: "2026-07-27T02:58:31Z"
closed_at: "2026-07-27T05:03:14Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, infra]
definition_of_done: |
  - [x] PROCESS: pick the scope — enforce all three unguarded rules, or only English-only — and pick the surface (a `goc validate` check, a `goc quality-pass` dimension, or a repo-local `tests/` guard), recorded in log.md. The rules are project-local, so a goc-shipped check would need a project-local opt-in.
  - [x] TDD: `reproduce.py` exits zero — some guard in the filing path flags the historical non-English title.
  - [x] TDD: the new check proves its own sensitivity — a test feeds it a known offender and asserts it is caught, not only that the current deck is clean (per `static-source-guards-never-prove-they-can-catch-an-offender`).
  - [x] TDD: no false positive on the 679 titles currently in the deck.
  - [x] MECHANICAL: `uv run goc validate` passes and `python scripts/sync_plugin_assets.py --check` is green.
worker: {who: "claude[bot]", where: main}
---

# AGENTS.md's card-authoring rules have no enforcement path

## Resolution

**English-only is now guarded; the two confidentiality rules are still not.**

`scripts/check_card_language.py` scans every card's `title`, `summary` and
`definition_of_done` and flags non-English text. It runs from two places: the
`card-language` pre-commit hook, and `tests/test_card_authoring_rules.py` in
CI. Because goc's auto-commit shells out to `git commit` without
`--no-verify` (`engine._git_auto_commit`), the pre-commit hook fires on `goc
new --commit` as well — so the guard sits in the filing path after all, not
only downstream of it.

It is repo-local by design. English-only is *this repo's* convention, not goc
semantics: a team running goc on a German codebase is entitled to a German
deck, so nothing was added to `TITLE_ANTIPATTERNS` and no consumer-facing
opt-in was invented. `reproduce.py` now asserts both halves of that — the
repo-local guard catches the title, and the engine predicate still does not.

Detection is precision-first, in two layers: 236 marker words that are common
in German, French, Spanish/Portuguese, Italian or Dutch and are never English
(homographs like `die`, `war`, `tag`, `todo`, `per`, `non`, `com`, `sans` are
deliberately excluded), plus nine German derivational endings (`-ung`,
`-keit`, `-lich`, …) that have zero collisions across the 4,363 distinct
tokens in the deck's scanned fields. Slug titles drop articles, so the
historical offender carried no function words at all — the suffix layer is
what makes content-word slugs catchable. Measured: 0 findings on all 681 live
cards, and both layers fire independently in the test suite.

The known limit is recall, stated plainly in the module docstring: a
non-English title built entirely from cognates
(`konfiguration-migration-problem`) still passes. This raises the floor from
"nothing checks" to "the realistic cases fail the commit"; it is not a
language classifier.

Card bodies are **out of scope** even though AGENTS.md names them. Bodies
legitimately quote non-English identifiers and upstream error strings — and
several cards, including this one, quote the offending title itself, so a body
scan would report the deck's own record of the bug as a violation.

## Location

`AGENTS.md` § "Card authoring rules" states four rules for cards filed in this
repo. When this card was filed, only the fourth was enforced:

| Rule | Enforced by (at filing) | Enforced by (now) |
|---|---|---|
| English only — titles, summaries, body, DoD | **nothing** | `scripts/check_card_language.py`, on title/summary/DoD |
| No direct quotes from discussions | **nothing** | **nothing** |
| No references to internal events / projects / people by name | **nothing** | **nothing** |
| YAML block style for the four edge list fields | the frontmatter emitter | the frontmatter emitter |

The nearest thing to a guard was `goc/engine.py:5493-5502`, and it still is
for every rule but the first:

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
it against both predicates, each with a control title so a dead scanner cannot
masquerade as a passing one:

```
$ uv run python .game-of-cards/deck/card-authoring-rules-in-agents-md-have-no-enforcement-path/reproduce.py
goc-shipped filing-path guard (engine._check_title_antipatterns)
  rules defined:                 8
  control 'r88-runSimulation-fails' -> 2 hit(s)
  offender -> 0 hit(s): []
repo-local English-only guard (scripts/check_card_language.py)
  marker words:                  236
  control 'konfiguration-wird-nicht-geladen' -> 2 hit(s)
  offender -> 2 hit(s): ["German marker word 'erzwingen'", "German marker word 'mehrfach'"]

OK — the repo-local guard flags the non-English title, and
`tests/test_card_authoring_rules.py` runs it over every card in CI. The engine
predicate still accepts it by design: goc does not ship an English-only policy
to consumers.
```

The engine line of that transcript is the *unchanged* original finding; only
the second block is new.

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

## Decision (taken 2026-07-27, both questions from DoD box 1)

1. **Scope — English-only.** It is the one rule with an empirical instance;
   the other two audited clean the same day. The no-internal-names rule needs
   a denylist whose contents are a judgement call and whose maintenance is
   open-ended, and AGENTS.md states its examples with "e.g.", so a denylist of
   the two named terms would give false confidence rather than coverage. The
   no-quotes rule cannot be told mechanically from the code and doc quoting
   the rule permits. Neither is worth a speculative guard at zero observed
   instances; AGENTS.md now says plainly that both are unguarded.
2. **Surface — repo-local, in `scripts/` + `tests/` + pre-commit.** No engine
   change, no template, no plugin mirror, no consumer-facing opt-in. The
   option the filing note called "the cheapest honest option" turned out to
   also be the *strongest* one available: because `engine._git_auto_commit`
   runs `git commit` without `--no-verify`, a pre-commit hook fires on `goc
   new --commit`, which puts the guard in the filing path — the thing a
   `tests/`-only guard was assumed to give up.

Both remaining rules stay unenforced, deliberately and on the record. If a
violation of either ever surfaces, that is the instance to file on; this card
is not it.
