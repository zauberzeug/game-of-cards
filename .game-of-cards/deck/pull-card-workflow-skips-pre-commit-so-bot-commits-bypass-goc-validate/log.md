## 2026-05-30T09:14:00Z — Autonomous attempt: tag-fix landed, workflow-edit blocked by App permission

The `pull-card.yml`-triggered bot pulled this card, implemented BOTH halves
locally, and ran the full closure flow (DoD ticked, log.md closure entry,
`goc attest` clean, `goc done` accepted). The commit landed on the bot's
local `main` successfully. The push to `origin/main` was then rejected:

```
! [remote rejected] main -> main (refusing to allow a GitHub App to create or
update workflow `.github/workflows/pull-card.yml` without `workflows` permission)
```

The bot reset to `origin/main`, re-applied only the deck-side fix (the
`verified`-tag drop on the
`deck-session-start-hook-strips-quotes-asymmetrically-across-frontmatter-readers`
card), raised this card's `human_gate` to `decision`, and parked.

State on disk after this entry:

- `tags: [bug, verified, infra]` → `tags: [bug, infra]` on the
  deck-session-start card. `uv run goc validate` is now clean.
- `.github/workflows/pull-card.yml` is unchanged at `origin/main`. The
  intended `Install pre-commit hooks` step still needs to land via a human
  commit (see `## Decision required` in the README).

Verification snapshot before the push obstacle surfaced (with the workflow
edit in place locally): `reproduce.py` exited 0 (both assertions PASS),
`uv run goc validate` clean, `scripts/sync_plugin_assets.py --check` clean.
So the proposed fix IS correct on the merits — the only failure was the
push-permission boundary.

This is a new piece of evidence about the autonomous loop's reach: the bot
cannot self-modify any file under `.github/workflows/`. Worth considering
when scoping future cards. The README's `## Decision required` section
captures the human's options.
