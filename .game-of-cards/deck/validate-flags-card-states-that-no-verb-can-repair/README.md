---
title: validate-flags-card-states-that-no-verb-can-repair
summary: "Generalization (spawned by `goc-validate-requires-supersession-and-gate-states-no-verb-can-produce`): `goc validate` enforces several frontmatter invariants for which no CLI verb can *repair* an offending card once it lands in the bad state. Two were just fixed (terminal `superseded_by` target; raised gate on a terminal card), but the shape recurs — other terminal-state invariants (e.g. `closed_at` set-iff-terminal, `superseded`⇒non-empty `superseded_by`) are only ever written by the close verbs, so a card that reaches the bad state via a hand-edit, a `goc migrate` import, or a bot commit that bypassed pre-commit has no repair path but `git`. The repair gap is systemic because the autonomous puller bypasses the pre-commit `goc validate` gate (`pull-card-workflow-skips-pre-commit-so-bot-commits-bypass-goc-validate`), so validator-red states accumulate on `main` silently. `goc repair-edges` is the lone proof that the repair-verb pattern is already valued — it just isn't generalized."
status: done
stage: null
contribution: medium
created: "2026-05-31T08:58:10Z"
closed_at: "2026-05-31T09:35:31Z"
human_gate: none
advances:
  - no-verb-can-fix-a-closed-at-that-contradicts-the-cards-status
advanced_by: []
tags: [meta-fix, api-contract, infra]
definition_of_done: |
  - [x] PROCESS: decision recorded in `## Decision` — scope is **audit-only** (see Decision block + reasoning).
  - [x] MECHANICAL: enumerate the `goc validate` invariants (engine.py `validate_card` + the `validate_*` / `detect_*` functions) and, for each, record whether a non-`git` verb can both *produce* and *repair* the valid state. Delivered as the `## Audit` table in this card's body.
  - [x] TDD: N/A under the recorded audit-only decision — this card adds no repair code, so there is no repair verb to regression-test. Each spawned per-gap card carries its own `reproduce.py` + regression test for the repair it adds (e.g. `no-verb-can-fix-a-closed-at-that-contradicts-the-cards-status`, modeled on `tests/test_decide_repairs_terminal_gate.py`).
  - [x] PROCESS: `uv run goc validate` clean; `uv run python -m unittest discover -s tests` green.
  - [x] PROCESS: file the targeted mechanical-gap follow-up card and reference the already-open cards for the other actionable gaps (see `## Findings → disposition`).
worker: {who: Rodja Trappe, where: main}
---

# `goc validate` flags card states that no verb can repair

## The pattern

`goc validate` is the deck's frontmatter contract enforcer. But enforcing
an invariant is only sound if a CLI verb can both **produce** a passing
value and **repair** a card that has drifted into a violating state. When
the only writer of a required field is a verb that *refuses* the very cards
that need fixing, the invariant becomes a permanent red with no escape but
hand-editing through `git`.

This card generalizes
[`goc-validate-requires-supersession-and-gate-states-no-verb-can-produce`](../goc-validate-requires-supersession-and-gate-states-no-verb-can-produce/),
which fixed two instances of exactly this shape:

- **terminal `superseded_by` target** — the validator demanded a live
  target the verbs refused to write (fixed by relaxing the invariant).
- **raised gate on a terminal card** — the validator demanded
  `human_gate: none`, but `goc decide` (the only gate-lowering verb)
  refused terminal cards (fixed by making `decide` the repair verb).

One was fixed by *relaxing the invariant*, the other by *adding a repair
path* — which is exactly why the general question ("for each invariant,
relax or add a repair verb?") deserves its own audit rather than being
answered ad hoc per bug report.

## Why it recurs

Several `goc validate` invariants are written *only* by the close-time
verbs (`goc done`, `goc done --bundle`, `goc status … <terminal>`):

- `closed_at` must be set iff `status` is terminal.
- `status: superseded` ⇒ non-empty `superseded_by`.
- `human_gate: none` once terminal.

A card can reach a violating combination of these via a route the close
verbs never policed:

1. **Hand-edits** to frontmatter.
2. **`goc migrate`** imports of legacy decks.
3. **Autonomous bot commits** — the puller bypasses the pre-commit
   `goc validate` gate
   ([`pull-card-workflow-skips-pre-commit-so-bot-commits-bypass-goc-validate`](../pull-card-workflow-skips-pre-commit-so-bot-commits-bypass-goc-validate/)),
   so a card it writes in a red state lands on `main` unchecked.

The hygiene pass on the parent card was empirical proof: this repo's own
deck was carrying six validator-red states on `main`, several of which had
**no repair verb** — `superseded_by` had to be hand-edited because
`goc status … superseded --by` no-ops on an already-superseded card
([`goc-status-superseded-discards-by-override-when-target-already-superseded`](../goc-status-superseded-discards-by-override-when-target-already-superseded/)).

## The existing template

`goc repair-edges [--apply]` already embodies the pattern for the
relationship graph: it detects half-edges and writes the missing reverse
side. The generalization is to (a) confirm every other invariant has a
comparable repair path, and (b) decide whether the mechanically-repairable
ones deserve a single `goc repair` umbrella verb rather than one bespoke
repair affordance per invariant.

## Not in scope

Closing the bot-bypass hole itself — that is the separate open card
`pull-card-workflow-skips-pre-commit-so-bot-commits-bypass-goc-validate`.
This card is about ensuring that *when* a red state lands (by any route),
the operator has a verb to fix it.

## Decision

*Resolved 2026-05-31T09:32:46Z:* Audit-only: land the validator-invariant × repair-verb enumeration as a durable reference in this card; file targeted per-gap cards only where a repair verb is genuinely warranted (the mechanical closed_at gap), and point at the already-open cards for the rest

*Reasoning:* The audit shows most validator gaps need human judgment to repair (which successor / which tag / what summary), so a general goc repair would only mechanically auto-fix a minority while adding a large build; the enumeration plus a couple of targeted follow-ups is the higher-ROI, honest scope

## Audit: every gating `goc validate` invariant × repair-verb coverage

Source: `engine.py` `_cmd_validate` (the functions whose results
`errors.append(...)` → `sys.exit(1)`). Verbs available:
`new status done attest decide advance unadvance wait repair-edges move
triage show quality-pass validate migrate` (+ `install`/`upgrade`).
"Repaired by" = a non-`git` path that takes an already-violating card from
red to green.

### Repo/layout-structural

| Invariant (validator) | Produced by | Repaired by | Gap |
|---|---|---|---|
| Dual deck tree present (`validate_deck_directories`) | `install` / `migrate` | manual dir move/merge | yes — structural, one-off |
| Skill-dir parity (`validate_skill_dir_parity`) | `install --local-skills` | `goc upgrade --keep-local-skills` | no |
| Plugin mirror parity (`validate_plugin_mirror_parity`) | sync script | `scripts/sync_plugin_assets.py` | no (a script, not a verb) |
| Hook registration (`validate_hook_registration`) | `install` | `goc upgrade` | no |

### Per-card frontmatter (`validate_card`)

| Invariant | Produced by | Repaired by | Gap |
|---|---|---|---|
| `tags` all known | `new --tag` | — (no retag verb; `quality-pass` only *surfaces*) | yes — judgment (which tag?) |
| terminal ⇒ `closed_at` set | close verbs | — (close verbs refuse already-terminal) | **yes — mechanical** |
| non-terminal ⇒ `closed_at` null | — | — (`status open/active` no-ops, never clears the stray date) | **yes — mechanical** |
| `done` ⇒ no unchecked DoD | `done` enforces | — (`done` refuses re-close) | yes — edge (tick boxes by hand) |
| terminal ⇒ `human_gate: none` | close verbs | `goc decide` | no — **added by parent card** |
| `summary` non-empty string | `new` | — (no summary-setter verb) | yes — judgment (what summary?) |
| `worker` shape valid | `status active --worker-*` | `status active` (only on a reclaim) | partial |
| `waiting_on`/`waiting_until` valid | `wait` | `goc wait --clear` | no |
| rel-field self-ref / unknown title | `advance` / `new` (validated) | `goc unadvance` | no (mostly) |
| non-empty `superseded_by` ⇒ `superseded` | `status superseded --by` | — | partial |
| `superseded` ⇒ non-empty `superseded_by` | `status superseded --by` | **blocked** — `--by` no-ops on an already-`superseded` card | yes → existing card |

### Relationship graph

| Invariant | Produced by | Repaired by | Gap |
|---|---|---|---|
| No advance cycle (`detect_advance_cycles`) | — | `goc unadvance` | no |
| No supersedes cycle (`detect_supersedes_cycles`) | — | — (no `unsupersede` verb) | yes |
| Bidirectional edges (`validate_bidirectional_edges`) | — | `goc repair-edges --apply` | no — **the template** |
| `supersedes` ⇒ target `superseded` (`validate_supersedes_targets`) | `status superseded --by` | — (no `unsupersede`) | yes |
| `superseded_by` is a list (`validate_superseded_by_targets`) | — | — (hand-edit) | yes — rare type-coercion |

(Advisory checks — `validate_blocker_coherence`, `validate_epic_edge_direction`,
`validate_waiting_overlay`, `validate_dod_method_tags` — print warnings but do
**not** gate exit, so they cannot produce a "permanent red"; out of scope here.)

## Findings → disposition

Of ~20 gating checks, ~8 already have a repair verb. The repair affordances
that exist — `repair-edges`, `decide` (new), `wait --clear`, `unadvance`,
`upgrade` — confirm the pattern is valued but applied piecemeal. The gaps
sort into four buckets:

1. **Mechanically auto-fixable, no verb → warrants a new verb.** The
   `closed_at`-vs-`status` drift (both directions). Filed as a targeted
   follow-up: `no-verb-can-fix-a-closed-at-that-contradicts-the-cards-status`.
2. **Blocked by an existing bug.** `superseded` ⇒ non-empty `superseded_by`
   has a *producing* verb (`status … --by`) that silently no-ops on an
   already-`superseded` card — fixing that bug restores the repair path. No
   new card: tracked by
   [`goc-status-superseded-discards-by-override-when-target-already-superseded`](../goc-status-superseded-discards-by-override-when-target-already-superseded/).
3. **Inverse-verb-shaped (an `unsupersede`/unwind verb).** Supersedes cycles,
   wrong-status `supersedes` targets, and redirecting an existing
   supersession all want a release/unwind affordance. The option is already
   contemplated in the `--by`-no-op card's decision options, so it is left
   there rather than duplicated.
4. **Judgment-only by nature — no verb is warranted.** Unknown tag, empty
   summary, unchecked DoD on a `done` card: there is no *mechanical* correct
   value, so hand-editing (informed by `quality-pass`) is the honest repair.
   Documented here so a future reader does not re-file them as "missing verb"
   bugs.

The systemic amplifier — the autonomous puller bypassing the pre-commit
`goc validate` gate, which lets red states land on `main` unchecked — is
out of scope and tracked by
[`pull-card-workflow-skips-pre-commit-so-bot-commits-bypass-goc-validate`](../pull-card-workflow-skips-pre-commit-so-bot-commits-bypass-goc-validate/).

