---
title: rename-bootstrap-to-kickoff-as-onboarding-dialog
summary: "Rename `Skill(bootstrap)` → `Skill(kickoff)` and expand it from a quiet scaffolder into the project's actual onboarding dialog. Today bootstrap silently runs `goc install` if `.game-of-cards/deck/` is missing; users get no introduction to GoC, no choice about the AGENTS.md / CLAUDE.md merge, no team/solo question, and no preflight check that `goc` is callable with the right permissions. Kickoff turns first contact into an interactive four-stage dialog: (1) one-paragraph introduction to GoC, (2) persona question (solo / classical team / OSS-eval / agent-runtime — vocabulary inherited from `define-personas-and-use-cases-for-game-of-cards`), (3) per-file opt-in for CLAUDE.md / AGENTS.md / CLAUDE.local.md merges (each a separate yes/no, not a single bundled choice), (4) infrastructure preflight (`goc --version` callable + `Bash(goc:*)` permission probe, with actionable remediation copy pointing at PyPI install and `settings.json` permission entries when checks fail). The persona answer drives downstream questions — classical team gets a pointer to the external-deck-location card, vibe-coder skips the CLAUDE.md merge entirely, agent-runtime gets a hook-only setup. This supersedes `make-claude-md-and-agents-md-merge-opt-in-via-skill` because the merge-opt-in concern is fully solved as part of the richer skill. The `kickoff` name was chosen over `game-of-cards` because it speaks the agile-vocabulary lineage out loud (Sprint-0 / project kickoff) and pairs with the broader vocabulary alignment in `align-skill-names-with-agile-vocabulary`."
status: open
stage: null
contribution: high
created: 2026-05-08
closed_at: null
human_gate: none
advances:
  - make-claude-md-and-agents-md-merge-opt-in-via-skill
advanced_by:
  - define-personas-and-use-cases-for-game-of-cards
tags: [story]
definition_of_done: |
  - [ ] Skill renamed: `goc/templates/skills/bootstrap/` → `goc/templates/skills/kickoff/`, plugin duplicate at `claude-plugin/skills/bootstrap/` → `claude-plugin/skills/kickoff/` in lockstep; CI byte-for-byte template-vs-plugin check still passes
  - [ ] Skill body implements four-stage dialog: (1) one-paragraph "what is GoC" intro, (2) persona question with vocabulary from the personas card, (3) per-file merge opt-in (CLAUDE.md, AGENTS.md, CLAUDE.local.md as three independent yes/no questions), (4) infra preflight: `goc --version` callable check + `Bash(goc:*)` permission probe, with concrete remediation strings for both failure modes (`uv tool install goc` / settings.json snippet)
  - [ ] AUTO-INVOKE description rewritten: triggers on "kickoff", "set up GoC", "use GoC here", "initialize GoC", and first GoC-skill use in a repo missing `.game-of-cards/deck/`
  - [ ] Hook scripts updated: `goc/templates/hooks/deck_session_start.py` and `goc/templates/hooks/deck_prompt_router.py` (and their byte-for-byte `claude-plugin/hooks/` duplicates) reference `Skill(kickoff)` wherever they hint at first-time setup
  - [ ] Documentation updated: `goc/templates/AGENTS_GOC.md`, `goc/templates/CLAUDE_GOC.md`, `AGENTS.md`, `CLAUDE.md`, and the README skill-surface listing all reflect the new name
  - [ ] `goc upgrade` on a repo previously installed with `Skill(bootstrap)` cleanly transitions to `Skill(kickoff)` — old skill folder removed, no orphan files
  - [ ] On close, file a closure entry in `make-claude-md-and-agents-md-merge-opt-in-via-skill/log.md` noting it is superseded by this card and close that card
---

# rename-bootstrap-to-kickoff-as-onboarding-dialog

## Why this is more than a rename

`Skill(bootstrap)` today is a silent scaffolder: it runs `goc install` if
`.game-of-cards/deck/` is missing and exits. Three pain points motivate
the expansion:

1. **No introduction.** A first-time user invoking GoC gets project
   state without ever being told what GoC is or why the deck folder
   appeared. The methodology lineage (XP / Kanban / Scrum) is invisible
   at the moment of first contact.
2. **The merge is not opt-in.** `goc install` writes the GoC marker
   block into `AGENTS.md` and `CLAUDE.md` unconditionally — the most
   invasive thing the tool does, and a known blocker for OSS / library
   evaluators. The existing `make-claude-md-and-agents-md-merge-opt-in-via-skill`
   card carved out this concern; this card absorbs it.
3. **Infrastructure failures surface late.** `bootstrap-error-when-cli-not-on-path`
   documents the case where the skill assumes `goc` is callable when it
   is not. A preflight check at kickoff time turns a mid-workflow trap
   into a clear, actionable first-screen prompt.

## The four-stage dialog

```
[1] Intro       — one paragraph, persona-neutral, sets methodology lineage
[2] Persona     — solo / classical team / OSS-eval / agent-runtime
[3] Merge opt-in — CLAUDE.md? AGENTS.md? CLAUDE.local.md? (three separate y/n)
[4] Preflight   — goc --version callable? Bash(goc:*) permission?
```

The persona answer is the routing key. Classical team paths to the
external-deck-location guidance; vibe-coder skips stages 3-4's merge
questions; agent-runtime defaults to hook-only.

## Why `kickoff` and not `game-of-cards`

The earlier merge-opt-in card proposed renaming `bootstrap` →
`game-of-cards` so that invoking the skill *was* the explicit opt-in
act of "calling the product by name". `kickoff` was chosen instead
because it pairs with the vocabulary alignment in
`align-skill-names-with-agile-vocabulary` — together they advertise the
agile lineage at the skill surface. The opt-in nature is preserved by
making each merge a separate explicit y/n question inside the dialog,
not by overloading the skill name itself.

## Out of scope

- Designing the persona list — that lives in
  `define-personas-and-use-cases-for-game-of-cards` (`advanced_by`).
- The vocabulary alignment for other skills — see
  `align-skill-names-with-agile-vocabulary`.
- Any change to `goc install` CLI behavior; `kickoff` is the
  Claude-Code-side surface and may continue to call `goc install` under
  the hood with appropriate flags.
