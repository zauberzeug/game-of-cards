## 2026-11-09T01:58:14Z — Staleness re-check

As-filed anchor gone from HEAD: `goc/engine.py:427`
(`return f"{{who: {_yaml_inline(who)}, where: {_yaml_inline(where)}}}"`),
moved by `1d2778b9` (the return now passes `flow=True` and spans four lines).
Reproducer: `reproduce.py` → exit 1, "FAIL: 4 check(s) show the strict-reader
coercion term is missing." (20 of 20 shapes retyped; branches `1.5` and `off`
still written bare).
Verdict: still live. Re-anchored `goc/engine.py:427` → `:536` at both
occurrences, the `return (` of `_emit_worker`'s flow-mapping branch.
Gate unchanged.
