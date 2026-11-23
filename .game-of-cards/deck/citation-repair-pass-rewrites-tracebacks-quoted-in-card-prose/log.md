## 2026-11-23T02:40:00Z — Filed from the refine-deck hygiene pass

Surfaced by the 2026-11-23 citation anchor check. Its scope classifier
implements the marker test, and it proposed moving the quoted traceback frame
on `repair-edges-crashes-with-traceback-on-bare-string-inverse-edge-field`
in both its first round and its committed re-run. The pass held the frame by
reading the line. The 2026-11-16 pass had restored the same frame the same
way. Recognising the line by hand on every pass is the gap this card closes.

Dedup: no open or gated card names records in prose. The nearest card,
`citation-repair-pass-has-no-rule-for-cites-inside-fenced-code-blocks`
(done 2026-09-01), wrote the scope rule and scoped it to fences. A forward
pointer is in its log. `file-line-citations-drift-again-within-days-of-every-repair-pass`
asks which citation form cards should use. Under any form it picks, a
quoted record still needs a scope test, so it is a separate question.

Gate `none` and contribution `low`: one live instance, and the fix extends a
test that already works to the one place it does not reach. The rejected
keyword alternative is recorded in `## Fix`.

## 2026-11-23T04:37:40Z — Closure

- **What changed**: `goc/templates/skills/refine-deck/SKILL.md` scope
  paragraph — a record quoted in prose is still a record, moved into a fence
  with its numbers as filed so the next pass's marker test holds it without
  a re-read; "Undecidable → record, left in place". `reference.md` § Citation
  anchor check — the long form: why prose escapes the marker test, the
  instance's history, the restore-from-history step behind "as filed", the
  reporting, the rejected keyword test. `goc/templates/skills/create-card/SKILL.md`
  Step 5 — quoted output (`reproduce.py`, tracebacks, error text) goes
  verbatim in a fenced block. The instance card's three result bullets
  fenced as filed (`4954 → 4911`), with a log entry there.
  `tests/test_refine_deck_citation_anchor.py` — `documented_prose_record_rule`
  plus `DocumentedProseRecordRuleTest` (6 tests).
  `tests/test_skill_body_size.py` — refine-deck cap 16,300 → 16,500 (the
  thirteenth raise) and create-card 10,500 → 10,600, each with its reason.
  `reproduce.py` — replay regex takes the fenced form and reports the move.
  Mirrors via `scripts/sync_plugin_assets.py` and the OpenClaw porter.
- **Verification**: `reproduce.py` exit 1 before (1 prose record over 193
  live cards), exit 0 after (0). The new core-skill test failed on the
  shipped paragraph (1 of 6 failing) and passes after the edit; the
  classifier reads the scope prose at `4bd2dbe4` as
  `prose-record-left-to-each-pass` on both surfaces and the edited prose as
  `prose-record-moved-under-the-marker-test` on both. The marker test reads
  the instance's first frame as a fenced record. Taxed sizes: refine-deck
  16,440 of 16,500, create-card 10,588 of 10,600.
  `sync_plugin_assets.py --check` and `port_skills_to_openclaw.py --check`
  both OK.
- **Audit**: no rubric configured; mechanical fix
- **Project impact**: n/a
- **Tests**: 1540 passed / 0 failed / 0 xfailed (`uv run python -m unittest
  discover -s tests`); `uv run goc validate` exit 0
- **Bundled with**: none. Cost record appended to
  `file-line-citations-drift-again-within-days-of-every-repair-pass`.

## Closure verification (2026-11-23T04:38:06Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 8/8 ticked
- [x] log-md-closure-entry — '## 2026-11-23T04:37:40Z — Closure' present
