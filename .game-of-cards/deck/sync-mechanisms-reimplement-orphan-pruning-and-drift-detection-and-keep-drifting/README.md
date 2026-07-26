---
title: sync-mechanisms-reimplement-orphan-pruning-and-drift-detection-and-keep-drifting
status: open
stage: null
contribution: medium
created: "2026-06-19T05:40:14Z"
closed_at: null
human_gate: decision
advances: []
advanced_by:
  - sync-plugin-assets-leaves-orphaned-hook-files-and-check-passes
  - sync-plugin-assets-leaves-orphaned-empty-skill-dirs-and-check-passes
  - openclaw-skill-porter-never-prunes-orphaned-ported-skills
  - openclaw-skill-porter-leaves-empty-orphan-subdir-when-nested-sibling-removed
  - openclaw-porter-orphan-check-misses-asset-only-skill-dirs
tags: [meta-fix, infra, api-contract]
summary: "scripts/sync_plugin_assets.py and scripts/port_skills_to_openclaw.py each reimplement, independently, the same two-part contract: prune dst-only orphans (files, empty dirs, whole dirs) and a drift `--check` that must flag any orphan the prune should have removed. Every new orphan class has had to be patched separately in each mechanism, and the drift checks have a recurring `rglob` blind spot (directories skipped). Four instance cards already document this; the recurring shape is the meta-fix. Decide whether to extract a shared orphan-prune/drift-detect helper or to bind the mechanisms with a shared test contract."
definition_of_done: |
  - [ ] PROCESS: maintainer picks an approach (A shared helper / B shared test contract / C won't-fix); decision + rationale recorded via `goc decide` and in log.md.
  - [ ] TDD: if A or B — a single shared regression contract asserts, for every sync mechanism, that a removed source file / empty dir / whole dir leaves no dst orphan AND `--check` flags one while it lingers.
  - [ ] MECHANICAL: if A — duplication removed (one prune + one drift-detect implementation consumed by both `sync_plugin_assets.py` and `port_skills_to_openclaw.py`); both `--check`s and `goc validate` stay green.
  - [ ] PROCESS: this card's `advanced_by` instance cards are cross-referenced and, if C, the won't-fix rationale is durable enough that future audits do not re-file the family.
---

# Sync mechanisms reimplement orphan pruning and drift detection, and keep drifting

## The recurring shape

The repo has (at least) two payload-sync mechanisms that copy a
source-of-truth tree into a shipped mirror and must keep that mirror
*exactly* tracking the source — including removing dst-only orphans
left when a source file/dir is renamed or removed:

- `scripts/sync_plugin_assets.py` — `_sync_dir` / `_sync_codex_skill_tree`
  (write path) + `_check_changes` (`--check`), covering the
  `claude-plugin/` and `codex-plugin/` mirrors.
- `scripts/port_skills_to_openclaw.py` — `main()` write path +
  `drifted_skills()` (`--check`), covering `openclaw-plugin/skills/`.
- (Conceptually `goc install` / `goc._iter_skill_assets` performs the
  same full-tree copy into consumer repos, without a prune/check at all.)

Each mechanism independently reimplements the same two-part contract:
**(1) prune every dst-only orphan**, and **(2) a drift check that flags
any orphan the prune should have removed**. Because the logic is
duplicated, every new *orphan class* has to be discovered and patched
separately in each mechanism — and the drift checks share a recurring
`rglob("*")` blind spot (`if asset.is_dir(): continue`) that makes empty
orphan directories invisible to `--check`. A related drift-check
*completeness* gap: `port_skills_to_openclaw.py:279` reports only
`<orphan>/SKILL.md` for an orphaned ported dir, while the write path
(`:360`, `shutil.rmtree(orphan)`) removes the whole dir including
sibling assets — so `--check` still fires (exit 1) but under-lists which
files a re-port deletes (see `log.md` 2026-06-22 for the probe).

## Instance cards (the evidence this is a family, not a one-off)

1. [sync-plugin-assets-leaves-orphaned-hook-files-and-check-passes](../sync-plugin-assets-leaves-orphaned-hook-files-and-check-passes/) — sync, orphan *files*.
2. [sync-plugin-assets-leaves-orphaned-empty-skill-dirs-and-check-passes](../sync-plugin-assets-leaves-orphaned-empty-skill-dirs-and-check-passes/) — sync, empty orphan *dirs*.
3. [openclaw-skill-porter-never-prunes-orphaned-ported-skills](../openclaw-skill-porter-never-prunes-orphaned-ported-skills/) — porter, whole orphan *skill dirs*.
4. [openclaw-skill-porter-leaves-empty-orphan-subdir-when-nested-sibling-removed](../openclaw-skill-porter-leaves-empty-orphan-subdir-when-nested-sibling-removed/) — porter, empty orphan *nested subdirs* (the most recent; closing it is what surfaced this family).

Each was filed and fixed in isolation by mirroring the same patch into
the other mechanism. Instance 4's fix is verbatim the shape of instance
2's fix, retargeted at the porter — the tell-tale sign of a missing
shared abstraction ("five special cases hiding one rule").

## Why it matters

The cost is not just duplicated code: it is that a *fifth* orphan class
(or a third sync mechanism) will silently ship a stale payload until
someone notices, files an instance card, and hand-mirrors the fix into
each site. The drift `--check`s are the safety net that is supposed to
make this impossible, yet they share the exact blind spot the prune
code does, so a gap in one is usually a gap in the other. This belongs
to the same architectural family as
[dod-fence-mask-reimplements-commonmark-fences-and-keeps-drifting](../dod-fence-mask-reimplements-commonmark-fences-and-keeps-drifting/),
[yaml-lite-quote-scanners-reimplement-the-same-state-machine-and-keep-drifting](../yaml-lite-quote-scanners-reimplement-the-same-state-machine-and-keep-drifting/),
and [openclaw-hook-predicates-reimplement-engine-logic-and-keep-drifting](../openclaw-hook-predicates-reimplement-engine-logic-and-keep-drifting/):
duplicated logic that drifts and is repaired one instance at a time.

## Decision required

The fix is architectural and has more than one credible shape — a human
should pick the approach before implementation:

- **Option A — extract a shared helper.** A single module (e.g.
  `scripts/_mirror_sync.py` or a function pair in one of the existing
  scripts) implementing `prune_orphans(src, dst, *, excludes, preserve)`
  and `find_drift(src, dst, ...)`, consumed by both mechanisms. Removes
  the duplication outright; the `rglob`-skips-dirs blind spot can only
  exist in one place. Risk: the two mechanisms have genuine differences
  (Codex frontmatter normalization, OpenClaw host-neutral skill rewrite,
  per-pair `excludes`/`preserve_files`, the SKILL.md special-case) that
  the shared API must parameterize without becoming a leaky abstraction.

- **Option B — keep separate implementations, bind them with a shared
  test contract.** A single parametrized regression suite that asserts
  "for every sync mechanism: a removed source file/empty-dir/whole-dir
  leaves no dst orphan AND `--check` flags one while it lingers." Cheaper
  and lower-risk than refactoring; the mechanisms stay independent but a
  new orphan class is caught in every mechanism at once. Risk: does not
  remove the duplication, so the *prune* code can still drift even if the
  *contract* is shared.

- **Option C — do nothing / close as won't-fix.** If the maintainers
  judge that two mechanisms are few enough that per-instance fixing is
  acceptable, record that decision so future audits stop re-surfacing it.

Recommendation to weigh: Option B is the high-leverage / low-risk first
move (it would have caught all four instances), with Option A as a
follow-up if a third mechanism appears. But this is a maintainer taste
call about abstraction vs. duplication — hence the gate.

## Definition of Done

Replaced below once the approach is decided; placeholder criteria for now.
