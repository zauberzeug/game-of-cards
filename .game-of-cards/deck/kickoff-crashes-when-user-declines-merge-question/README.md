---
title: kickoff-crashes-when-user-declines-merge-question
summary: "Stage 4 of the kickoff onboarding skill instructs the model to invoke `goc install --no-claude-md` or `goc install --no-agents-md` based on the user's per-file merge answers. Neither flag exists in `goc/cli.py` or `goc/install.py` — the parser only knows `--dry-run`, `--agents`, `--claude`, `--codex`, and `--local-skills`. Any user who answers \"No\" to either merge question crashes Stage 4 with `goc install: error: unrecognized arguments: --no-claude-md` and leaves the repo un-initialized. Found during a 2026-05-09 review of the `make-kickoff-idempotent-on-restart` and `rename-bootstrap-to-kickoff-as-onboarding-dialog` work."
status: done
stage: null
contribution: high
created: 2026-05-09
closed_at: 2026-05-09
human_gate: none
advances:
  - list-game-of-cards-on-anthropic-community-marketplace
advanced_by: []
tags: [bug]
definition_of_done: |
  - [x] Reproduce: in a tmpdir, run the kickoff Stage 4 install command with `--no-claude-md` and confirm the parser error
  - [x] Fix path chosen (see Decision required) and implemented in `goc/cli.py` + `goc/install.py` and/or `goc/templates/skills/kickoff/SKILL.md`
  - [x] Plugin mirror copy of `kickoff/SKILL.md` synced (per `validate_plugin_mirror_parity`)
  - [x] Regression test exercises the per-file-decline path end-to-end
  - [x] `uv run goc validate` passes
  - [x] Manual verification: kickoff completes cleanly when the user answers "No" to both CLAUDE.md and AGENTS.md merge questions
worker: {who: "claude[bot]", where: main}
---

# Kickoff crashes when user declines a merge question

## Reproduction

The kickoff skill at
[`goc/templates/skills/kickoff/SKILL.md:167-169`](../../../goc/templates/skills/kickoff/SKILL.md)
(byte-identical mirror at `claude-plugin/skills/kickoff/SKILL.md`)
prescribes for Stage 4:

> Run `goc install` with the merge flags chosen in Stage 3:
> - If the user said "No" to CLAUDE.md, append `--no-claude-md`.
> - If the user said "No" to AGENTS.md, append `--no-agents-md`.

Neither flag exists. `goc/cli.py` registers only `--dry-run`,
`--agents`, `--claude`, `--codex`, and `--local-skills` for the
`install` subcommand. argparse rejects unknown flags hard:

```
goc install: error: unrecognized arguments: --no-claude-md
```

So a kickoff run where the user declines either merge crashes at the
exact moment it's supposed to scaffold project state. The user is
left with a half-initialized repo and a confusing CLI error.

## Decision

*Resolved 2026-05-09:* Drive the per-file merge from the kickoff skill body. Stage 4 calls plain 'goc install' (no negative flags) and then conditionally strips the marker-bounded GoC block from CLAUDE.md and/or AGENTS.md based on the user's Stage 3 answers, using sed or equivalent inside the skill body.

*Reasoning:* Per-file UX is a UX concern that belongs in the kickoff skill, not the install primitive. Keeping the CLI minimal means no future drift between '--claude' (agent toggle) and '--no-claude-md' (file toggle), and the install command stays a simple primitive that callers compose against.
## Notes

- This is a regression introduced by either
  `rename-bootstrap-to-kickoff-as-onboarding-dialog` (2026-05-08) or
  `make-kickoff-idempotent-on-restart` (2026-05-08) — neither card's
  DoD verified the decline-merge path end-to-end.
- The plugin path and the local-skills path are equally affected
  because the skill body is identical in both consumer copies.
- A regression test that drives kickoff through Stage 4 with each
  combination of (yes, no) answers would prevent recurrence and is
  worth filing as a sub-task of whichever fix path is chosen.

## Cross-references

- `rename-bootstrap-to-kickoff-as-onboarding-dialog` (done) — introduced
  the four-stage dialog
- `make-kickoff-idempotent-on-restart` (done) — extended kickoff;
  did not catch the missing flags
- `make-claude-md-and-agents-md-merge-opt-in-via-skill` (superseded) —
  ruled out option C above
