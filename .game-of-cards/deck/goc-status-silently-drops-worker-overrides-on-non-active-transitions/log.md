## 2026-10-30: re-checked — the defect still fires, but the reproducer no longer reaches it

On hand-written authored cards, `goc status <t> open --worker-who alice
--worker-where feature/x` from `active`, and `goc status <t> disproved
--worker-who alice` from `open`, both exit 0 and write no `worker`.

`reproduce.py` still prints `DEFECT REPRODUCED (3/3 …)`, but it no longer
tests the path this card documents. `goc new` now writes draft scaffolds, so
the draft guard refuses its `disproved` and `superseded` probes (exit 2),
and the script counts those refusals as drops. Its `open` probe starts from
`open`, so it hits the same-status no-op rather than a transition. Rebuild
the probes on authored (non-draft) cards, and start the `open` probe from
`active`, before ticking the TDD item.
