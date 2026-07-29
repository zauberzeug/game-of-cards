## 2026-07-26: filed from a live instance in this repo

Filed after a decision was recorded on
[`autonomous-picker-wastes-passes-on-cards-only-a-human-can-finish`](../autonomous-picker-wastes-passes-on-cards-only-a-human-can-finish/)
without reading its `advanced_by` prerequisite, which corrected the very
premise being decided. The decision was rewound the same day.

Filed as an engine gap rather than as a process note because `goc decide`
already parsed the frontmatter carrying the edge and chose to print
nothing about it, while the queue and board renderers print a dependency
advisory for the same condition. The asymmetry is the defect: the surface
that *removes* the human gate is quieter about prerequisites than the
surfaces that merely list the card.

Deduped before filing. Three neighbours were checked and none covers this:

- `advanced-by-treated-as-hard-prerequisite-but-documented-as-mostly-loose`
  (closed 2026-05-26) settled edge *semantics* — ~80% value contribution,
  ~20% strict, distinction "carried by the body, not the field." That
  decision is what makes this advisory necessary rather than redundant:
  since the field cannot express strictness, the only way to tell is to
  read the prerequisite, and nothing prompts that at decide time. No
  change to closure or readiness semantics is proposed here.
- `goc-validate-requires-supersession-and-gate-states-no-verb-can-produce`
  (done) covers gate *lowering* on terminal cards — a different invariant.
- The missing gate-*raise* verb, which this instance also hit (the rewind
  required hand-editing frontmatter), is already a DoD item on
  `human-gate-is-card-level-but-human-only-ness-is-a-dod-item-property`.
  Connected there rather than re-filed.

Scaffolded at `--gate none` deliberately. The one design question —
advisory or blocking — is answered by two existing constraints rather
than by taste: refusing would break the ~80% loose-edge majority the root
card settled, and the deck's house style for anything short of a schema
violation is warning-only (`UNTAGGED_DOD_ITEM` and every other
`BlockerWarning` class). The DoD pins the advisory as non-blocking with
an unchanged exit code so a later pass cannot quietly harden it.

`reproduce.py` exits 1 on `main`; output pasted verbatim into the README.

## 2026-07-29T05:32:38Z — Closure

- **What changed**: `goc/engine.py:6154` — new `_unclosed_prerequisite_notice(card, by_title)`
  builds the advisory by calling `dependency_advisory` (the renderers' own helper) in its
  default terminal-gated form; `_cmd_decide` resolves it from the pre-mutation card and
  prints it to stderr immediately before the `decision recorded; gate <prior> → none` line.
  `goc/templates/skills/decide-card/SKILL.md:58` — step 1 now instructs the reader to read
  unclosed `advanced_by` prerequisites *before* recording, since the CLI advisory necessarily
  arrives as the decision lands. Five mirrors regenerated (`.claude/`, `.codex/`,
  `claude-plugin/`, `codex-plugin/`, `openclaw-plugin/`).
- **Verification**: `reproduce.py` exit 0 (was exit 1 on `main`, `output names the
  prerequisite: False`). Against the live deck the advisory fires on 3 of the parked cards,
  including the exact 2026-07-26 incident this card was filed from —
  `autonomous-picker-wastes-passes-on-cards-only-a-human-can-finish` → 1 unclosed
  prerequisite `human-gate-is-card-level-but-human-only-ness-is-a-dod-item-property (open)`.
  `uv run goc validate` exit 0 across 684 cards; `sync_plugin_assets.py --check` and
  `port_skills_to_openclaw.py --check` both green.
- **Audit**: no rubric configured; mechanical fix. (`.game-of-cards/hooks/finish-card.md` is
  a comment-only stub.) Two repo constraints did bind the design and are pinned by tests
  rather than left to a later pass: the advisory is non-blocking, because refusing would
  break the ~80% loose-edge majority settled by
  `advanced-by-treated-as-hard-prerequisite-but-documented-as-mostly-loose`; and the liveness
  rule is derived from `dependency_advisory` rather than re-inlined, per the drift shape
  `renderers-reimplement-the-dependency-advisory-liveness-gate-and-drift`.
- **Slice choice**: default (terminal-gated), NOT the renderers' `queue_only=True` slice.
  `queue_only` mutes `active` cards because "you may start" has no audience once a card is
  claimed — but an `active` card at a raised gate is exactly a card whose decision someone
  is about to act on, so muting there would reintroduce the bug for the claimed case. A
  dedicated test pins that an `active` card still gets the notice.
- **Tests**: 845 passed / 0 failed. `tests/test_decide_unclosed_prerequisites.py` adds 12 —
  8 unit (naming + status label, no prereqs, each terminal prereq status, mixed set, dangling
  ref rendered `(card not found)`, each terminal card status, active card still notified,
  and an equivalence assertion that the notice fires iff `dependency_advisory` reports
  blockers) and 4 end-to-end CLI (advisory precedes the gate-flip line; non-blocking —
  exit 0, `human_gate: none` on disk, `## Decision` block and log entry written; silent when
  every prerequisite is terminal; silent when the card has no prerequisites).
- **Adjacent finding, not re-filed**: `_run_derived_check`'s `advanced-by-closed` branch
  (`goc/engine.py:5098`-ish) hand-rolls a third variant of the same predicate whose
  `t in by_title and ...` drops dangling references this fix renders as `(card not found)`.
  Already owned by `attest-treats-dangling-advanced-by-refs-as-closed` (open, `decision`
  gate) plus the two liveness-drift cards; folding it in would change what `goc done`
  refuses, so it stays out of this closure. Recorded in the README's scope boundary.
- **Project impact**: n/a

## Closure verification (2026-07-29T05:33:03Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-07-29 — Closure' present

## 2026-07-29T05:38:00Z — post-close generalization connect

The Stop-hook pattern check flagged the fix as having broader applicability, and
it does: the dependency advisory is opt-in per call site, and this closure fixed
one site. Verified the remaining ones on a two-card temp deck — `goc status
<title> active` prints only `child: open → active`, and `goc show <title>`
prints the raw `advanced_by` list with no prereq status.

Deduped rather than filed. The deck already carries a three-member family with
this exact shape and naming (`draft-gating-is-opt-in-per-surface-…`,
`query-flag-validation-is-opt-in-per-flag-…`,
`doc-accuracy-guards-are-opt-in-per-claim-…`), all open at `human_gate:
decision`, already cross-referencing each other. A fourth umbrella would be the
redundant-umbrella anti-pattern — three undecided umbrellas is the signal that
the missing act is a decision, not another card.

Instead the instance is CONNECTED: `draft-gating-is-opt-in-per-surface-and-new-verbs-keep-missing-it`
gains a "Sibling property: the dependency advisory has the same shape" section
carrying the evidence above, and this card's scope boundary gains the reciprocal
pointer. That card's three mechanism options (invert the default / validate-time
lint / per-site fixes) are verbatim the options this property needs, so whoever
decides it decides both. No `advances` edge: the connection is a shared decision,
not value flow into a closed card.
