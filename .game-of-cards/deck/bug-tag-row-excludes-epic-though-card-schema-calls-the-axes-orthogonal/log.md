## 2026-11-16T02:25:00Z — Filed by refine-deck

Surfaced by the 2026-11-16 hygiene pass. Its tag sweep scored the `bug`
state row over the live deck and found 11 open `meta-fix` umbrellas carrying
`bug` while their two or more wired instances meet the `epic` row. The
regression test reads `not epic` as "does not carry the `epic` tag", under
which all 11 pass; the reference reads the axes as orthogonal, under which
the clause should not exist. The sweep reports and never strips, so no tag
was touched; this card files the contradiction behind the report.

Dedup: `story-tag-predicate-fails-on-two-thirds-of-the-cards-carrying-it`
reconciled the `story` row with the same paragraph and left the `bug` row as
it was; no open card names the `bug` row. Filed at `human_gate: none` with a
recommended fix because the run that filed it had no human in the loop; a
reader may raise the gate if the alternative deserves a decision.

## 2026-11-20T04:40:00Z — Resolved: the recommended fix, not the alternative

Worked from a pull-card run at `human_gate: none`. The filing invited a
reader to raise the gate if the alternative deserved a decision; it did
not, for a reason the filing had not measured. The first packaged table
(`94975556`, 2026-05-04) defined the three tags as structural roles:
`epic` a coordinator, `story` "part of an epic-grouping", `bug` the
standalone finding that was neither. `not epic and not story` was
coherent there. `story-tag-predicate-fails-on-two-thirds-of-the-cards-carrying-it`
redefined `story` as what a card delivers and made `epic` orthogonal to
it, and so retired the role reading the `bug` clause depended on. It
kept the row only because its exclusion "stops being circular" with a
positive `story`, and it never weighed `bug` beside `epic`. Keeping the
clause would leave `epic` orthogonal to `story` but exclusive with
`bug`, with no reason specific to defects. Its one candidate argument,
that an epic's deliverable is its children's, the reference already
rejects for capability epics. It would also make 11 live umbrellas
`bug` mistags. No project-local consultation exists either:
`.game-of-cards/hooks/pull-card.md` is the unedited scaffold stub.

Test design. The scorers in `tests/test_canonical_tag_rows.py` are
copied from the rows by hand, and nothing compared a row against the
reference, so changing `_score_bug` alone would not stop the clause
coming back. Once a live card carries `bug` and `epic`, a re-added
clause would pass the scorer and contradict the reference again
without a red test. `test_delivery_rows_leave_epic_orthogonal` closes
that gap. It fails if either delivery row names `epic`, and it first
shows it rejects the pre-fix row, per
`static-source-guards-never-prove-they-can-catch-an-offender`.
`test_a_bug_family_umbrella_satisfies_both_bug_and_epic` replaces the
offender with one umbrella card scored through both rows. Both tests
were run against the pre-fix row and scorer, and both fail there.

The reference paragraph keeps its "whether the card coordinates
others.** Orthogonal" lead-in, so `reproduce.py`'s `reference calls
epic orthogonal` check still reads True and the script exits 0 for the
right reason, not because it lost its anchor. The card-schema
`SKILL.md` shrank from 12663 to 12648 bytes taxed (cap 12800). No card
was retagged. Zero of 838 cards carry both tags today, so the fix
changes what the schema allows and no existing card.

## 2026-11-20T04:56:00Z — Closure

- **What changed**: `goc/templates/skills/card-schema/SKILL.md:258` — the `bug` row reads `not `story` (default for findings)`; `goc/templates/skills/card-schema/reference.md:314-328` — the `epic` paragraph lets either delivery tag sit beside `epic` and names the bug-family umbrella, plus a note on where the dropped clause came from; `tests/test_canonical_tag_rows.py` — `_score_bug` transcribes the row, `bug carrying epic` moved from `OFFENDERS` to an accepted umbrella case, and a new row-text guard keeps both delivery rows from naming `epic`.
- **Verification**: `reproduce.py` exits 0 (was 1); both new tests fail against the pre-fix row and scorer; `sync_plugin_assets.py --check` and `port_skills_to_openclaw.py --check` OK; census unchanged at 11 `bug` / 4 `epic` / 13 neither.
- **Audit**: no rubric configured; mechanical fix
- **Project impact**: n/a
- **Tests**: 1534 passed / 0 failed / 0 xfailed
- **Bundled with**: n/a

## Closure verification (2026-11-20T04:56:09Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 6/6 ticked
- [x] log-md-closure-entry — '## 2026-11-20T04:56:00Z — Closure' present
