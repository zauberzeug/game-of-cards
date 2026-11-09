## 2026-11-09T01:58:14Z — Staleness re-check

As-filed anchor gone from HEAD: `goc/engine.py:5221`
(`return mutate_frontmatter_field(text, "worker", worker_yaml)`), moved by
`1d2778b9` (the value now renders through `_emit_worker(worker)`).
Reproducer: `reproduce.py` → exit 0 (inverted: prints "DEFECT REPRODUCED:
appended field wedged inside the keep scalar's trailing blank run; scalar
silently lost its final newline").
Verdict: still live. Re-anchored `goc/engine.py:5902` (as-filed `:5221`) → `:6728`.
Gate unchanged.
