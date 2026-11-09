## 2026-11-09T02:35:38Z — Filed from the refine-deck pass's pattern check

The pass's Stop-hook pattern check asked whether its changes touched a
broader pattern. Answering it meant sweeping the deck's live cards for
identifiers that do not exist. The sweep found 10 names that never existed in
code history; 8 are proposed helpers, which is legitimate. One card named a
downstream consumer by the internal project name AGENTS.md forbids. A full
search then found 16 such lines across 6 cards, three of them older than the
2026-07-27 "audited clean" sentence.

Dedup: the only card on the rule is the closed
`card-authoring-rules-in-agents-md-have-no-enforcement-path`, whose scope decision rested on there being no instance. Per
"closure is not frozenness", this is post-close evidence: a new card, plus a
forward pointer on the closed one.

Filed at `human_gate: none`. Redacting the lines and correcting the AGENTS.md
sentence are mechanical. The guard recommendation revisits that card's
decision with evidence it did not have; a reader who disagrees can raise the
gate. This card names neither the project nor the individual; § Instances
gives card titles and line numbers.

## 2026-11-09T05:27:09Z — Sweep verdicts

**Tier 1, the example project: 16 of 16 lines rephrased.** They became "a
downstream consumer repository", "a downstream card", "that drain" or, in one
gateway card, nothing: the parenthetical only labelled a single-agent install,
so it was dropped. Every downstream card slug, date and count stayed. The
deck-wide case-insensitive grep now matches one line: the `worker:` `where:`
host in `draft-clearing-verbs-release-summary-less-cards-into-a-validate-red-deck`.
That is a machine name, which AGENTS.md's worker docs permit.

**Tier 2, individual attributions.** The filing list was a lower bound
("at least these"), so the sweep ran deck-wide. It searched for the
maintainer's name outside frontmatter `worker:` values and found 130 lines,
plus one false hit where the surname is a substring of an ordinary word. A capitalized-name
search on attribution verbs (decided, chose, confirmed, asked, reported,
`*Reasoning:* <Name>:` …) found no other individual. Verdicts by class:

| class | lines | cards | verdict |
|---|---|---|---|
| attribution of a decision, report, review, sign-off or credential (`<name> decided`, `Reported by <name>`, `*Reasoning:* <name>:`, `(<date>, <name>)` decision headings, `<name>'s credentials`) | 62 | 26 | rephrased to "the maintainer", or "Maintainer review" / "maintainer visual sign-off" where the original was a label; all six lines in the filing list are among them |
| worker-slug examples in prose and reproducer fixtures (the slug AGENTS.md's own worker docs use) | 30 | 11 | kept: slug examples are permitted |
| home-directory paths in quoted tool output and commands | 29 | 7 | kept: a login inside a verbatim path is an identifier, and rewriting the output would degrade the evidence |
| rendered worker labels in the board-truncation cards, and a git `user.name` example | 5 | 3 | kept: worker values as the board renders them |
| registry account handles in `publish-npm-package-under-zauberzeug-org-not-personal` | 4 | 1 | kept: moving off that personal handle is the card's subject |

Three of the 62 lines also quoted a discussion verbatim, which the quoting
rule forbids. They are paraphrased:

- the option-α reasoning in `provide-openclaw-plugin-for-skills-and-hooks`
  log;
- the triage call in `provide-codex-plugin-for-skills-and-hooks` log;
- the gate-order remark in
  `human-gate-is-card-level-but-human-only-ness-is-a-dod-item-property` log.

All three predate 2026-07-27, so that day's "audited clean" verdict was wrong
for the quoting rule too. A follow-up search for first-person speech inside
quotation marks found only illustrative user prompts and trigger phrases, not
discussion quotes. That is a heuristic, not an audit, and AGENTS.md says so.

Edits touched 78 lines in 30 cards. None of those cards was active. Two are
gated (`autonomous-picker-…`, `human-gate-…`); only their prose changed,
never a `## Decision required` option. Per-card log entries were not added:
this entry, the commit, and the forward pointer on the 2026-07-27 card are the
record.

**Guard decision.** The guard landed, scoped as § Fix step 4 proposed. The
2026-07-27 card's own decision named this as the trigger: "If a violation of
either ever surfaces, that is the instance to file on." The guard holds only
AGENTS.md's two published examples, because a list of anything else would
publish what the rule protects. It reads every file under the deck and exempts
a README's frontmatter `worker:` value alone. Sensitivity: `git archive HEAD`
of the deck as filed, run through `scan_deck_for_internal_names`, gives 16
findings in 6 cards. They are exactly the § Instances table; the `worker:`
host line is correctly exempt. The first implementation folded diacritics
with a per-character `unicodedata.combining` loop and cost 1.2 s per commit. A
C-level regex over the combining-mark blocks, plus a substring pre-check,
brought it to 0.25 s, against 0.54 s for the existing language check.

## 2026-11-09T05:27:09Z — Closure

- **What changed**: `scripts/check_card_language.py` — `PUBLISHED_INTERNAL_NAMES`, `flag_internal_names`, `scan_deck_for_internal_names`; `main` runs and reports both checks. `tests/test_card_authoring_rules.py` — `PublishedInternalNamesGuardTest`, 10 tests: a planted body fails `--check`, every surface scanned, the `worker:` value the only exemption, spelling variants, near misses, line numbers, parity with AGENTS.md's examples, live deck clean. AGENTS.md § Card authoring rules — the audit sentence replaced by the guard's scope, the unguarded remainder, and this sweep's date and result; the Common commands comment updated. `.pre-commit-config.yaml` — the `card-language` hook's name and comment cover both checks. 78 card lines in 30 cards rephrased (verdicts above). The closed 2026-07-27 card gets a README forward pointer.
- **Verification**: the guard on the deck as filed gives 16/16 findings with no false positive. Live deck: `English-only: clean (828 cards scanned)` and `Published internal names: clean (828 cards scanned, every file)`. Before AGENTS.md was updated, the parity test failed on the missing guard reference; after the update it passes.
- **Audit**: no rubric configured; mechanical fix
- **Project impact**: n/a
- **Tests**: 1499 passed / 0 failed / 0 xfailed (`uv run python -m unittest discover -s tests`); `uv run goc validate`, `scripts/check_card_language.py --check`, `scripts/check_card_frontmatter_yaml.py --check` and `scripts/sync_plugin_assets.py --check` all exit 0

## Closure verification (2026-11-09T05:27:51Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 6/6 ticked
- [x] log-md-closure-entry — '## 2026-11-09T05:27:09Z — Closure' present

## 2026-11-09T05:30:36Z — Post-close amendment

Linked as the thirty-eighth instance of
[doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them](../doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them/)
(`advances` edge plus a row in its table). The "audited clean on 2026-07-27"
sentence was an unpinned prose restatement of deck content, false when
written. `PublishedInternalNamesGuardTest` now derives the derivable part.
