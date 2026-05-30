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
