## 2026-05-29: cross-link to sibling card

Sibling: [goc-done-marks-cards-done-without-clearing-or-checking-human-gate](../goc-done-marks-cards-done-without-clearing-or-checking-human-gate/).
That card documents the gate-clear gap in `goc done` that is the
primary reachability path into the closed-card-with-raised-gate state
this card's guard refuses. The two cards are siblings, not a sequence —
the guard added here makes the bad state unreachable from
`goc decide` regardless of whether the upstream `goc done` gap is
fixed.

## 2026-05-29: shared terminal-status guard helper — declined

Three call-sites now share the `if t.status in TERMINAL_STATUSES: print
ERROR + sys.exit(2)` pattern: `_cmd_done` (engine.py:3244), `_cmd_status`
(engine.py:3983), and `_cmd_decide` (engine.py:4548-4557, this card).
The error messages are deliberately different — `done` points at
supersede/disprove, `status` says "cannot be moved backward", `decide`
points at filing a new card and using `goc status … superseded --by`.
A shared helper would either flatten those three context-specific
messages into one generic line (lossy for the user) or require a verb-
specific message argument (which is just the call-site spelled
differently). Three is still below the threshold where the duplication
costs more than the cohesion of seeing the full guard inline at each
verb. Decline; revisit if a fourth verb joins the family.

## 2026-05-29: fix landed

Added a terminal-status guard at the head of `_cmd_decide` (engine.py:4557-4566)
mirroring the peer-verb pattern. Order matters: the terminal check
fires before the gate-already-none check so the deeper violation
surfaces. Tests: `tests/test_decide_terminal_status_guard.py` covers
`done` / `disproved` / `superseded` cases; `reproduce.py` now exits 0
(VERDICT: guard works). Plugin mirrors regenerated via
`scripts/sync_plugin_assets.py`. Full regression suite green (233/233).

## 2026-05-29 — Closure

- **What changed**: `goc/engine.py:4557-4566` — added a `TERMINAL_STATUSES` guard at the head of `_cmd_decide`, mirroring `_cmd_done` and `_cmd_status`. A `done` / `disproved` / `superseded` card with `human_gate != none` can no longer be silently re-decided.
- **Verification**: 233/233 regression tests pass; new `tests/test_decide_terminal_status_guard.py` (3 cases) green; `reproduce.py` exits 0 with VERDICT "guard works"; `uv run goc validate` clean; `scripts/sync_plugin_assets.py --check` clean after mirror regeneration.
- **Audit**: PASS — no rubric configured; mechanical fix (peer-verb-symmetric guard, no project-principle binding).
- **Project impact**: n/a
- **Tests**: 233 passed / 0 failed / 0 xfailed
- **Bundled with**: n/a

## Closure verification (2026-05-29T15:34:05Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-05-29 — Closure' present

## 2026-05-31 — Partially reversed by `goc-validate-requires-supersession-and-gate-states-no-verb-can-produce`

The blanket terminal-status refusal this card added to the head of `_cmd_decide`
was removed. It created an unrepairable state: the validator *requires*
`human_gate: none` on terminal cards, but `decide` is the only gate-lowering
verb and it refused terminal cards outright — so a card that reached a terminal
status while carrying a raised gate (older closure predating the gate guard, a
hand-edit, or a `goc migrate` import) failed `goc validate` forever with no
escape. `decide` is now the repair path: the "gate already none" guard runs
first (covering every cleanly-closed card, which always carries `gate: none`),
so the only terminal cards `decide` touches are the broken ones — and it
repairs them by recording the resolving decision and lowering the gate while
leaving the card closed. This card's original concern — no silent post-closure
mutation of a *cleanly* closed card — is preserved by that gate-already-none
guard. The fix was dogfooded on this very repo's deck (two terminal cards with
stale gates repaired). See the new card for the full rationale.
