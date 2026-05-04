---
title: goc-install-command-scaffolds-repo
summary: "The `goc install` flow that drops the methodology into a target repo: extract skill templates from package data, write `.claude/skills/`, scaffold `deck/` directory + log.md, append CLAUDE.md sections, install the `UserPromptSubmit` hook, register the validator pre-commit hook. Idempotent — safe to re-run; detects existing install and offers `goc upgrade` instead. Mirrors `specify init`, `bmad install`, `agent-os install` patterns. The actual decision of WHICH agents to populate shims for is delegated to `goc-multi-agent-shim-which-agents-at-v1`; this card scaffolds Claude-side artifacts as the v1 baseline."
status: done
stage: null
contribution: high
created: 2026-05-03
closed_at: 2026-05-04
human_gate: none
advances:
  - goc-ship-game-of-cards-as-cross-agent-cli
advanced_by: []
tags: [story, infra]
definition_of_done: |
  - [x] `goc install` in a clean repo creates `.claude/skills/` (11 skills), `deck/` (with placeholder log.md), `.claude/hooks/user-prompt-submit-goc.py` (deviated from `.sh` — Python hook is what Claude Code reads natively, matching the phasor reference)
  - [x] `goc install` appends GoC sections to `CLAUDE.md` (creating it if absent) — sections are bounded by HTML-comment markers so `goc upgrade` can re-sync without clobbering user edits
  - [x] `goc install` registers the `goc validate` equivalent as a pre-commit hook in `.pre-commit-config.yaml` (creating it if absent)
  - [x] `goc install` is idempotent: running twice in the same repo detects existing install and exits with "already installed; run `goc upgrade` to sync templates"
  - [x] `goc upgrade` re-syncs marker-bounded sections in CLAUDE.md, replaces skill files, preserves user-authored cards in `deck/`
  - [x] `goc install --dry-run` prints planned writes without touching the filesystem
  - [x] On a fresh tmpdir: `goc install && goc new round-trip-test && goc done round-trip-test && goc validate` round-trips green
  - [x] CLAUDE.md section authorship: the appended block matches today's GoC sections in this repo (deck-first mode, two-mode runtime, Andon-cord) but is written generically (no phasor-agents-specific references)
---

# `goc install` scaffolds the methodology into a repo

## Why

Sub-card of `goc-ship-game-of-cards-as-cross-agent-cli`. This is the per-repo install flow — the runtime equivalent of `git init` for a methodology framework. Without it, the PyPI package is just a CLI with no on-disk presence in target repos.

Today the same job is done by `Skill(use-game-of-cards)` mode A, which scaffolds *from this repo's working tree*. That implementation is the prior art — it lists exactly the files to create, the hooks to install, the CLAUDE.md sections to append. This card moves that logic into `goc install`, sourcing templates from package data instead of the working tree.

## What

A `goc install` command that, in any target repo, performs:

1. **Detect** whether the repo already has a GoC install (by checking `deck/` directory + `.claude/skills/deck/` markers + a sentinel `.goc-version` file in `deck/`).
2. **Plan writes** — list every file to create, every section to append, every hook to register. With `--dry-run`, exit here.
3. **Extract templates** from package data via `importlib.resources.files("goc.templates")`:
   - `.claude/skills/` ← `templates/skills/` (the 11 skill directories)
   - `.claude/hooks/user-prompt-submit-goc.sh` ← `templates/hooks/user-prompt-submit.sh`
4. **Scaffold deck/** with an empty `log.md` and a `.goc-version` sentinel pinning the schema version.
5. **Append CLAUDE.md sections** — bounded by `<!-- BEGIN GOC -->` / `<!-- END GOC -->` markers so `goc upgrade` can re-sync without clobbering user content. Section content: deck-first mode, two-mode runtime (session + autonomous), Andon-cord, deck workflow.
6. **Register pre-commit hook** in `.pre-commit-config.yaml` (creates the file if missing) — runs `goc validate` against `deck/.*$`.
7. **Print next steps** — "Methodology installed. Try: `goc new my-first-card`. Run `goc upgrade` later to sync template updates."

`goc upgrade` is the sibling command:

- Re-extracts skill templates (with a diff preview, prompts before overwriting if the user has modified skill files).
- Re-syncs marker-bounded CLAUDE.md sections (preserves everything outside markers).
- Migrates `deck/` schema if the new version requires it (calls into engine schema migrations).
- Preserves authored cards untouched.

## How

1. Build `templates/` from the current `.claude/skills/` directories (sub-card 1 packages them as data).
2. Implement `goc install` as a Click command in `goc.install`:
   - Use `importlib.resources.as_file` to materialize template trees onto disk.
   - Use a small templating step for files that need substitution (CLAUDE.md sections that reference the package version).
   - Atomic: write to a temp dir, then `os.replace` into place per file. If anything fails mid-way, abort cleanly.
3. CLAUDE.md marker pattern:

```markdown
<!-- BEGIN GOC v0.1.0 -->
... GoC sections ...
<!-- END GOC -->
```

`goc upgrade` finds this block, replaces it with the new version. Anything outside the markers is the user's; never touched.

4. **Idempotency test**: run `goc install` twice, assert second run exits with "already installed" message and zero filesystem changes.
5. **End-to-end smoke**: in CI, scaffold a fresh tmpdir, `goc install`, `goc new`, `goc done`, `goc validate`, assert all succeed.

## Out of scope

- AGENTS.md output → `goc-write-agentsmd-alongside-claudemd` (separate card; AGENTS.md is a different file with a different convention).
- Per-agent shim templates beyond Claude → `goc-multi-agent-shim-which-agents-at-v1`.
- Bootstrap UX for the missing-`goc` case (i.e., what happens *before* the user runs `goc install`) → `goc-bootstrap-error-when-cli-not-on-path`.
- Migrating phasor-agents off vendored `deck.py` → `goc-migrate-phasor-agents-off-vendored-deckpy`.

## Cross-references

- Parent epic: `goc-ship-game-of-cards-as-cross-agent-cli`
- Prior art (in-repo installer): `Skill(use-game-of-cards)` mode A
- CLAUDE.md sections to template from: this repo's CLAUDE.md, "Game of Cards is the Runtime" + "Deck Workflow" + "Tests vs Verification" (the latter is phasor-specific — strip it).
- Hook script source: `.claude/hooks/` in this repo (whatever the `UserPromptSubmit` hook currently runs)
