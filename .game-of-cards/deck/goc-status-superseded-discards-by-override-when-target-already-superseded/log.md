## 2026-10-30: re-checked — still fires; the reproducer aborts in setup; a later decision bears on the options

On hand-written cards, `goc status foo superseded --by bar` followed by
`goc status foo superseded --by baz` still prints `foo: already superseded;
nothing to do` and exits 0. `foo.superseded_by` stays at `bar`, and
`baz.supersedes` never gains `foo`. The same-status early return in
`_cmd_status` still runs before both the successor wiring and the
terminal-status refusal.

`reproduce.py` no longer gets that far. `goc new` now writes draft
scaffolds, and the draft guard refuses its first `goc status foo superseded
--by bar` (exit 2). Rebuild its setup on authored (non-draft) cards before
ticking the TDD item.

Two facts for the decision, both newer than this card:

- Option 1 (honor the redirect) would make `goc status` rewrite a closed
  card's record. The closed `terminal-status-guard-missing-across-mutation-verbs`
  (decided 2026-10-22) has `_refuse_terminal_mutation` refuse that for
  `wait`, `attest`, `quality-pass` and `move`, and that helper's docstring
  already states that `_cmd_status` refuses every terminal card, which holds
  everywhere except this same-status path.
- Option 2's sketched message tells the operator to release the supersession
  and then re-supersede, but no verb releases one. `goc status` refuses to
  move a terminal card, `goc unadvance` handles only `advances` edges, and
  the one `_mutate_pair` call on the supersession pair, in `_cmd_status`,
  passes `add=True`. A refusal would have to name a path that exists, such as
  hand-editing both cards and then running `goc validate`, or the
  "After closure" amendment `_refuse_terminal_mutation` names.
