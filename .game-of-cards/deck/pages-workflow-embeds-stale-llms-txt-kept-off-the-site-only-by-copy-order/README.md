---
title: pages-workflow-embeds-stale-llms-txt-kept-off-the-site-only-by-copy-order
summary: "`.github/workflows/pages.yml` synthesizes `/llms.txt` from an embedded heredoc that is several revisions stale (legacy `deck/` paths, a two-step install recipe whose second step no-ops with 'already installed', and a `goc status` smoke test that is actually a usage error). The deployed site is correct today only because the later verbatim `site/` copy overwrites `_pages/llms.txt` with `site/llms.txt`. Two divergent sources of truth for the one file aimed at LLM ingestion; any rename of `site/llms.txt` or reorder of the workflow silently resurfaces the broken recipe."
status: open
stage: null
contribution: medium
created: "2026-07-23T01:11:06Z"
closed_at: null
human_gate: session
advances: []
advanced_by: []
tags: [documentation, infra]
definition_of_done: |
  - [ ] MECHANICAL: `pages.yml` stops synthesizing `llms.txt` from the embedded heredoc — `site/llms.txt` becomes the single source of truth (delete the heredoc write, or replace it with a read of `site/llms.txt`) — requires a HUMAN commit (the bot's GITHUB_TOKEN cannot modify `.github/workflows/`)
  - [ ] TDD: `reproduce.py` exits zero — no second `llms.txt` body embedded in `pages.yml`
  - [ ] EMPIRICAL: after the next Pages deploy, game-of-cards.com/llms.txt still serves the `site/llms.txt` content (spot-check one marker line); verdict recorded in log.md
  - [ ] PROCESS: `uv run goc validate` passes
---

# pages.yml embeds a stale llms.txt that only copy order keeps off the site

## Location

`.github/workflows/pages.yml:146-195` — the
`(out / "llms.txt").write_text("""# Game of Cards ...""")` heredoc —
masked by the later verbatim copy at lines ~218-228:

```python
if Path("site").is_dir():
    for src in Path("site").rglob("*"):
        if src.is_file():
            dst = out / src.relative_to("site")
            ...
            shutil.copy(src, dst)
```

which overwrites `_pages/llms.txt` with `site/llms.txt`.

## What's broken

The heredoc is several revisions stale. Verified against current `goc`
behavior (0.0.27):

1. **Legacy deck path, three times.** The heredoc claims `goc install`
   "creates `deck/`" and "Cards are markdown directories under
   `deck/`". The canonical location has been `.game-of-cards/deck/`
   since 0.0.4; `site/llms.txt` says so.
2. **Un-followable install recipe.** Steps 2–3 tell the reader to run
   `goc install` and then `goc install --agents claude`. The second
   invocation does not add agent files — it prints
   `already installed (.game-of-cards/deck/.goc-version → 0.0.27)` and
   exits without doing what the recipe promises (verified in a scratch
   repo).
3. **Broken smoke test.** Step 4 says "`goc status` prints an empty
   deck". Bare `goc status` is a usage error:
   `goc status: error: the following arguments are required: title, new_status`.
4. **Superseded framing.** The Claude Code plugin is presented as a
   "Lean alternative"; the shipped `site/llms.txt` leads with the
   plugin as the primary install path (per the closed
   `lead-llms-txt-with-claude-code-plugin`).

Every llms.txt improvement card (`lead-llms-txt-with-claude-code-plugin`,
`add-openclaw-install-section-to-llms-txt`,
`llms-txt-still-recommends-uv-tool-install-as-preferred`) edited only
`site/llms.txt` — the workflow's embedded duplicate was never touched.
The deployed file is correct **only by copy order**: the heredoc writes
first, the `site/` walk overwrites second. Renaming `site/llms.txt`,
moving the synthesis step later, or restricting the copy loop silently
resurfaces the stale recipe at `game-of-cards.com/llms.txt` — the one
URL explicitly aimed at LLM ingestion, where a broken install recipe
does maximal damage.

## Empirical evidence

`reproduce.py` scans `pages.yml` for the embedded llms.txt body and
confirms both the stale markers and the divergence from
`site/llms.txt` (output verbatim):

```
[FAIL] pages.yml embeds its own llms.txt body (heredoc write found)
       stale marker present: 'creates `deck/`'
       stale marker present: 'goc install --agents claude'
       stale marker present: '`goc status` prints an empty deck'
       embedded body differs from site/llms.txt (site copy wins today only by copy order)
```

It exits non-zero today and zero once `pages.yml` no longer embeds a
second body.

## Fix

Delete the heredoc write in `pages.yml` (or replace it with
`(out / "llms.txt").write_text(Path("site/llms.txt").read_text())` if
an explicit write is preferred over relying on the `site/` walk).
`site/llms.txt` already exists and is the maintained copy, so the
minimal fix is pure deletion.

**Why the session gate:** the fix is a `.github/workflows/` edit, which
the autonomous bot cannot push (no `workflows` permission — rejection
documented on
[pull-card-workflow-skips-pre-commit-so-bot-commits-bypass-goc-validate](../pull-card-workflow-skips-pre-commit-so-bot-commits-bypass-goc-validate/)).
A human session must apply it.
