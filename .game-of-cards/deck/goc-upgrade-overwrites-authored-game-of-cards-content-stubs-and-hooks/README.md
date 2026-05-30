---
title: goc-upgrade-overwrites-authored-game-of-cards-content-stubs-and-hooks
summary: "`goc upgrade` blind-copies the bundled `templates/game_of_cards/` tree over a consuming repo's `.game-of-cards/` project state, silently destroying authored content in the 12 content stubs + `hooks/*.md` and in `README.md`. Only `config.yaml` is spared (a one-file `skip_existing` carve-out). Fix in two layers: make the engine non-destructive and ownership-aware (preserve diverged files, scaffold only absent ones, emit a divergence report), and add a dedicated `upgrade` skill that does LLM-driven integration of evolving content (README, config) while confirming preservation of user-owned stubs. AGENTS.md/CLAUDE.md marker-merge already does the right thing and stays unchanged."
status: open
stage: null
contribution: high
created: "2026-05-30T12:47:43Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero today; after the fix it exits non-zero (authored `canonical-tags.md` and `hooks/create-card.md` content survive a real cross-version `goc upgrade`)
  - [ ] TDD: regression test — a repo that authored content into every one of the 12 user-owned stubs/hooks keeps all of it across `goc upgrade`; an absent stub is still scaffolded (new-in-version files appear); an untouched (pristine/comment-only) stub may be refreshed
  - [ ] MECHANICAL: engine upgrade path no longer blind-copies user-owned `.game-of-cards/` files. Per file: absent → scaffold; byte-identical to shipped template → no-op; diverged → preserve, do NOT overwrite. `_sync_game_of_cards_config`'s `skip_existing={config.yaml}` carve-out is generalized to the whole user-owned surface
  - [ ] MECHANICAL: the engine emits a machine-readable divergence report (which `.game-of-cards/` files diverged from stock, and the shipped template content for the evolving ones) that the `upgrade` skill can consume; safety does not depend on an agent being present (headless/CI runs preserve content with no prompt)
  - [ ] MECHANICAL: dry-run plan accuracy — `_plan_upgrade_writes` / `_print_plan` label each `.game-of-cards/` file `create` / `unchanged` / `preserved (diverged)` instead of the misleading blanket `sync`; `config.yaml` is no longer reported as a write when it is in fact preserved
  - [ ] PROCESS: new dedicated `upgrade` skill under `goc/templates/skills/upgrade/` (host-agnostic; auto-synced to the plugin mirrors like every other skill). It runs the engine upgrade, reads the divergence report, and for the evolving-content files (`README.md`, `config.yaml`) does a 2-way LLM reconcile of upstream changes into the local copy, asking the user when ambiguous; for user-owned stub divergences it confirms "kept yours, nothing upstream"; for the AGENTS.md/CLAUDE.md GoC block it summarizes what methodology guidance changed (informational, not a merge)
  - [ ] MECHANICAL: AGENTS.md / CLAUDE.md marker-merge (`_append_marker_block`, `_sync_methodology_blocks`) is unchanged — verified the existing marker/strip regression tests still pass (do not regress the bugs closed by the `append-marker-block-*` / `strip-goc-block-*` family)
  - [ ] PROCESS: `.game-of-cards/README.md` (the shipped hook-point catalogue) gets a documented ownership rule — it is goc-owned reference docs but flagged "customizable per repo", so the `upgrade` skill reconciles it rather than the engine clobbering it
  - [ ] MECHANICAL: CLAUDE.md / AGENTS.md guidance updated — document the per-file ownership model (regenerate goc-owned, preserve user-owned, reconcile evolving) and the new `upgrade` skill
  - [ ] PROCESS: `uv run goc validate` passes; full `unittest` suite passes; `python scripts/sync_plugin_assets.py --check` and the OpenClaw porter `--check` stay green (new skill mirrors regenerated)
---

# `goc upgrade` overwrites authored `.game-of-cards/` content stubs and hooks

`goc upgrade` re-runs the same template copy that `goc install` uses,
and that copy blindly overwrites a consuming repo's **project-state**
files — the per-repo content stubs and workflow hooks under
`.game-of-cards/` that the shipped README explicitly tells consumers to
author. A downstream repo that customized its tag vocabulary, domain
glossary, file-path map, or per-skill workflow hooks loses all of it on
the next `goc upgrade`, with no prompt and no backup.

## Location

- `goc/install.py:790` — `_sync_game_of_cards_config()` → calls
  `_copy_tree(templates / "game_of_cards", config_dst, skip_existing=…)`.
- `goc/install.py:775` — `_copy_tree()` overwrites every walked file
  unless its relative path is in `skip_existing` **and** already exists.
- `goc/install.py:799` — the carve-out is exactly one file:
  ```python
  skip_existing = {Path("config.yaml")} if migrate_legacy else set()
  ```
- `goc/install.py:1401` — `upgrade()` calls
  `_sync_game_of_cards_config(target, templates, migrate_legacy=True)`,
  so on upgrade only `config.yaml` is spared; the other 13 files are
  re-copied from stock.

## What's broken

The bundled `goc/templates/game_of_cards/` tree has 14 files. On
`goc upgrade` they fall into three behaviors, only one of which is
correct:

| Files | Count | Ships as | Upgrade behavior | Correct? |
|---|---|---|---|---|
| content stubs (`canonical-tags.md`, `domain-vocabulary.md`, `domain-examples.md`, `file-path-map.md`, `tooling-conventions.md`, `documentation-conventions.md`) + `hooks/*.md` × 6 | 12 | **comment-only stub** (7 lines, blank by design) | **blind overwrite** | ❌ destroys authored content |
| `README.md` | 1 | real, evolving docs (hook-point catalogue) | **blind overwrite** | ❌ destroys local edits |
| `config.yaml` | 1 | real, structured config | preserve if present | ⚠️ safe, but never receives new keys |

The 12 stubs ship **permanently blank** — they contain only an HTML
comment explaining what the consumer should author:

```
<!-- .game-of-cards/canonical-tags.md
     Project-local content stub injected into goc-shipped skill bodies via
     `!`cat .game-of-cards/canonical-tags.md`` at documented insertion points.
     Author the content the skills should see. ... -->
```

So on upgrade there is **no upstream content to bring** for these
files — the only correct behavior is "never overwrite authored content;
scaffold only if absent." The blind copy instead replaces the
consumer's authored file with the empty stub.

Note the other agent's report was partly wrong: **`config.yaml` is
NOT overwritten** — it is the single file already protected by
`skip_existing`. The casualties are the stubs, the hooks, and the
README.

### Secondary defect — the dry-run plan lies

`_plan_upgrade_writes` (`goc/install.py:729`) maps every planned
`write` to the label `sync`, including `config.yaml` — which the real
run preserves. So `goc upgrade --dry-run` reports `config.yaml` under
"sync" (it isn't touched) and labels the genuinely-clobbered stubs with
the same undifferentiated `sync` verb. A dry run cannot currently tell
you which files are create-only, which overwrite, and which are
preserved.

## Empirical evidence

`reproduce.py` installs into a fresh temp repo, authors real content
into a content stub and a workflow hook, pins an older `.goc-version`
(so upgrade does real work rather than the same-version no-op
short-circuit), then runs `goc upgrade`:

```
authored content stub  (canonical-tags.md): LOST
authored workflow hook (create-card.md): LOST

--- .game-of-cards/canonical-tags.md after upgrade (first 6 lines) ---
<!-- .game-of-cards/canonical-tags.md
     Project-local content stub injected into goc-shipped skill bodies via
     `!`cat .game-of-cards/canonical-tags.md`` at documented insertion points.

     Author the content the skills should see. If this file is empty, the
     skills proceed with their generic flow. See the goc README for the

DEFECT REPRODUCED: goc upgrade overwrote authored project-state.
```

## Why it matters

This is silent data loss for every downstream consumer who follows the
README's instruction to author project state. `goc upgrade` is the
documented, encouraged way to receive template updates — so the bug
fires precisely when a careful consumer does the right thing twice
(customize, then upgrade). Reachability is unambiguous: any consumer on
an older `goc` version who runs `goc upgrade` hits
`_sync_game_of_cards_config(migrate_legacy=True)` →
`_copy_tree(skip_existing={config.yaml})`, which re-copies the 13
unprotected stock files over whatever the consumer authored.

Related but distinct: the closed card
[goc-upgrade-clobbers-non-goc-skills-and-validate-fails-in-plugin-mode](../goc-upgrade-clobbers-non-goc-skills-and-validate-fails-in-plugin-mode/)
fixed an analogous destructive-upgrade bug on a *different* tree
(`.claude/skills/`). Same family (upgrade treating user-owned content as
goc-owned scaffold), different surface.

## AGENTS.md / CLAUDE.md are the reference pattern (not broken)

`AGENTS.md`, `CLAUDE.md`, and `CLAUDE.local.md` are handled by a
**completely different** mechanism — the marker-bounded merge
(`_append_marker_block` at `goc/install.py:922`, driven by
`_sync_methodology_blocks` at `:957`). It regenerates only the content
between `<!-- BEGIN GOC vX.Y.Z -->` and `<!-- END GOC -->` from
`templates/AGENTS_GOC.md`; everything outside the markers is preserved.
This surface is **not** subject to the data-loss bug — the GoC block is
explicitly goc-owned territory, regenerated on purpose so consumers
receive methodology updates. The only by-design caveat is that edits
*inside* the markers are replaced (the contract is "don't edit there").

This is exactly the pattern the rest of the fix should imitate, and the
deck shows it is delicate: the `append-marker-block-*` and
`strip-goc-block-*` family (8+ closed cards) hardened this merge over
time. **The marker-merge must be left unchanged — align to it, do not
"unify" it into something that re-opens those bugs.**

## Decision (resolved in conversation)

The unifying principle across all goc-managed content on upgrade is
**explicit ownership**:

- **goc-owned region** → regenerate wholesale (AGENTS.md/CLAUDE.md GoC
  marker block — already done, keep as-is).
- **user-owned** → never clobber (the 12 stubs + hooks).
- **shared / evolving** → reconcile upstream changes into the local
  copy (README, config).

The fix is **two layers**:

1. **Engine — deterministic safety.** `goc upgrade` stops blind-copying
   user-owned `.game-of-cards/` files. Per file: absent → scaffold;
   identical to shipped template → no-op; diverged → **preserve** and
   record in a divergence report. This guarantees no data loss even
   when no agent is in the loop (CI's `goc validate` gate, the
   `--keep-local-skills` scripted path, cron). The dry-run plan is
   fixed in the same pass to label `create` / `unchanged` /
   `preserved (diverged)`.

2. **Skill — LLM integration.** A new dedicated `upgrade` skill
   (decided: yes, a standalone skill, not folded into kickoff) reads
   the engine's divergence report and:
   - for evolving-content files (README, config) → **2-way LLM
     reconcile** of upstream changes into the local copy, asking the
     user when ambiguous (decided: 2-way to start — the engine does not
     yet retain old-version templates for a true 3-way base; 3-way is a
     possible follow-up if 2-way proves too fuzzy);
   - for user-owned stub divergences → confirm "kept yours, nothing
     upstream";
   - for the AGENTS.md/CLAUDE.md GoC block → summarize what methodology
     guidance changed (informational; that region is goc-owned, not
     merged).

## Fix

See the Decision section above for the locked design; the DoD
enumerates the concrete deliverables. Key implementation notes:

- Generalize `skip_existing` in `_sync_game_of_cards_config` from
  `{config.yaml}` to the full user-owned set, OR (cleaner) split the
  copy into "scaffold-if-absent" vs "diverged → report, don't write".
- The divergence report wants to be consumable by the skill — e.g. a
  `--report-divergence` / structured stdout mode on `goc upgrade`, or a
  small machine-readable section the skill parses.
- New skill lives at `goc/templates/skills/upgrade/SKILL.md`
  (source-of-truth); the pre-commit `sync-plugin-assets` hook mirrors it
  into `claude-plugin/`, `codex-plugin/`, `.claude/`, `.codex/`, and the
  OpenClaw porter ports it — all enforced by existing parity tripwires.
- "Pristine" detection for refresh-if-untouched: a stub whose content is
  empty or only the HTML scaffolding comment is safe to refresh; the
  skills already treat comment-only stubs as "no content, fall through".
