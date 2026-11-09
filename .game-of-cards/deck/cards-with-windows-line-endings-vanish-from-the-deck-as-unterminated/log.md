## 2026-11-09T01:58:14Z — Staleness re-check

As-filed anchors gone from HEAD: `goc/engine.py:130` and `engine.py:130`
(`FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.DOTALL)`),
moved by `05e13fc5` (pattern rewritten since; still LF-only).
Reproducer: `reproduce.py` → exit 1, "RESULT: DEFECT PRESENT — opener guard
accepted '---\r\n' but the regex rejected it as unterminated."
Verdict: still live. Re-anchored `goc/engine.py:130` → `:220` (Location) and
`engine.py:130` → `:220` (DoD). The Location bullet still quotes the
as-filed pattern; only the number changed.
Gate unchanged.
