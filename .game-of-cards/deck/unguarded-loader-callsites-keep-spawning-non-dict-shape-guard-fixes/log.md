## 2026-11-09T01:58:14Z — Staleness re-check

As-filed anchor gone from HEAD: `engine.py:161`
(`data = yaml.safe_load(m.group(1))`), moved by `05e13fc5`; the
frontmatter-parse call in `parse_frontmatter` now reads
`yaml.safe_load(m.group(1) + m.group(2))`.
Reproducer: none.
Verdict: not verified (no reproducer) — needs a human re-read. Re-anchored
`engine.py:161` → `:253`. Seen in HEAD, not verified: sites #1
(`load_deck_config`) and #3 (canonical-tags loader) now carry per-site
`isinstance(_, dict)` guards; site #2's probe now lives in
`_shared_worktree_deck_root` and still calls `.get` on an unchecked result.
Gate unchanged.
