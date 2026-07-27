## 2026-07-27 — Filed from the Stop-hook pattern check

The refine-deck pass that renamed
`openclaw-plugin-skills-erzwingen-mehrfach-reads-pro-session` treated it as a
one-off mechanical fix. The Stop-hook pattern check asked whether the change
touched something broader, and it did: the rename was possible only because a
human-or-agent read the title, and nothing in the toolchain could have found
it.

Dedup before filing. `goc --status all` grepped for `title` / `jargon` /
`antipattern` / `quality-pass` returned 19 cards; all are about the *mechanics*
of the guard (it crashes, it is bypassed by `move`, it shows a raw regex error,
it mutates terminal cards) and none about what the guard does not cover.
Grepping deck bodies for "English only" / "non-English" returned exactly one
hit — the rename log entry written minutes earlier in this same pass. No root
card exists, so this is a filing and not a connection.

Two adjacent cards are cross-referenced in the body rather than edged, and the
body says explicitly why each is adjacent rather than parent:
`doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them`
(different root: tree-derived claims, not authoring conventions) and
`static-source-guards-never-prove-they-can-catch-an-offender` (not a parent,
but its requirement is inherited into DoD box 3).

Scope kept deliberately narrow. The live instance count is one, on one of the
three unguarded rules; the other two were audited during this pass and are
clean. That is well under the four-instance threshold `Skill(audit-deck)` uses
for filing an architectural meta-fix, so this is filed as an ordinary
`contribution: low` gap card and not as a family umbrella. The body states the
instance count plainly so a later reader can judge whether it is worth the
false-positive budget a language heuristic would spend.

Gate left at `none` per the unattended-pass instruction; the scope and surface
picks are carried by the first DoD box.

## 2026-07-27 — Decision and implementation

**Scope: English-only.** The two confidentiality rules stay unguarded, and
AGENTS.md now says so in the section that states them. Reasons, in order of
weight: neither has an observed instance (both audited clean the same day the
English-only instance surfaced); AGENTS.md states its internal-name examples
with "e.g.", so a denylist of the two named terms would buy false confidence
rather than coverage, and the filing note's concern that such a list "must live
somewhere that is not itself public" is a real unresolved constraint; and the
no-quotes rule cannot be separated mechanically from the code and doc quoting
the rule explicitly permits. Filing a card per speculative rule is the
redundant-umbrella move `Skill(audit-deck)` warns about — the honest artefact
is a documented gap, which is what landed.

**Surface: repo-local — `scripts/check_card_language.py`, enforced from
`tests/test_card_authoring_rules.py` and a `card-language` pre-commit hook.**
No engine change, no template, no plugin mirror, no consumer-facing opt-in.
Deliberately NOT `TITLE_ANTIPATTERNS`: that list ships to every consumer, and
a team running goc on a German codebase is entitled to a German deck. An
opt-in config key was rejected as a consumer-facing surface disproportionate
to a one-instance project-local rule.

The surface pick turned out better than the filing note assumed. It framed the
`tests/` option as the cheap-but-weaker one — CI-only, downstream of filing.
But `engine._git_auto_commit` runs `git commit` without `--no-verify`, so a
pre-commit hook fires on `goc new --commit` as well. Wiring the same script
into `.pre-commit-config.yaml` puts the guard in the filing path at zero extra
cost, which is the property the engine-side option was supposed to be needed
for. Both enforcement points call one script, so they cannot drift.

**Detector, and why it is shaped this way.** Two layers. 236 marker words
across German, French, Spanish/Portuguese, Italian and Dutch, each one a claim
that the word is never legitimate English in a card — homographs (`die`, `war`,
`hat`, `tag`, `fast`, `todo`, `con`, `sin`, `per`, `non`, `come`, `pour`,
`sans`, `com`) are deliberately excluded and listed in the module docstring so
the next reader does not "helpfully" add them back. Plus nine German
derivational endings (`-ung`, `-ungen`, `-ierung`, `-keit`, `-heit`,
`-schaft`, `-lich`, `-isch`, `-ieren`) with a six-character floor and an
explicit English exception set (`unsung`, `unstrung`, …).

The suffix layer is not redundant with the word layer, and the historical
offender is why: slug titles drop articles, so it contained no function words
at all — only content words. A function-word list alone, which is what the
filing note sketched ("stop-word lists"), would have missed the very title
that motivated the card. `test_each_detection_layer_fires_on_its_own` pins
both layers separately so one going dead is visible.

**Measurements.** Zero findings across all 681 live cards. The nine
`MARKER_SUFFIXES`/`MIN_SUFFIX_TOKEN_LEN` combinations were checked against
every one of the 4,363 distinct tokens in the deck's scanned fields before
being adopted: zero matches. `flag_text` catches the historical offender on
two independent markers, plus one recall case per language and two
single-layer cases. Full suite: 829 tests, green. `uv run goc validate` and
`scripts/sync_plugin_assets.py --check` both clean.

**Stated limits, on the record rather than in a comment.** Recall is the price
of precision: a non-English title built entirely from cognates
(`konfiguration-migration-problem`) still passes. Card bodies are out of scope
even though AGENTS.md names them — bodies legitimately quote non-English
identifiers and upstream error strings, and several cards (including this one)
quote the offending title itself, so scanning bodies would report the deck's
own record of the bug as a violation. Both limits are in the module docstring
and the README, not just here.

**Inherited requirement discharged.** Per
`static-source-guards-never-prove-they-can-catch-an-offender`, the guard
demonstrates it can catch an offender rather than only reporting a clean tree:
`test_scan_deck_reports_a_planted_offender` runs the whole deck scan against a
planted card, and `test_live_deck_is_actually_being_scanned` fails if the deck
glob ever goes empty — without it, moving the deck would turn the clean-tree
assertion into a vacuous pass. The same planted-offender check was also run
end-to-end against the real deck path (`--check` exited 1 with four findings,
then the tree was restored).

## 2026-07-27T05:03:08Z — Closure

- **What changed**: `scripts/check_card_language.py` (new) — a precision-first
  two-layer non-English detector over each card's `title`, `summary` and
  `definition_of_done`; wired into `.pre-commit-config.yaml` as the
  `card-language` hook and into `tests/test_card_authoring_rules.py` (new) for
  CI. `AGENTS.md` § "Card authoring rules" now names the guard on the
  English-only bullet and records that the two confidentiality rules remain
  unguarded. `reproduce.py` rewritten to probe both predicates with a control
  each.
- **Verification**: 0 findings across 681 live cards; historical offender caught
  on 2 independent markers; 9 marker suffixes checked against all 4,363 distinct
  tokens in the scanned fields with 0 collisions; `--check` exits 1 with 4
  findings on a planted offender in the real deck path, 0 once removed;
  `reproduce.py` exits 0.
- **Audit**: no rubric configured (`.game-of-cards/hooks/finish-card.md` is the
  unedited placeholder). Not a purely mechanical fix, so naming the principle it
  does bind: AGENTS.md's ownership model — project-local convention stays
  repo-local and ships to no consumer, which is why `TITLE_ANTIPATTERNS` was
  left untouched.
- **Project impact**: the English-only authoring rule moves from unenforceable to
  enforced at commit time; the other two rules' unguarded status is now documented
  rather than merely true.
- **Tests**: 829 passed / 0 failed / 0 xfailed.

## Closure verification (2026-07-27T05:03:11Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-07-27 — Closure' present
