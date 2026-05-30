## 2026-05-29T21:37:45Z: decision deliberation archived

Archived from the README's `## Decision required` section by `goc decide` before it was replaced with the resolved `## Decision` block — README is the dashboard, log.md is the journal. This preserves the options and recommendation that produced the decision below.

Two fix shapes are credible; pick before implementing.

**Option A — Port siblings verbatim (broadest fix).** Extend the porter to walk `skill_dir.rglob("*")`, port `SKILL.md` through `render_skill`, and copy every other file unchanged. Extend `drifted_skills()` symmetrically: for each sibling, compare bytes. Also extend `_orphaned_ported_dirs` (or add a sibling-orphan check) so a removed sibling is detected. Matches the shape of the four other consumers; future sibling assets get coverage for free.

**Option B — Port the one sibling we have (narrowest fix).** Hard-code `schema.yaml` as the one bundled sibling and copy/compare it. Leaves the structural defect in place; the next sibling asset re-introduces the bug.

**Recommendation: Option A.** The four other consumers already walk full trees; aligning the OpenClaw porter removes the only outlier and matches the cross-host parity promise the `AGENTS.md` paragraph implies. Option B's only advantage is smaller diff; the cost is re-litigating this card the next time a skill grows a companion file.

Open sub-questions Option A inherits:
1. Should siblings ever be transformed (like `SKILL.md` goes through `render_skill`)? Today the only sibling is plain YAML with no host-specific syntax, so a verbatim copy is correct. If a future sibling carries host-specific references, the porter would need a per-extension dispatch — but that's a future card, not this one.
2. Are there file shapes worth excluding (`__pycache__`, `*.pyc`)? `_iter_skill_assets` in `goc/install.py:875` excludes `__pycache__` explicitly. Mirror that exclusion in the porter.


## 2026-05-30T13:56:58Z: decision recorded

Option A: extend the porter to walk skill_dir.rglob('*') — port SKILL.md via render_skill and copy every other file verbatim (excluding __pycache__/*.pyc, mirroring _iter_skill_assets); extend drifted_skills() and the orphan check symmetrically for siblings — aligns the OpenClaw porter with the four other plugin consumers that already walk full trees, honors the cross-host parity promise, and gives future sibling assets coverage for free instead of re-litigating this card each time a skill grows a companion file. Gate decision → none.
