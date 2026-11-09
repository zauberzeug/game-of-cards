## 2026-09-14 — refine-deck: stale park verified, promoted

Card had sat 94 days at `unverified` with no prior re-check note — the
only one of this round's six >90-day parks that had never had its
falsification recipe retried. Ran the recipe verbatim against engine
`0.0.27.post1.dev402`: a temp git repo whose `CLAUDE.md` holds user
prose plus a bare `@AGENTS.md`, then
`goc install --briefing-target CLAUDE.md --agents claude`.

Result: install exits 0, the marker block is appended, the user's prose
survives, and the bare `@AGENTS.md` line is deleted. The recipe named
that outcome as promotion, so the `unverified` tag was dropped and the
README's hypothesis / why-deferred / falsification-recipe sections were
rewritten in place into a `## Reproduction` section carrying the
transcript.

Still open: the ownership decision (`## Decision required`) and landing
the transcript as `reproduce.py`. The gate stays at `decision` — the
reproduction settles *whether* the defect is real, not *which* of the
three ownership rules GoC should adopt.

## 2026-11-09T01:58:21Z — Staleness re-check

As-filed anchors gone from HEAD: `goc/install.py:209`
(`def _strip_claude_import(path: Path) -> None:`) and `goc/install.py:229`
(`def _sync_claude_import(target: Path, briefing_target: str) -> None:`), both moved by `0be57d4d`.
Reproducer: none (the `## Reproduction` recipe has not landed as `reproduce.py`).
Verdict: not verified (no reproducer) — needs a human re-read. Reading HEAD: the bare-line filter quoted under
"Confirmed behaviour" is still present verbatim in `_strip_claude_import` (`goc/install.py:267-271`).
Re-anchored `goc/install.py:226-243` → `:256-278` and `goc/install.py:246-283` → `:281-324` (the whole function; the old range stopped one line short of its end).
Gate unchanged.
