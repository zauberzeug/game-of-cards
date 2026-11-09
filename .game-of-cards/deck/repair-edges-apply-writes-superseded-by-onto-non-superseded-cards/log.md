## 2026-11-09T02:00:12Z — Staleness re-check

As-filed anchor gone from HEAD: `goc/engine.py:4762` (`structural = []`),
removed by `c472b3dd`.
Reproducer: `reproduce.py` → exit 1, crashed: "RuntimeError: goc new card-a failed"
— `goc new` refuses without a deck since `3e17e3b3`, and the harness never creates
`.game-of-cards/deck/` in its temp dir. A scratch copy adding only that `mkdir`
prints "3 defect signal(s)"; that copy is not the card's reproducer.
Verdict: not verified (reproducer crashed: `goc new` refuses without a deck) —
needs a human re-read.
Not placed: `goc/engine.py:4762-4776` — `c472b3dd` split the block: the cycle gate
now runs in `_classify_half_edges` (`:7230-7251`), the mutating loop is `:7286-7289`.
Gate unchanged.
