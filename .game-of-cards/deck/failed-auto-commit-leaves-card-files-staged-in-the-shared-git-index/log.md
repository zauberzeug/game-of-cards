## 2026-11-16T01:50:00Z — Staleness re-check

As-filed anchor gone from HEAD: `.pre-commit-config.yaml:16`
(`# AGENTS.md § "Card authoring rules" requires English cards. goc's own`),
reworded by `116b2643`, which added the internal-names clause to the
card-language hook's comment and grew it from three lines to four.
Reproducer: `reproduce.py` → exit 1, "BUG: 2 path(s) left staged by the
failed auto-commit" and "BUG: the verb exited 0 and printed its success
line while nothing was committed".
Verdict: still live. Re-anchored `.pre-commit-config.yaml:38-40` → `:38-41`,
the whole comment the card's prose points at. The blockquote under it is the
comment as filed and is left verbatim; its substance (`git commit` without
`--no-verify`, so the hook fires on the filing path) is unchanged in HEAD.
Gate unchanged.
