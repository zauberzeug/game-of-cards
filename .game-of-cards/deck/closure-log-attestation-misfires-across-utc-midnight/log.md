
## 2026-08-31 — refine-deck: stale park re-checked, kept

96 days parked. Re-read against HEAD: the claim holds. The
`log-md-closure-entry` derived check still builds its pattern from
`date_prefix = _date_part(today)` at attest time (`goc/engine.py:5653`) and
matches `^## <that date>(?:T…Z)? — Closure` (`goc/engine.py:5657`), so a
closure entry written on one UTC day and attested on the next is still
searched for under the wrong header.

No `reproduce.py` built this round. Reproducing through the real attest path
means controlling the clock across a UTC day boundary, and the two honest
ways to do that — injecting `today` (the parameter exists, so the test would
prove the predicate rather than the shipped path) or freezing time around the
subprocess — differ in what they license the card to claim. Picking between
them is a design question the parked decision should answer first.

## 2026-10-22T05:56:37Z: decision recorded

Lower the gate: verify, then make the closure-entry match tolerate the UTC day boundary — Bulk rule approved by the maintainer in a human session on 2026-10-22: a gated card with no written question and a mechanical fix drops to gate none. Gate decision → none.

## 2026-10-31T05:44:52Z — Verified, and the fix decided

**Verified.** `reproduce.py` exits 1 on `main` before the fix (6b882ce1),
through both the predicate (injected `today` 2026-05-27T00:01:00Z, heading
2026-05-26T23:59:00Z → `False`) and the real `goc attest` on the real clock
(heading stamped 23:59:00Z yesterday → `[ ] log-md-closure-entry`, exit 2).
That settles the 2026-08-31 design question. The shipped path needs no clock
control, because a heading dated yesterday *is* the log a pre-midnight entry
leaves for a post-midnight run. `unverified` dropped.

**Decision: accept any well-formed closure heading, whatever day it names.**

- *Compare against `closed_at`*: rejected, unworkable. `_cmd_attest`
  refuses terminal cards (`_refuse_terminal_mutation`), so every card
  attest runs on has `closed_at: null`.
- *A tolerance window (today or yesterday, or N hours)*: rejected. It still
  compares a hand-typed stamp with attest's clock. Of the 370 datetime
  closure headings here that sit above a passing attest block, 91 are
  stamped later than that run, up to 8.09 h ahead, and 46 cards carry a
  `T00:00:00Z` placeholder. So a window wide enough not to misfire filters
  nothing. A narrow window still fails a legitimate later-day re-run
  (attest blocked on an open `advanced_by` prerequisite, re-run once it
  closes), and append-only log.md then forces a duplicate closure entry.
- *What the date bought*: a weak freshness guard. It only told an entry from
  an *earlier UTC day* apart from a fresh one; a stale entry from an
  abandoned same-day closure attempt already passed. `_cmd_status` cannot
  reopen a closed card, so the only source of a stale entry on an attestable
  card is an abandoned attempt, and none of this deck's open or active cards
  carries one. The check's job, per finish-card Step 4, is presence.

Kept strict: the em-dash separator (the open gated
`attest-closure-marker-check-rejects-ascii-hyphen-headings-as-missing`
decides that), the time format, and the line anchor. With dates no longer
filtering, the anchor is what keeps attest's own block from satisfying the
check, so the regression test pins it.

## 2026-10-31T05:44:52Z — Closure

- **What changed**: `goc/engine.py:6392` — new `_CLOSURE_HEADING_RE`
  (either documented heading form, line-anchored). `goc/engine.py:6426`:
  the `log-md-closure-entry` branch accepts any such heading, names the
  latest in its summary, and on a miss reports
  `no '## YYYY-MM-DDTHH:MM:SSZ — Closure' section`. `today` stays in
  `_run_derived_check`'s signature, read by no check, because four deck
  reproducers pass it, two of them on open decision-gated cards; removing it
  would make them die with an exit 1 that reads as "defect fires".
  `_cmd_attest`'s docstring drops two false claims: that a late attest
  fails this check, and that a bare `## Closure verification` header
  satisfies it (never true). `Skill(finish-card)` Step 4 now says the check
  takes the heading whatever day it names. Mirrors synced, OpenClaw skills
  re-ported.
- **Verification**: `reproduce.py` exit 1 pre-fix → exit 0 post-fix.
  `tests/test_closure_entry_check_ignores_heading_date.py`: 8 tests. On the
  pre-fix engine 6 fail (8 failure reports, counting subtests): 5 on the
  defect, 1 on the reworded miss message. The 2 guard properties, no log.md
  and attest's own blocks, already held and still do. The reproducers of
  `goc-attest-mutates-log-md-on-already-closed-cards` and
  `goc-attest-reports-ok-and-writes-empty-stub-when-no-checks-are-configured`
  still exit 0.
- **Audit**: no rubric configured; mechanical fix
- **Project impact**: closers no longer write a duplicate closure entry
  because attest ran after UTC midnight, or on a later day than the entry.
- **Tests**: 1462 passed / 0 failed / 0 xfailed
  (`uv run python -m unittest discover -s tests`). `uv run goc validate`
  exits 0, `sync_plugin_assets.py --check` and
  `port_skills_to_openclaw.py --check` are green, and the card-language and
  strict-YAML guards are clean.

## Closure verification (2026-10-31T05:45:27Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-10-31T05:44:52Z — Closure' present
