## 2026-05-29T15:13:43Z: decision deliberation archived

Archived from the README's `## Decision required` section by `goc decide` before it was replaced with the resolved `## Decision` block — README is the dashboard, log.md is the journal. This preserves the options and recommendation that produced the decision below.

Two credible fix paths:

**Option A — CLI guard only.** Add a check in `_cmd_status` that
refuses `superseded` as the target status when `--by` is not
provided. Pro: fail-fast at the input boundary; clearer error
message. Con: hand-authored YAML can still produce the orphan state
and pass `goc validate`.

**Option B — Validator check only.** Add the inverse check at
`goc/engine.py:1255-1260`:

```python
if status_value == "superseded" and not superseded_by:
    errors.append(
        f"{t.title}: status: superseded requires non-empty superseded_by"
    )
```

Pro: catches both CLI and hand-edited paths at one place. Con:
deferred failure — the user sees the error at `goc validate` time,
not at the `status` invocation that produced it.

**Option C — Both.** CLI refuses the input at the source; validator
catches drift from hand-edits and direct frontmatter writes. The
cost is two checks that overlap by design; the win is the same
defense-in-depth that `goc done`'s DoD gate + `goc validate`'s
closure-gate already share.

Recommend Option C, but the maintainer picks.


## 2026-05-30T13:36:43Z: decision recorded

Both: a CLI guard in _cmd_status refuses 'goc status <card> superseded' when --by is absent, AND the validator rejects status:superseded with empty superseded_by — defense-in-depth — the CLI guard fails fast at the input boundary with a clear message while the validator catches hand-edited and direct-frontmatter drift, matching the same dual-gate pattern that goc done's DoD-gate + goc validate already share. Gate decision → none.

## 2026-05-30: fix landed

Implemented Option C (both gates):

- Validator (`goc/engine.py` `validate_card`): added an inverse check next to the existing `superseded_by → status: superseded` rule — `status: superseded` with empty `superseded_by` now emits `status: superseded requires non-empty superseded_by (forward routing pointer; set via goc status <c> superseded --by <new>)`.
- CLI (`goc/engine.py` `_cmd_status`): added an input guard next to the existing reverse check — `goc status <c> superseded` with no `--by` now exits 2 with `ERROR: status superseded requires --by <successor> (the typed forward routing pointer; without it a cold reader landing on <c> has nowhere to go)`.

Regression test: `tests/test_superseded_requires_by.py` (two cases — CLI refusal without mutation, validator rejection on a hand-edited orphan card).

Reproducer now returns exit 1 ("FIXED: the orphan supersession state is no longer reachable"). Full 309-test suite green; plugin mirrors regenerated; `goc validate` clean. `goc done` is unaffected — it already gates on `human_gate` and DoD; the new CLI guard sits one level earlier in `_cmd_status` so a `superseded` transition can never reach the closure-data write without a successor.
