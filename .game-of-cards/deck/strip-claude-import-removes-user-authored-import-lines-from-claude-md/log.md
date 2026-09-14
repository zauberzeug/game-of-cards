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
