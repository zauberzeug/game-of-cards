## 2026-11-09T01:54:48Z — Staleness re-check

As-filed anchors gone from HEAD: `goc/install.py:773`
(`def _strip_claude_vendored_harness(target: Path, templates: Path) -> None:`), changed by
`3e48d39b` (gained `*, probe: bool = False`, returns bool), and `install.py:776`
(`Removes only the skill directories whose names match GoC templates,`), reworded by `d07fd621`.
Reproducer: `reproduce.py` → exit 1, "BUG REPRODUCED: prior-version GoC content survives cleanup".
Verdict: still live. Re-anchored `goc/install.py:856-906` → `:928-992` (summary and Location)
and `install.py:859-862` → `:931-934`. That docstring paragraph now says "skill directories
`_goc_skill_names` lists", so the card's quoted wording is no longer verbatim.
Gate unchanged.
