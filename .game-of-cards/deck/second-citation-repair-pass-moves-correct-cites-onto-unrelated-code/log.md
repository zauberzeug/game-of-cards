## 2026-08-17T04:37:34Z — Closure

- **What changed**: `goc/templates/skills/refine-deck/SKILL.md:115` +
  `reference.md:129-151` — the citation-repair anchor moved from the card's
  creating commit to the commit that last WROTE the cited number, found by
  walking the README's own history for the commit where the cite token turns
  from absent to present. The retired rule's independence claim is replaced by
  the measurement that refutes it. Mirrors regenerated across all five payloads.
- **Verification**: `reproduce.py` exits 0 — the rule the skill names now
  agrees with the reference anchor on 859 of 859 open-card cites, 485 of which
  carry numbers a repair pass rewrote (the only cites on which the two rules
  can differ). The retired anchor, replayed as a counterfactual on the same
  cites, would still move 165 correct ones. `tests/test_refine_deck_citation_anchor.py`
  builds the two-pass shape from scratch and is red against the pre-fix prose
  (2 of 4 cases fail: the parsed rule repairs the fixture to line 21, the decoy,
  instead of line 16).
- **Audit**: PASS — no rubric configured; the project-local finish-card hook is
  an empty stub. The change binds one documented principle: the skill body is
  the contract an agent follows literally, so the executable rule lives in
  `SKILL.md` and the rationale in the reference sibling
  (`tests/test_skill_body_size.py`, cap raised 11,200 → 11,500 with that
  reasoning recorded).
- **Project impact**: n/a
- **Tests**: 990 passed / 0 failed / 0 xfailed (`uv run python -m unittest
  discover -s tests`); `uv run goc validate` clean; `scripts/sync_plugin_assets.py
  --check` and `scripts/port_skills_to_openclaw.py --check` both clean.
- **Bundled with**: n/a

The guard deliberately reads the rule out of the shipped prose rather than
re-implementing it. A test that only asserted the walk works would stay green
through a rewrite of the skill body, which is exactly where this defect lived:
the implementation was never wrong, the instruction was.

## Closure verification (2026-08-17T04:39:54Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 6/6 ticked
- [x] log-md-closure-entry — '## 2026-08-17 — Closure' present
