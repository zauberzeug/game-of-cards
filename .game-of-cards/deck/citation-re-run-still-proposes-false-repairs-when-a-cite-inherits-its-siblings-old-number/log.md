## 2026-11-16T02:20:00Z — Filed by refine-deck

Found by the 2026-11-16 hygiene pass, whose closing re-run over its committed
171 citation repairs (`4ca21b40`) proposed two more. Both were read against
the prose, both were false, and neither was applied; the skill classes a
non-empty second round as a recipe defect to file, so this card files it.

Dedup: the shape is neither the uncommitted re-run that
`citation-idempotence-re-run-reports-false-repairs-until-the-pass-commits`
closed (this re-run ran after the commit) nor the two-current-occurrence
collision `citation-repair-pass-gives-two-cites-in-one-card-the-same-anchor-when-their-numbers-collide`
guards (each token occurs once). No open card names a hand-off. Filed at
`human_gate: none` with a recommended fix: the run that filed it had no
human in the loop, and a reader may raise the gate. No `advances` edge: the
earlier citation-recipe cards are cross-linked, not wired.

## 2026-11-20T04:43:37Z — Closure

- **What changed**: `goc/templates/skills/refine-deck/SKILL.md` step 2 —
  where the token is on both sides of a commit, compare the cite's SLOT (its
  line with cite numbers masked, plus its place among that line's cites); a
  commit whose new holder's slot held another number before, or whose old
  holder's slot holds another number after, handed the number over and wrote
  it. `reference.md` § Citation anchor check — "Getting the anchor" points
  forward; a new "A commit can hand the token from one cite to another"
  section carries the shape, the slot, the reworded-line case (kept, not
  declined) and the measurements; the commit-first paragraph now calls the
  commit necessary, not sufficient; the `retired occurrence` row names the
  hand-off. `tests/test_refine_deck_citation_anchor.py` —
  `documented_handoff_rule`, `cite_slots`, `handed_off`, the hand-off and
  reworded-line fixtures, 14 tests in `DocumentedHandoffRuleTest` (7),
  `SameCommitHandoffTest` (5) and `RewordedLineScopeTest` (2).
  `tests/test_skill_body_size.py` — refine-deck cap 16,000 → 16,300, the
  twelfth raise, with its reason. `reproduce.py` — `replay()` follows the
  walk step 2 words, over a two-line and a one-line fixture. Mirrors via
  `scripts/sync_plugin_assets.py` and the OpenClaw porter.
- **Verification**: against the shipped recipe the new fixture's committed
  re-run reads `{'src/app.py:11': 16}` and 5 tests fail (core-skill rule,
  reference no longer sufficient-claiming, residue row, two-line and one-line
  fixed point); with the fix the re-run is `{}`. `reproduce.py` exits 1 on
  the shipped step 2 and 0 on the amended one. Replay over this deck's open
  and active cards (568 single-occurrence cites): the two live instances are
  the only hand-offs that move an anchor; one reworded line, a prose edit.
  Live instances read against their prose: both still carry the numbers
  `4ca21b40` wrote (`engine.py:7139` on `def _remove_from_list_field`,
  `goc/engine.py:6010` on `if check.returncode == 1:` in that tree); no
  pass moved them since (`2a665b45` rewrote other cites on both cards), so
  nothing to restore. Both have drifted +269 with the engine, and the slot
  walk relocates them correctly (7408, 6277) where the bare token walk would
  move them onto their siblings (7426 `_mutate_pair`, 6295
  `claim_push_enabled`). SKILL.md taxed size 16,274 of 16,300.
  `sync_plugin_assets.py --check` and `port_skills_to_openclaw.py --check`
  both OK.
- **Audit**: no rubric configured; mechanical fix
- **Project impact**: n/a
- **Tests**: 1532 passed / 0 failed / 0 xfailed (`uv run python -m unittest
  discover -s tests`); `uv run goc validate` exit 0
- **Bundled with**: none. Cost record appended to
  `file-line-citations-drift-again-within-days-of-every-repair-pass`.

## Closure verification (2026-11-20T04:43:44Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 6/6 ticked
- [x] log-md-closure-entry — '## 2026-11-20T04:43:37Z — Closure' present
