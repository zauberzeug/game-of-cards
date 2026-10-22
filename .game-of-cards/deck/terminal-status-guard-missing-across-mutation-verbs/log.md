## 2026-06-21: claimed and gate raised to `decision`

An autonomous `pull-card` session pulled this epic (`human_gate: none`,
the only ready card) and discovered its completion depends on resolving
four children that each carry `human_gate: decision`
(`goc-wait-...`, `goc-attest-...`, `goc-quality-pass-...`,
`goc-move-...`). The guard *shape* per verb — notably the `goc move`
`--force` escape hatch and the `quality-pass` filter-vs-error choice —
is a genuine API-contract taste call, and this repo defines no
project-local `pull-card` consultation hook. Per the pull-card Andon
protocol (no hook → surface the decision), the session did the work it
*could* do autonomously: consolidated the four scattered per-verb
option menus into one coherent recommended bundle (the
`## Decision required` section), then raised this epic's gate so the
human approves the family in a single `Skill(decide-card)` action
rather than four.

The recommended bundle: a shared `_refuse_terminal_mutation` helper
(five call-sites now justify it); strict refuse for `wait` and
`attest`; filter+helper-guard for `quality-pass`; reject-with-`--force`
for `move`; and `_cmd_advance`/`_cmd_unadvance` classified **out of
scope** (supersession edges legitimately mutate closed-card
relationships — that pre-answers DoD item 5). No code changed this
session; implementation waits on the decision.

## 2026-07-09T05:30:00Z — Sibling-shape precedent

[`path-shaped-title-arguments-let-verbs-read-and-mutate-files-outside-the-deck`](../path-shaped-title-arguments-let-verbs-read-and-mutate-files-outside-the-deck/)
closed by introducing `resolve_card_dir()` — a single shared helper that every
title-taking verb routes through — rather than per-verb inline checks. That is
a working precedent for this epic's "reusable helper that each verb calls"
option in the PROCESS DoD item, and the helper itself (called at the top of
each verb's title resolution) is a candidate hang-point for a shared
terminal-status guard.

## 2026-06-21T10:57:17Z: decision deliberation archived

Archived from the README's `## Decision required` section by `goc decide` before it was replaced with the resolved `## Decision` block — README is the dashboard, log.md is the journal. This preserves the options and recommendation that produced the decision below.

The four open children each carry their own `human_gate: decision`
with a menu of options. This epic exists so the family is resolved
under **one** shared decision instead of four that can drift. An
autonomous `pull-card` session consolidated the children's
recommendations into the single bundle below; the per-verb option
catalogues remain in each child's body. Approving this bundle (via
`Skill(decide-card)` on this epic) lowers the gate and authorises a
follow-up session to implement all four verbs + the shared helper in
one commit-series, then close the children under the chosen shape.

The recommendation everywhere is the **sibling-consistent strict
guard** — every other state-touching verb (`done`, `status`, `decide`)
already refuses terminal targets; the deck convention "closed cards
are read-only for state-touching verbs" is the established axis. The
genuine taste calls are the `goc move` escape hatch and the
`validate_waiting_overlay` follow-through; both are called out below.

### Recommended bundle

1. **Shared shape — one helper, not four inline checks.** Add
   `_refuse_terminal_mutation(card, verb, *, replacement="supersede")`
   to `engine.py` that prints an error mirroring the post-fix
   `_cmd_decide` message (names the card, its terminal status, and the
   `goc status <old> superseded --by <new>` forward path) and
   `sys.exit(2)`. Each guarded verb calls it immediately after
   `load_card_or_exit`. With five call-sites (decide already inline +
   four new) the helper is past the "two sites is too small" threshold
   the closed predecessor's DoD flagged. (`_cmd_decide` may stay inline
   or be refactored onto the helper — implementer's choice, since its
   message is the template.)

2. **`goc wait`** → strict refuse (child option 1). On a terminal
   target, exit non-zero, write nothing. Leave
   `validate_waiting_overlay`'s terminal-skip as-is — it becomes
   *defensible* once the setter refuses, because a terminal overlay can
   then only be inherited from a pre-closure live state (history),
   never freshly created. No `TERMINAL_OVERLAY` warning needed.

3. **`goc attest`** → strict refuse (child option 1). Guard at the top
   of `_cmd_attest`; the misleading `Next: goc done …` print is then
   unreachable on the terminal path.

4. **`goc quality-pass`** → filter **+** helper-guard (child
   recommendation "(a)+(c)"). Filter terminal cards out of the Layer-2
   LLM *sample* regardless of `--status` (Layer-1 antipattern scan still
   reports over them, read-only), AND guard `_apply_summary_rewrite` /
   `_apply_dod_rewrite` so any future caller inherits the protection.

5. **`goc move`** → reject-by-default **with a `--force` escape hatch**
   (child option c). The record axis defaults to immutability; a
   deliberate closed-card retitle (slug-normalization sweep) is rare
   enough that an explicit per-call `--force` is the right ergonomic,
   matching the `goc done --force` precedent. The quality-pass `move`
   subprocess hop inherits the rejection via the non-zero exit code (no
   `--force` passed), which is the intended behaviour.

6. **`_cmd_advance` / `_cmd_unadvance`** → **out of scope (no guard).**
   These maintain `advances`/`advanced_by` edges, and the supersession
   sibling (`goc status … superseded --by`) legitimately mutates a
   closed card's relationship edges as part of the record axis. Edge
   maintenance on a terminal endpoint is a feature, not the defect this
   family targets. Record this classification in `log.md` to close DoD
   item 5.

### If you disagree

The reversible alternative on the one real taste call: drop the
`--force` hatch on `goc move` (child option a, plain reject) if a
closed-card retitle should never be possible without re-opening the
question per-card. Everything else in the bundle is the conservative,
convention-aligned default; diverging from it would re-open the
"closed cards are read-only" axis the deck already settled.


## 2026-10-22T05:17:11Z: decision recorded

Approve the recommended bundle: strict refuse via one shared terminal-status helper across wait, attest, move, quality-pass and the summary/DoD rewrites; goc move gets a --force escape hatch; advance/unadvance stay out of scope; the helper's message is written fresh — The maintainer approved the bundle in a human session on 2026-10-22; it is the sibling-consistent 'closed cards are read-only' default, and _cmd_decide no longer refuses terminal cards (it now runs a terminal gate-repair path), so there is no refusal message left to mirror. Gate decision → none. Status active → open — the claim parked behind the gate is released, so the next pull-card claims the card per this decision.
