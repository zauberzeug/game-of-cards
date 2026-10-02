---
title: cli-reference-plugin-switch-recipe-deletes-user-skills-and-the-next-upgrade-reverts-it
summary: "UNVERIFIED. goc.md:162 tells a vendored repo moving to the plugin to delete .claude/skills/, .claude/hooks/ and the GoC settings entries by hand, which also deletes every non-GoC skill the repo keeps there and leaves skills_source pinned to vendored. The next routine goc upgrade then re-vendors every GoC skill, hook and settings entry, restoring the duplicate hook firing the same section warns about, while the supported switch in AGENTS.md (edit skills_source: plugin, then goc upgrade) is documented nowhere a consumer reads."
status: active
stage: null
contribution: high
created: "2026-09-28T01:34:17Z"
closed_at: null
human_gate: none
advances:
  - doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them
advanced_by: []
tags: [bug, documentation, api-contract, unverified]
definition_of_done: |
  - [ ] TDD: a reproduce.py follows the `goc.md:162` recipe on a scratch `--local-skills` install holding one user-authored skill, then runs `goc upgrade`, and asserts the repo ends in plugin mode with the user skill intact — or the run disproves the hypothesis and the card flips to `disproved`
  - [ ] MECHANICAL: `goc.md`'s coexistence section gives the supported switch (`skills_source: plugin` in `.game-of-cards/config.yaml`, then `goc upgrade` and accept the cleanup) instead of a hand-delete of `.claude/skills/`, and says the cleanup preserves non-GoC skills
  - [ ] MECHANICAL: drop the `unverified` tag once reproduce.py lands; the correction carries a derive-from-tree guard or is listed on `doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them`
worker: {who: "claude[bot]", where: main}
---

# The CLI reference's plugin-switch recipe deletes user skills, and the next upgrade reverts it

> **UNVERIFIED.** Surfaced by an audit hunter on the docs-vs-code seam on
> 2026-09-28. The filing agent re-read and confirmed the citations. No
> `reproduce.py` was written this round; the falsification recipe is
> below.

## Location

- `goc.md:155-162`, under "Coexistence with the repo-local harness".
  Line 162 reads:
  > To clean up a previous repo-local harness installation, remove
  > `.claude/skills/`, `.claude/hooks/`, and the GoC hook entries from
  > `.claude/settings.json`, then rely on the plugin entirely.
- `AGENTS.md:313-318`, the real contract:
  > Switching modes is a manual config edit. To move a vendored repo to
  > plugin mode: edit `skills_source: plugin` in
  > `.game-of-cards/config.yaml`, then `goc upgrade` — which detects the
  > leftover `.claude/skills/` and prompts for cleanup. The cleanup only
  > removes GoC-managed skill directories, hook files, and settings
  > entries; non-GoC skills in `.claude/skills/` are preserved.
- `goc/install.py:2041` `claude_skills_mode = effective_skills_source()`.
  Then, at `:2054-2056`, a repo still pinned `skills_source: vendored`
  takes the branch `if claude_skills_mode == "vendored": local_skills_agents = frozenset(agents)`,
  which re-vendors every GoC skill and hook.
- None of `goc.md`, `README.md`, `ABOUT.md`, `site/llms.txt` or
  `claude-plugin/README.md` mentions `skills_source`.

## Hypothesis

The published recipe fails in two ways.

1. **It deletes user content.** Removing `.claude/skills/` wholesale takes
   every non-GoC skill the repo keeps there. The engine's own cleanup
   deliberately preserves those skills.
2. **It does not stick.** The recipe never touches
   `.game-of-cards/config.yaml`, so `skills_source` stays `vendored`
   (written by `goc install --local-skills`). The next routine
   `goc upgrade` (`goc.md:72-79` recommends one) re-vendors all GoC
   skills, hooks and `settings.json` entries. That restores the duplicate
   hook firing the same section tells the reader to avoid, and nothing
   warns: `goc validate` passes on the half-migrated repo.

The recipe predates `skills_source`: it was written on 2026-05-05 and the
key arrived on 2026-05-14. It was never updated. This is one more instance
of the family tracked by
[doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them](../doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them/).

## Why deferred

The citations are confirmed. The hunter's scratch run followed the recipe
on a `--local-skills` install, and `goc upgrade </dev/null` brought back
17 skill dirs, 3 hook scripts and 3 settings hook events. Following the
AGENTS.md flow instead preserved `.claude/skills/my-own-skill`. No
`reproduce.py` is committed this round.

## Falsification recipe

1. In a scratch repo, run `goc install --local-skills`.
2. Add `.claude/skills/my-own-skill/SKILL.md`.
3. Apply `goc.md:162` literally.
4. Run `goc upgrade </dev/null`.
5. If `.claude/skills/` stays absent, the hypothesis is disproved. Also
   disproved if `goc validate` warns about the half-migrated state.

Surfaced by: general-purpose audit hunter (human-facing docs vs code),
2026-09-28.
