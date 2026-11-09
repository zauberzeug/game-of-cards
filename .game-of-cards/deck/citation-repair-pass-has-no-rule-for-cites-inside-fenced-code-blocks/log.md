## 2026-09-01T05:04:32Z — Closure

- **What changed**: `goc/templates/skills/refine-deck/SKILL.md:112-119` — a
  scope paragraph ahead of the four-step recipe: a cite is scoped by what it
  CLAIMS, not by where it sits, so a comment label (`#`/`//` marker before
  the cite) is repaired inside a fenced block exactly as in prose, while a
  dated record (pasted `grep -n` output, a `reproduce.py` transcript, a
  quoted error) is out of scope and its count reported apart from the step-4
  declines. `reference.md:123` carries the long form plus the census and the
  2026-08-31 pass that motivated it. Placed before the anchor walk rather
  than as a caveat on step 4, so skipping a record costs no
  `git log --follow`.
- **Verification**: `reproduce.py` check 1 went 0/0 mentions and
  `recipe is SILENT (defect fires)` → 3/6 mentions and
  `recipe is explicit (defect fixed)`. All 17 pasted-output cites the census
  finds were re-read by hand: 4 transcript section headers, 1 `reproduce.py`
  "Cited code:" line, 12 lines of `grep -n` output — 0 comment labels, so the
  marker test classifies the live corpus with no exceptions.
  `DocumentedFencedScopeTest` replayed against the pre-fix prose at `HEAD~`
  classifies both surfaces `SILENT`, i.e. the guard fails on the defect.
  `refine-deck` SKILL.md 11,420 → 11,992 B, `BODY_CAPS` raised 11,500 →
  12,300 with the rationale in the established form.
- **Audit**: no rubric configured; mechanical fix
- **Project impact**: n/a
- **Tests**: 1063 passed / 0 failed / 0 xfailed; `uv run goc validate` exit 0

## Closure verification (2026-09-01T05:04:56Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-09-01 — Closure' present

## 2026-11-09T02:36:25Z — Post-closure: damage from before the rule, repaired

The rule this card landed (`eae2bea9`) stopped passes from rewriting fenced
records. It did not repair records the 2026-08-10, 08-17 and 08-24 passes had
already renumbered. A 2026-11-09 sweep checked every record cite in live
cards for a hygiene-pass commit as its writer. It found four pasted
transcripts with rewritten numbers; two of them claimed the same number for
two different lines. All four were restored to their filing-time output
(`7e8549ae`, `f868a963`):
`openclaw-skill-porter-claude-substitutions-emit-doubled-articles`,
`goc-decide-archived-deliberation-entry-uses-card-filing-time`,
`openclaw-porter-arguments-substitution-breaks-single-quoted-python-literals`
and `agent-manifest-guidance-block-is-built-but-silently-ignored`. The same
check over closed cards found none. No remediation remains open.
