## 2026-05-08 — Closure

Redesigned `goc/templates/skills/kickoff/SKILL.md` and mirrored the result byte-for-byte to `claude-plugin/skills/kickoff/SKILL.md`.

Changes:

- **Stage 0 now does a state-detection sweep**: deck dir, `goc` on PATH, `<!-- BEGIN GOC -->` markers in CLAUDE.md / AGENTS.md, CLAUDE.local.md presence, `Bash(goc:*)` in either `.claude/settings.json` or `~/.claude/settings.json`. The sweep emits a set of flags the rest of the flow consumes.
- **Stages 1, 2, 3 each declare a "skip if" rule** keyed off the Stage 0 flags. Re-entry on a partially-set-up repo no longer re-asks the intro paragraph (skipped if any prior engagement signal is detected), the persona question (skipped if all three Stage 3 answers are derivable from on-disk state), or any individual merge question whose target file already has its marker.
- **Stage 4 dropped the "write settings.json + restart now" loop**. Kickoff just runs `goc install` directly — when `Bash(goc:*)` is not pre-allowed, Claude Code's interactive permission prompt fires and the user clicks "always allow" once. Claude Code records the grant in `.claude/settings.json` automatically. No restart required.
- **New Stage 5 persists the permission for future sessions** as the LAST mutation kickoff makes, but only if Stage 0 detected the allowance was missing AND the interactive grant in Stage 4 did not write it. The note to the user is "current session continues to work without a restart" — the restart is no longer blocking.
- **Stage 6 unchanged** — final confirmation message.

Verified manually: `diff -q` confirms the two SKILL.md copies are byte-for-byte identical (CI tripwire requirement). `uv run goc validate` passes.

The marketplace-submission card and the `rename-bootstrap-to-kickoff-as-onboarding-dialog` card both gain this as a closed prereq, since the kickoff UX is the first impression any community-marketplace consumer will have.

## Closure verification (2026-05-08)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — all 1 done
- [x] dod-100-percent — 6/6 ticked
- [x] log-md-closure-entry — '## 2026-05-08 — Closure' present
