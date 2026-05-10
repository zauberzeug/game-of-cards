---
title: kickoff-and-install-handle-non-git-directories
summary: "Running `goc install` (and the `kickoff` skill on top of it) in a directory without a `.git/` produces dead-weight artifacts and offers no notice to the user. `_append_precommit_hook` writes `.pre-commit-config.yaml` unconditionally even when no git repo is present, leaving a config no hook can act on. The `kickoff` skill never checks for git either, so the methodology — which assumes git for auto_commit, claim records, and history — silently runs half-armed. Fix: skip the pre-commit write when `.git/` is absent, and have `kickoff` flag the absence to the user (one-line notice, no education) so they can decide whether to `git init` before continuing."
status: active
stage: null
contribution: medium
created: 2026-05-10
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [ ] `_append_precommit_hook` in `goc/install.py` skips writing `.pre-commit-config.yaml` when `(target / ".git").is_dir()` is false; existing file in a non-git dir is left alone (do not delete user content)
  - [ ] `kickoff` skill (in `goc/templates/skills/kickoff/SKILL.md`) checks for `.git/` early; if absent, surfaces a one-line notice ("no git repository here — version control is not set up; run `git init` if you want the deck tracked") and continues
  - [ ] Notice text is factual, not educational — does NOT explain what git is, why GoC needs it, or recommend a specific workflow
  - [ ] Verified: `goc install` in a fresh non-git tmpdir does NOT create `.pre-commit-config.yaml`; `.game-of-cards/`, `AGENTS.md`, `CLAUDE.md`, and the marker block still land normally
  - [ ] Verified: `kickoff` in a fresh non-git tmpdir prints the notice once before scaffolding, then proceeds
  - [ ] Both Claude-plugin and pipx-installed engine paths re-synced via `pre-commit run sync-plugin-assets --all-files`
worker: {who: "claude[bot]", where: main}
---

# Kickoff and install handle non-git directories

## Why

Test reproduced in `/tmp/goc-usage` (2026-05-10): kickoff on an empty
non-git dir produced a `.pre-commit-config.yaml` referencing `goc validate`
that pre-commit can never run (no `.git/hooks/` to install into). The
config is dead weight until the user runs `git init`, at which point the
pre-commit hook becomes useful — but nothing in the install path tells the
user this gap exists.

The deeper issue: GoC's documented workflow assumes git. `auto_commit:
true` (default in `config.yaml`) is a no-op without a repo; the README in
`.game-of-cards/` says "Versioned in git, kept in the repo root"; claim
commits and closure logs are designed to be traceable in git history. The
methodology is half-armed without it, and kickoff offers no signal that
this is the case.

The fix is two surgical changes, not a redesign of the install flow.

## What

**1. `_append_precommit_hook` (goc/install.py:705) becomes git-aware.**

```python
def _append_precommit_hook(target: Path) -> None:
    """Append the `goc validate` hook to `.pre-commit-config.yaml` (creating it)."""

    if not (target.parent / ".git").is_dir():
        return  # No git repo here — pre-commit config would be dead weight.
    # ...existing logic...
```

The `target` passed in is `target / ".pre-commit-config.yaml"`, so the git
check runs on the parent. The function is only called from one site
(`_run_install` line ~865) so the guard lives in the function itself.

If a `.pre-commit-config.yaml` already exists in a non-git dir (e.g. user
ran `goc install` then `git init` later, or the user is templating GoC
into an existing non-git project), we leave it alone — do not delete.

**2. `kickoff` skill checks for `.git/` early and surfaces a one-line
notice when absent.**

The `kickoff` skill currently runs through:
1. Introduce GoC.
2. Persona question.
3. Merge prompt for AGENTS.md.
4. `goc install`.
5. Hand off to `claude-kickoff`.

Insert between (1) and (2) — or fold into (1) — a git presence check. If
absent, print:

> No git repository here — version control is not set up. The deck assumes
> git (auto_commit, claim history, closure logs); run `git init` if you
> want the deck tracked.

Then continue. **Do not educate.** No explanation of what git does, why
GoC uses it, or how to fix it beyond the `git init` mention. Per Rodja's
explicit feedback (2026-05-10): factual notice, not a tutorial.

## How

`goc/install.py:_append_precommit_hook` — three-line guard, low risk.

`goc/templates/skills/kickoff/SKILL.md` — insert the git check as a
single bash one-liner the skill runs:

```bash
[ -d .git ] || echo "No git repository here — version control is not set up. The deck assumes git (auto_commit, claim history, closure logs); run \`git init\` if you want the deck tracked."
```

The skill body wraps that in its existing instruction prose so the agent
prints the notice once at the right moment. No new dialog turns; the user
isn't asked anything (they can `git init` whenever they want).

## Cross-references

- Reproduced via `/tmp/goc-usage` kickoff session 2026-05-10.
- Touches the same install flow as `write-agentsmd-alongside-claudemd`
  but is independent of that card's marker-block redesign.
- Not blocked by `kickoff-asks-where-goc-briefing-lives` (sibling card
  filed in the same session) — both are scoped to `kickoff` skill edits
  but in different code paths.

## Out of scope

- Auto-running `git init` for the user. The notice is informational; the
  user decides.
- Redesigning `auto_commit` to fail loud in non-git mode. That's a
  separate concern; today it silently no-ops, which is acceptable.
- Educating the user on git itself. Per feedback: notice is factual.
