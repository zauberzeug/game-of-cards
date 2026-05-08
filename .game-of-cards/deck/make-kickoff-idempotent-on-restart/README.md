---
title: make-kickoff-idempotent-on-restart
summary: "Today's kickoff skill writes `.claude/settings.json` mid-flow, instructs the user to fully restart Claude Code, and then expects to 'resume at Stage 5' — but Claude Code sessions are episodic. Restarting without `-r` drops conversation context, and a fresh `Skill(kickoff)` invocation only checks Stage 0 (`.game-of-cards/deck/` exists?). All other stages — intro, persona, three merge questions — are re-asked from scratch. Surfaced today during Rodja's pre-submission smoke test: after the restart prompt, a new session re-asked every kickoff question even though the user had already answered them once. Two design changes are needed in lockstep: (a) make kickoff idempotent via on-disk state detection so a re-run on a partially-set-up repo only asks for the answers not yet captured (preferred over a progress file per Rodja's choice); (b) restructure stage ordering so the restart-required stage — if any — is the LAST stage, with everything else (persona, merges, `goc install`, settings.json write) happening before it. Ideally drop the mandatory mid-flow restart entirely by relying on Claude Code's interactive permission prompt when `goc install` runs without a pre-existing `Bash(goc:*)` allowance."
status: done
stage: null
contribution: medium
created: 2026-05-08
closed_at: 2026-05-08
human_gate: none
advances:
  - list-game-of-cards-on-anthropic-community-marketplace
advanced_by:
  - rename-bootstrap-to-kickoff-as-onboarding-dialog
tags: [bug, documentation]
definition_of_done: |
  - [x] `goc/templates/skills/kickoff/SKILL.md` reorders stages so any step that requires a Claude Code session restart sits at the END of the flow — `goc install` runs first, settings.json write follows, and the restart suggestion (if still present) is final and optional. The user must never lose work-in-progress to a mid-flow restart.
  - [x] On re-entry into a partially-set-up repo, kickoff detects on-disk state in a single Stage 0 sweep (deck dir, `<!-- BEGIN GOC -->` markers in CLAUDE.md / AGENTS.md / CLAUDE.local.md, `Bash(goc:*)` in `.claude/settings.json` or `~/.claude/settings.json`, `goc` on PATH) and only asks for the answers it cannot derive — no progress file required
  - [x] Stage 4's restart instruction is replaced (or moved): kickoff runs `goc install` directly and relies on Claude Code's interactive permission prompt for `Bash(goc:*)` when the allowance is absent. After install, kickoff persists the permission to `.claude/settings.json` so future sessions are silent. No "fully restart now" instruction in the middle of the flow
  - [x] If a restart is still genuinely needed (e.g., for a permission to be canonical in new sessions), the instruction appears only AFTER all other stages — including `goc install` — have completed successfully
  - [x] `claude-plugin/skills/kickoff/SKILL.md` is updated byte-for-byte to match the template (CI tripwire `validate_skill_dir_parity` enforces this)
  - [x] `uv run goc validate` passes
worker: {who: Rodja Trappe, where: main}
---

# Make kickoff idempotent on restart

## Why

Today's kickoff skill assumes Claude Code preserves conversation state
across a session restart, which is not the case unless the user runs
`claude -r` (resume). The skill body even ends Stage 4 with:

> "**fully restart Claude Code** for the change to take effect... After
> restart, say 'continue' and I'll resume at Stage 5."

But on a normal restart, the new session has no memory of where the
previous one was. A fresh `Skill(kickoff)` invocation runs through
Stage 0 (which only checks `.game-of-cards/deck/`), finds the deck
still missing (because Stage 5 was the install step that never ran),
and starts over from Stage 1 — re-asking every question.

Rodja hit this in today's pre-submission smoke test: kickoff wrote
`.claude/settings.json`, asked for a restart, the user restarted
without `-r`, and the new session asked everything again.

## Design (Rodja's pick: state-detection)

Replace the implicit "you need a progress file" model with on-disk
detection. Each piece of kickoff state has a natural artefact:

| Stage | On-disk signal |
|---|---|
| Deck scaffolded | `.game-of-cards/deck/` directory |
| CLAUDE.md merge | `<!-- BEGIN GOC -->` marker in CLAUDE.md |
| AGENTS.md merge | `<!-- BEGIN GOC -->` marker in AGENTS.md |
| CLAUDE.local.md stub | file presence |
| `Bash(goc:*)` permission | `permissions.allow` entry in `.claude/settings.json` or `~/.claude/settings.json` |
| `goc` on PATH | `which goc` exit status |

A single Stage 0 sweep reads all of these, presents a state summary,
and routes accordingly:

- Deck present → exit silently ("GoC is already set up.")
- Goc missing → halt with install instructions
- Otherwise → ask only the questions whose answers are not already
  derivable from the on-disk artefacts

The persona question is special: it has no direct artefact. But it
only drives Stage 3 defaults — if Stage 3's answers are already
recoverable from markers, persona is irrelevant on re-entry.

## Restart should be last (Rodja's clarification)

The deeper fix is to remove the mandatory mid-flow restart. The
current sequence is "ask everything → write settings.json → restart →
resume at Stage 5." A better sequence is:

1. State-detection sweep.
2. Intro / persona / merge questions (chat only — no Bash needed).
3. Run `goc install` directly. If `Bash(goc:*)` is not pre-allowed,
   Claude Code's interactive permission prompt fires; the user
   approves once and the install runs. No settings.json write needed
   at this point because Claude Code's "always allow" option writes
   it automatically.
4. If the interactive grant did not happen (e.g., user is running in
   `--permission-mode dontAsk` and the allowance was missing), kickoff
   writes `.claude/settings.json` itself. This becomes the LAST step.
5. Optionally tell the user "for the canonical permission to be live
   in fresh sessions, restart Claude Code at your convenience" — but
   not as a blocking step. The current session is fully set up.

If a restart is genuinely required for some future enhancement, it
must remain the last stage so even a context-losing restart leaves
the deck and merges already in place.

## Out of scope

- A general "save kickoff progress to a file" mechanism. The user
  picked state-detection over a progress file; the latter would
  introduce a tracked-but-ephemeral file (`.kickoff-state.yaml` or
  similar) that consumers would have to ignore. State-detection
  reuses signals that already exist for other reasons.
- Persuading Claude Code upstream to reload `settings.json` mid-
  session. That would obviate the restart pattern entirely but is
  out of our reach.
- Reworking the persona Q&A. The four-persona prompt stays — only
  its idempotency-on-re-entry behaviour changes.

## Cross-references

- `rename-bootstrap-to-kickoff-as-onboarding-dialog` (done) —
  introduced the current kickoff skill body that this card refines.
- `list-game-of-cards-on-anthropic-community-marketplace` (open,
  gate=decision) — depends on this card; the kickoff UX is the
  first impression any marketplace consumer will have.
