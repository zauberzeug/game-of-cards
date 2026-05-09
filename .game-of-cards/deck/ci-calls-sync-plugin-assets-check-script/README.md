---
title: ci-calls-sync-plugin-assets-check-script
summary: "The CI step that detects drift between `goc/templates/` and `claude-plugin/` should call `python scripts/sync_plugin_assets.py --check` directly, instead of duplicating that script's logic in an inline 35-line `filecmp` block in `.github/workflows/ci.yml`. Today the inline block exists because the bot that introduced the script (commit `d9a5a02`) hit a GitHub-App `workflows`-permission wall when pushing the workflow change and partially-reverted itself in `6794c03`, leaving the duplication in place. The closed parent card `generate-plugin-payloads-from-templates-on-release` ticked its 'Generation step runs in CI' DoD bullet despite this revert, so this card finishes what that closure claimed."
status: done
stage: null
contribution: low
created: 2026-05-09
closed_at: 2026-05-09
human_gate: none
advances:
  - generate-plugin-payloads-from-templates-on-release
advanced_by: []
tags: [bug, infra, meta-fix]
definition_of_done: |
  - [x] `.github/workflows/ci.yml` contains a single `Verify plugin assets` step that runs `python scripts/sync_plugin_assets.py --check` (no inline filecmp block)
  - [x] CLAUDE.md's claim that "CI runs `python scripts/sync_plugin_assets.py --check`" is once again accurate (no edits required if the workflow lands)
  - [x] `uv run goc validate` passes
worker: {who: rodja, where: main}
---

# ci-calls-sync-plugin-assets-check-script

## Why now

`d9a5a02` introduced `scripts/sync_plugin_assets.py` and rewrote the
workflow step to call `python scripts/sync_plugin_assets.py --check`.
The follow-up commit `6794c03` reverted just the workflow file
("ci: revert workflow change (app lacks workflows permission)") because
the GitHub App identity pushing the change lacked the `workflows` scope.

The script and pre-commit hook stayed; the workflow stayed inline.
Functionally the two implementations agree today, but they are now two
copies of the same drift-detection logic that can diverge in:

- which (src, dst) pairs they cover,
- error message wording,
- exit semantics,

…exactly the duplication the script existed to eliminate. CLAUDE.md
already documents the intended behavior; reverting the inline block to
the script call makes documentation true.

## Scope

Single-file edit. Replace the `Verify plugin assets match templates
byte-for-byte` step (lines ~81–118 of `.github/workflows/ci.yml`) with
the two-line invocation that `d9a5a02` originally introduced. Keep the
existing step name aligned with reality (`goc/` is the source of truth,
not just `goc/templates/`):

```yaml
      - name: Verify plugin assets match goc/ byte-for-byte
        run: python scripts/sync_plugin_assets.py --check
```

The script invokes `filecmp` over the same pair list the inline block
walks today, so behavior is unchanged on a clean tree. CI also runs
`uv sync` earlier in the job, so `python` resolves inside the project's
venv with no additional setup.

## Out of scope

- Granting the `claude[bot]` App `workflows: write` permission. That is
  a separate policy decision (see commit message of `6794c03`); this
  card just lands the missing diff manually.
- Reopening or rewriting the closed `generate-plugin-payloads-from-templates-on-release`
  card. This card supersedes the unmet DoD bullet via the `advances` link.
