## 2026-11-02T01:02:06Z — Parked finding: nothing makes `CLAUDE.local.md` gitignored

This is a separate defect, parked here because this card's premise depends on it. It has not been filed as its own card yet: the run that found it filed one new card. Body change: one caveat paragraph at the end of `## Why it matters`. No option text changed, and the gate stays `decision`.

- **Hypothesis**: five shipped surfaces promise that the `CLAUDE.local.md` briefing home stays out of version control:
  - `goc/install.py:61`: the stub header `"# Local notes for Claude Code (not checked in)"`
  - `goc/install.py:1780`: the `--briefing-target` help, `CLAUDE.local.md (gitignored, ...)`
  - `goc/templates/skills/kickoff/SKILL.md:121`: `CLAUDE.local.md` — gitignored, no commit footprint
  - `goc/templates/skills/kickoff/SKILL.md:152-153`: "gitignored by default"
  - `goc/templates/skills/kickoff/reference.md:16-17`: "Check the chosen file in unless it is `CLAUDE.local.md`, which is gitignored by default."

  Yet `goc/install.py` writes no ignore rule and checks for none. Its only `gitignore` occurrence is the help string at `:1780`.
- **Observed by the surfacing agent** (scratch repo, `GIT_CONFIG_GLOBAL=/dev/null`): `goc install --briefing-target CLAUDE.local.md` exited 0. `git check-ignore CLAUDE.local.md` then exited 1, and `git status` showed `?? CLAUDE.local.md`.
- **Why unverified**: the docs may mean Claude Code's own convention for `CLAUDE.local.md` rather than goc's. Whether Claude Code adds the ignore rule itself has not been checked, so it is open whether the bug is a missing write or wrong wording.
- **Falsification recipe**: run the same install in a fresh repo with no global excludes file, open one Claude Code session there, and run `git check-ignore -v CLAUDE.local.md`. If nothing ignores it, either install writes the rule or the five surfaces stop promising it. Kickoff recommends this home for the Solo persona, so a wrong promise reaches new users first.
- **Surfaced by**: an `audit-deck` hunter agent (general-purpose), 2026-11-02.
