## 2026-11-09T01:53:57Z — Staleness re-check

As-filed anchors gone from HEAD: `openclaw-plugin/README.md:66`
(`` `python3` (3.10+) on PATH. The plugin invokes the bundled engine via ``)
and `goc.md:214` (`` - **`goc` as a registered OpenClaw tool** — not a shell
binary on PATH ... ``), both reworded by `defb02e4` (launcher path instead of
`python3 -m goc.cli`); the cited claims (no pipx step, not a shell binary on
PATH) still stand.
Reproducer: `reproduce.py` → exit 1, "FAIL: the registered `goc` tool cannot
emit a no-subcommand argv" (plus two further FAIL lines; 0/10 bullets expressible).
Verdict: still live. Re-anchored `goc.md:214` → `:229`;
`openclaw-plugin/README.md:66-68` still spans the same paragraph, left as is.
Gate unchanged.
