# Log

## 2026-08-04: filed from a pull-card session that hit the defect

Surfaced while running `Skill(pull-card)` on a fully-gated deck. The
skill's injected `--ready -v` block rendered as the `ACTIVE:` banner
followed by nothing, and establishing that the queue was genuinely
empty — rather than the query being wrong or the bootstrap having
failed — took three further commands (`goc --status open`, a per-card
`human_gate`/`waiting_on` cross-tab, and reading the three
`gate: none` cards). That is the cost the missing line imposes on
every drained-queue run.

## 2026-08-04: fixed — the table path states its empty result

`render_empty_query_line` (new, `goc/engine.py`, beside
`render_active_notice`) builds a sentence naming every filter that was
in effect; `_cmd_default`'s table arm substitutes it for the empty
string `render_table` returns. Scoped to that arm: `--json` still
emits exactly `[]` and `--board` still emits only its header, both
pinned by tests, so no machine-readable or grid consumer changes.
`render_table` itself is unchanged and still returns `""` for an empty
list — the message belongs to the command, not the renderer, and a
test pins that too.

Enumerating the filters (rather than a bare "no cards") is what makes
the `--worker` case reachable. `--status` and `--tag` reject unknown
values at parse time, but `worker` is unregistered by design
(AGENTS.md § Card authoring rules), so there is no enum to validate a
typo against; echoing the value back is the only available signal.

### Verification

`reproduce.py` 1 → 0: the three table probes went from `0 bytes /
(nothing)` each and byte-identical, to distinct sentences.

Live deck (`uv run goc --ready -v`), the state that motivated the card:

```
ACTIVE: 6 claimed cards outside this open queue: … Check `goc --status active` or `goc --board` before claiming new work.
No cards match (ready: status open, gate none, no active impediment).
```

and with a filter that matches nothing for a different reason:

```
No cards match (ready: status open, gate none, no active impediment; worker: 'no-such-worker').
```

Suite 897 → 905, green: +8 in `tests/test_empty_query_result_line.py`.
Guard sensitivity checked by neutering `render_empty_query_line` to
return `""` (the pre-fix behaviour) and re-running the module — 12
failures across the three offence-detecting tests and their subTests,
while the `--json` / `--board` / `render_table` / non-empty pins stayed
green. That split is the intended one: those four are contracts the
fix must not break, not detectors of the defect.

`uv run goc validate` clean; `scripts/sync_plugin_assets.py --check`
and `scripts/port_skills_to_openclaw.py --check` both OK after the
mirror sync (3 files: the vendored `goc/engine.py` copies under
`claude-plugin/`, `codex-plugin/`, `openclaw-plugin/`).

### Left open deliberately

The Andon-cord *advisory* — naming the highest-value gated card when
nothing is pullable — stays with
[ready-leverage-line-goes-silent-when-no-card-is-pullable](../ready-leverage-line-goes-silent-when-no-card-is-pullable/),
which is gated on a decision about that line's shape. This card only
restores the statement that the query matched nothing; the two
compose, since the advisory appends after this line when it lands.

## 2026-08-04T05:40:34Z — Closure

- **What changed**: `goc/engine.py` — new `render_empty_query_line`
  beside `render_active_notice`, substituted for `render_table`'s `""`
  in `_cmd_default`'s table arm, so a zero-match query names the
  filters it matched on instead of printing nothing.
- **Verification**: `reproduce.py` 1 → 0 (three table probes: 0/0/0
  bytes and byte-identical → 70/36/96 bytes and distinct); live deck
  `goc --ready -v` now prints `No cards match (ready: status open,
  gate none, no active impediment).`
- **Audit**: no rubric configured; mechanical fix.
- **Project impact**: n/a
- **Tests**: 905 passed / 0 failed / 0 xfailed (897 → 905, +8 in
  `tests/test_empty_query_result_line.py`).
- **Bundled with**: —

## Closure verification (2026-08-04T05:40:48Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 6/6 ticked
- [x] log-md-closure-entry — '## 2026-08-04 — Closure' present

## 2026-08-04: connected to the query-flag-contract root

Post-close generalization check. The pattern — a read surface deciding
on its own how to present shared card-set state — is already
catalogued property-by-property in this deck
([draft-gating-is-opt-in-per-surface-and-new-verbs-keep-missing-it](../draft-gating-is-opt-in-per-surface-and-new-verbs-keep-missing-it/),
[renderers-reimplement-the-dependency-advisory-liveness-gate-and-drift](../renderers-reimplement-the-dependency-advisory-liveness-gate-and-drift/),
closed), and no general umbrella exists because the fix differs per
property. Filing another umbrella would have been the redundant-root
anti-pattern, so this card was CONNECTED instead of duplicated.

Edge added: `advances:
query-flag-validation-is-opt-in-per-flag-and-new-flags-keep-missing-it`.
That root's `## Decision required` asks which mechanism replaces
per-flag opt-in validation; this closure supplies a constraint on the
answer — `--worker` values are unregistered by design, so that flag can
never have an input-side contract and the output-side statement is the
only signal available for it. Recorded as a new
"### One flag can never have an input-side contract" subsection on the
root, which is where a decision-maker will read it.
