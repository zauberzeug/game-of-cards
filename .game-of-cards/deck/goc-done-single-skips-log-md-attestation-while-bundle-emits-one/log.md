
## 2026-08-31 — refine-deck: stale park re-checked, kept

93 days parked. Re-read against HEAD: the asymmetry is unchanged.
`_cmd_done_bundle` still writes both an attestation block and a
`— Closure (bundled)` entry into each member's `log.md`
(`goc/engine.py:4938-4944`); `_cmd_done` (single) still writes nothing to
`log.md` at all — a grep of the whole single-close function for `log.md`
or `Closure` returns zero hits.

Kept parked rather than promoted. The card's own summary already names why:
the asymmetry may be intentional (a bundle has a structured payload — the
co-closing member set — that a single close does not), so a `reproduce.py`
would only re-state what the two functions plainly say. What is missing is
the intent call, not the evidence, and that is the decision gate's job.
