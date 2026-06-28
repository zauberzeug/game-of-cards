---
title: pull-card-workflow-skips-pre-commit-so-bot-commits-bypass-goc-validate
summary: "`.github/workflows/pull-card.yml` drains the autonomous queue by invoking `claude-code-action`, which commits via plain `git commit` — but the workflow never runs `pre-commit install`, so the `goc-validate` and `sync-plugin-assets` hooks declared in `.pre-commit-config.yaml` never fire on the bot's closure commits. Combined with `ci-skips-deck-validation-after-deck-moved-to-game-of-cards-directory` (CI also doesn't run `goc validate`), invalid frontmatter has no safety net when the bot commits. Demonstrated: closure commit 1ec1986 (`deck-session-start-hook-strips-quotes-asymmetrically-across-frontmatter-readers`) landed `tags: [bug, verified, infra]` — `verified` is not in `goc/schema.yaml` canonical_tags, and `uv run goc validate` errors on the card today."
status: open
stage: null
contribution: medium
created: "2026-05-30T09:09:34Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [ ] EMPIRICAL: `deck/<title>/reproduce.py` exits non-zero today (confirms `pull-card.yml` has no `pre-commit install`/run step and that an invalid-tag card exists in history) and exits zero after the fix (the workflow gains a pre-commit gate before the agent commits).
  - [ ] MECHANICAL: `.github/workflows/pull-card.yml` runs `pre-commit` before the bot pushes — either install the git hook (`uv run pre-commit install`) before the `Pull one card` step, or add an explicit `uv run pre-commit run --files <staged>` / `uv run goc validate` step after the agent step that fails the job on drift.
  - [x] MECHANICAL: Fix the latent invalid tag in `.game-of-cards/deck/deck-session-start-hook-strips-quotes-asymmetrically-across-frontmatter-readers/README.md`: change `tags: [bug, verified, infra]` to either `[bug, infra]` (drop the unverified flag once verified — the canonical convention) or add a project-local `verified` tag in `.game-of-cards/canonical-tags.md`. The closure commit message already states the defect was empirically verified, so simple removal is the natural read.
  - [ ] PROCESS: `uv run goc validate` exits 0 on the repo deck after both fixes land. Plugin mirrors stay in sync (`python scripts/sync_plugin_assets.py --check` clean).
---

# `pull-card.yml` bypasses pre-commit hooks, letting the bot land frontmatter
that `.pre-commit-config.yaml` would have rejected

## Decision required (2026-05-30)

The autonomous bot attempted to land the fix and discovered a second-order
obstacle: the GitHub App that runs `pull-card.yml` cannot push commits that
modify files under `.github/workflows/`. GitHub rejected the push with:

```
! [remote rejected] main -> main (refusing to allow a GitHub App to create or
update workflow `.github/workflows/pull-card.yml` without `workflows` permission)
```

This means **the bot cannot fix its own workflow**. The tag-drop half of this
card (the only piece the bot could push) has been applied; the workflow-edit
half waits for a human commit.

The human needs to either:

1. **Just push the one-line workflow change manually.** Apply the proposed
   `Install pre-commit hooks` step under `Prepare Python environment` (see
   "Fix proposal" below) and push from a local checkout. Then re-claim the
   card (status remains `open`, gate stays `decision` until this is decided)
   and close it on the next pull.
2. **Provision a PAT with `workflow` permission** for the bot and rewire
   `pull-card.yml` to use it for the push step. This unblocks future
   workflow-self-edits but adds a long-lived secret to the repo — a real
   trust trade-off worth deciding on its own. If chosen, file as a separate
   card (this card stays scoped to the pre-commit gate itself).

Recommendation: option (1) for this card, and consider whether option (2)
warrants its own follow-up card. The bot pulled the Andon cord rather than
silently leaving the workflow file changed-but-unpushed in working tree.

## Location

- `.github/workflows/pull-card.yml` — the autonomous drain workflow.
  The relevant steps:
  ```yaml
  - name: Prepare Python environment
    run: uv sync

  - name: Pull one card
    if: steps.queue.outputs.count != '0'
    uses: anthropics/claude-code-action@v1
    with:
      ...
      prompt: |
        ...
        Follow CLAUDE.md and AGENTS.md. Commit and push the files
        for the card you close or park before exiting.
  ```
  There is no `pre-commit install` step and no post-agent
  `pre-commit run` / `goc validate` gate.

- `.pre-commit-config.yaml` — declares the local gates:
  ```yaml
  - id: sync-plugin-assets
    entry: uv run python scripts/sync_plugin_assets.py
    files: ^goc/
  - id: goc-validate
    entry: uv run goc validate
    files: ^(\.game-of-cards/deck/|goc/|claude-plugin/).*$
  ```

- `AGENTS.md` (lines 22-31, "Common commands") documents
  `pre-commit run --all-files` as the project's local gate that "syncs
  plugin assets + goc validate."

## What's broken

The autonomous drain workflow (cron-fired every hour, plus
`workflow_dispatch`) sets up the venv with `uv sync` and then hands
control to `claude-code-action@v1`. The action's agent commits via
plain `git commit`. Git only invokes `.git/hooks/pre-commit` when that
hook script exists on disk; the script is written by
`uv run pre-commit install`. The workflow never runs that. So:

1. The bot's `git commit` skips the `goc-validate` hook.
2. The bot's `git commit` skips the `sync-plugin-assets` hook.
3. CI on the resulting push would catch only the
   `sync_plugin_assets.py --check` divergence (job
   "Verify plugin assets match goc/ byte-for-byte" in
   `.github/workflows/ci.yml`). `goc validate` is NOT run by CI
   either, because the validate step guards on the wrong path —
   see [ci-skips-deck-validation-after-deck-moved-to-game-of-cards-directory](../ci-skips-deck-validation-after-deck-moved-to-game-of-cards-directory/).

The result is a complete frontmatter-drift gap on the autonomous
path. Pre-commit catches it locally for humans; CI doesn't catch it
for the bot.

## Empirical evidence

`uv run goc validate` today emits:

```
ERROR: deck-session-start-hook-strips-quotes-asymmetrically-across-frontmatter-readers: tags: unknown tag 'verified' — add a project-local tag in .game-of-cards/canonical-tags.md (under a `canonical_tags:` YAML block, merged by `goc validate`); for a tag that should ship with goc, open a PR against the goc repo
```

The offending card's frontmatter:

```yaml
tags: [bug, verified, infra]
```

`verified` is not a canonical tag (`goc/schema.yaml` line 28-39
lists: bug, documentation, test, api-contract, meta-fix, infra,
unverified, epic, story). It is not defined in
`.game-of-cards/canonical-tags.md` either (that file is the stub).

The card was closed by `claude[bot]` in commit `1ec1986`:

```
$ git show 1ec1986 -- .game-of-cards/deck/deck-session-start-hook-strips-quotes-asymmetrically-across-frontmatter-readers/README.md | grep -E "^[+-]tags"
-tags: [bug, unverified, infra]
+tags: [bug, verified, infra]
```

The closure commit body claims `uv run goc validate: OK`, but the
diff demonstrably ships the invalid tag. The discrepancy is consistent
with the validate having been run *before* the manual tag flip from
`unverified` → `verified`, with no subsequent gate firing on the
final tree. That gate is exactly what a wired-up `pre-commit run` on
the bot's commit path would have provided.

## Why it matters

The autonomous loop is supposed to be safe by construction: the bot
pulls a card, implements it, runs DoD, closes, commits — and the
infrastructure validates what it ships. `.pre-commit-config.yaml` is
the documented contract for what validates a commit; `AGENTS.md`
"Common commands" advertises `pre-commit run --all-files` as the
synchronization gate. When the autonomous worker bypasses that
contract, every bot commit becomes a trust-the-LLM-to-self-validate
event. The deck-session-start card is one demonstrated slip; the
gap is structural and accumulates silently — every new tag drift,
every list-field that becomes a non-list, every renamed status
value will land unchecked on autonomous closures until a human
notices.

Reachability: every cron-fired `pull-card.yml` run (hourly), every
manual `workflow_dispatch`, every self-triggered follow-up run
exercises this path. The bot commits hundreds of times per month
based on the recent log.

## Fix proposal

Pick one (both are mechanical):

**(A) Install the git hook so plain `git commit` triggers it.** Add
after `Prepare Python environment`:

```yaml
- name: Install pre-commit hooks
  run: uv run pre-commit install
```

This matches what a human contributor does. The bot's `git commit`
then runs `goc-validate` + `sync-plugin-assets` automatically.

**(B) Run pre-commit explicitly after the agent step.** Less
invasive but post-hoc — the agent could have pushed if the step
fired only on commit. Better as a belt-and-suspenders on top of (A):

```yaml
- name: Verify pre-commit gates pass on bot's commit
  if: steps.queue.outputs.count != '0'
  run: uv run pre-commit run --from-ref HEAD~1 --to-ref HEAD
```

Recommend (A) as the canonical fix; it matches the documented gate
mechanism and runs *before* push, so the bot cannot push a commit
that would fail the gate.

Separately, fix the latent invalid tag on the
`deck-session-start-hook-strips-quotes-asymmetrically-across-frontmatter-readers`
card (drop `verified` — the convention is to remove the `unverified`
tag once verified, not flip it to a non-canonical opposite).

## Related

- [ci-skips-deck-validation-after-deck-moved-to-game-of-cards-directory](../ci-skips-deck-validation-after-deck-moved-to-game-of-cards-directory/) — the CI half of the missing safety net. Fixing only this card still leaves CI silent on drift; both are needed.
