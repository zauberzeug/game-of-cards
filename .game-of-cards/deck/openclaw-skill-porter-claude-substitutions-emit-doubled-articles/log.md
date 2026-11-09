## 2026-11-09T01:54:43Z — Staleness re-check

As-filed anchors gone from HEAD: `openclaw-plugin/skills/kickoff/SKILL.md:172`
(``briefing. `--briefing-target CLAUDE.md` is the the agent-only path: ...``),
moved by `8a1af2f5` (kickoff split into SKILL.md + reference.md sibling).
Reproducer: `reproduce.py` → exit 1, "FAIL: 6 ungrammatical substitution
artifact(s) in ported skills." (kickoff :139/:149, openclaw-kickoff :81/:83/:88,
plus a new one at `openclaw-plugin/skills/deck/SKILL.md:36`).
Verdict: still live. Not placed: `openclaw-plugin/skills/kickoff/SKILL.md:172`
— the sentence now sits in `openclaw-plugin/skills/kickoff/reference.md:22`, a
verbatim-copied sibling where it reads "the Claude-only path" (no doubled
article), so no home carries the cited artifact; left as is.
Gate unchanged.
