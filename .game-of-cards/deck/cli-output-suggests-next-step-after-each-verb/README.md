---
title: cli-output-suggests-next-step-after-each-verb
summary: "Every successful goc verb that mutates state should print a one-line Next: hint pointing at the natural follow-up action. The verb's stdout is part of the LLM's tool-call result and the most reliable channel to keep the methodology flow visible — more reliable than expecting the agent to have read goc.md or AGENTS.md. `goc install` already does this; the rest of the verb surface doesn't."
status: open
stage: null
contribution: medium
created: 2026-05-05
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [story, infra]
definition_of_done: |
  - [ ] Audit done: list of every `click.echo` line in `goc/cli.py`, `goc/engine.py`, and `goc/install.py` that fires on a successful state mutation
  - [ ] Each verb with an obvious natural next-step gets a one-line `Next:` hint appended to its success path (style matching the existing `goc install` hint)
  - [ ] Hints align with the AGENTS.md operating modes — autonomous loop (pull-card), Andon-cord (decide-card), session work (advance-card → implement → finish-card)
  - [ ] Hints are NOT printed on `--dry-run` or no-op success paths ("already installed", "already at goc X", etc.) so they don't add noise to non-action invocations
  - [ ] Hints are tested via existing CI's `goc --version` and `goc validate` smoke matrix (or a new minimal stdout-capture test if one is warranted)
  - [ ] No flag or behavior changes — additions are stdout-only
  - [ ] `uv run goc validate` passes
---

# CLI output suggests the natural next step after each verb

## Why

`goc` is the substrate for an LLM-first methodology. When an agent runs a goc verb, the verb's stdout becomes part of the agent's tool-call result and influences what the agent does next. The most reliable channel for "remind the LLM to do X next" is therefore the verb's own output line — more reliable than expecting the agent to have read goc.md, AGENTS.md, or any skill body before this run.

`goc install` already exhibits the pattern. Commit `65e222b` ("install: redirect 'Next:' hint to extend-deck for fresh installs") established the seed: after installation, the install command prints `Next: ask your LLM agent to "expand the deck" — it audits the repo and files initial cards.` That single line is the difference between an LLM that knows to suggest the next move and one that stalls after the install completes.

The rest of the verb surface doesn't yet do this. After `goc done <card>`, the LLM sees just `<title>: open → done` — no hint that the natural follow-up is `goc` (show queue) or `pull-card` (claim the next). After `goc decide`, no hint that the gate is now lowered and any agent can claim. The methodology's state transitions are designed for handoff, but the CLI doesn't surface those handoffs.

## Tentative verb→hint mapping

To refine during implementation. The principle: name the natural next action *for the role currently driving the work*. If a human just lowered a gate, the next mover is an agent; if an agent just finished a card, the next mover is either another agent or the human checking the queue.

| Verb | Success state | Tentative `Next:` hint |
|---|---|---|
| `goc install` | done (already implemented) | `Next: ask your LLM agent to "expand the deck"...` |
| `goc upgrade` | sync complete | `Next: re-run goc validate to confirm cards parse against the new schema.` |
| `goc new <title>` | card scaffolded | `Next: edit deck/<title>/README.md to fill the body and DoD; then ask your agent to implement the card.` |
| `goc status <title> active` | claim recorded | `Next: implement the card; tick DoD items as you go; then goc done <title>.` |
| `goc done <title>` | card closed | `Next: goc to see what's open, or ask your agent to "drain the queue" (pull-card).` |
| `goc decide <title>` | gate lowered | `Next: gate lowered to none — any agent can now claim this card. goc to see the queue.` |
| `goc advance <title> --by <other>` | edge added | (no hint — relationship-graph mutation, not a state transition that needs a follow-up) |
| `goc validate` | parse OK | (no hint — the success message IS the answer) |
| `goc triage` | parked cards listed | `Next: ask your agent for "decisions to make" (Skill(scan-deck) decisions to make) to walk them in one round.` |
| `goc attest` | attestation written | `Next: goc done <title> to close once attest passed and DoD ticks complete.` |
| `goc move` | rename committed | (no hint — mechanical) |
| `goc unadvance` | edge removed | (no hint — graph cleanup) |
| `goc quality-pass` | findings listed | `Next: re-title flagged cards via goc move <old> <new>.` |

## Style

- One line per hint. The existing `goc install` hint is a useful format reference.
- Lead with `Next: ` (matches the install precedent).
- Name a concrete action — a verb the user/agent can run, or a skill they can invoke.
- Don't echo the hint on `--dry-run`, `--help`, or no-op success paths ("already installed", "no cards parked", etc.).
- Don't add hints to verbs whose success message already contains the answer (`goc validate`, `goc move`).

## Notes

- The pattern is purely additive: stdout text only, no flag changes, no behavior changes. CI's existing `goc --version` and `goc validate` smoke matrix should be sufficient unless a future change flips a default that depends on hint presence.
- The audit might surface other `click.echo` calls that are misclassified — error-path messages that look like success, or success paths that should be silenced under certain flags. Address those as bonus findings or split into companion cards.
