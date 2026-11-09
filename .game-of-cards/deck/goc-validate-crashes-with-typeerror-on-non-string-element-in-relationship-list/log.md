## 2026-11-09T01:58:14Z — Staleness re-check

As-filed anchor gone from HEAD: `goc/engine.py:161`
(`data = yaml.safe_load(m.group(1))`), moved by `05e13fc5`; the
frontmatter-parse call in `parse_frontmatter` now reads
`yaml.safe_load(m.group(1) + m.group(2))`.
Reproducer: `reproduce.py` → exit 1, "VERDICT: defect reproduces — validator
crashed with raw traceback." The traceback is the card's own defect
(`TypeError: unhashable type: 'list'` at `elif ref not in all_titles:` in
`validate_card`), not a harness crash.
Verdict: still live. Re-anchored `goc/engine.py:161` → `:253`.
Gate unchanged.
