## 2026-11-09T02:26:58Z — Pasted output restored to what was printed

The `Cited code: goc/engine.py:…` line in § Empirical evidence is `reproduce.py` output, and the script prints `4593` verbatim. The 2026-08-10, 08-17 and 08-24 hygiene passes (`69e1e4f2`, `f290f5f7`, `e8449764`) ran before fenced records were ruled out of scope (`eae2bea9`), and renumbered it `4593` → `6427` → `6675` → `6786`. Restored to `4593`, matching what the reproducer prints.
