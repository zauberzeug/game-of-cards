---
title: goc-upgrade-cleanup-misses-prior-version-skills-and-hooks-renamed-since-install
summary: "`_strip_claude_vendored_harness` (goc/install.py:773-819) and `_sync_skill_tree(replace_skills=True)` (install.py:1140-1178) identify GoC-owned content by enumerating the *current* templates directory. Any skill or hook GoC shipped in a *prior* version but has since renamed or removed (real example: `bootstrap/` → `kickoff/`, see closed card `rename-bootstrap-to-kickoff-as-onboarding-dialog`) is therefore not in the GoC-owned set, so the cleanup `shutil.rmtree` skips it. Stale prior-version GoC content survives indefinitely in `.claude/skills/` and `.claude/hooks/`, accumulating across upgrades. The closed predecessor `goc-upgrade-clobbers-non-goc-skills-and-validate-fails-in-plugin-mode` deliberately tightened these sets to preserve user-authored content; the unintended consequence is that *GoC*-authored content from earlier versions is now indistinguishable from user content under the current identification rule."
status: open
stage: null
contribution: medium
created: "2026-05-31T02:38:42Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, infra, api-contract, meta-fix]
definition_of_done: |
  - [ ] TDD: regression test scaffolds a Claude-vendored install where `.claude/skills/` contains a current-template skill plus a synthetic prior-version skill dir whose name is NOT in current templates; after `_strip_claude_vendored_harness`, the prior-version dir is gone (today the test would FAIL because the dir is preserved)
  - [ ] TDD: regression test scaffolds a `.claude/hooks/` dir with one current-template hook file plus a synthetic prior-version hook file whose path is NOT registered in `GOC_CLAUDE_HOOKS`; after cleanup, the prior-version file is gone
  - [ ] TDD: regression test scaffolds a Claude-vendored install with one current-template skill plus one user-authored skill plus one prior-version GoC skill; after `_sync_skill_tree(replace_skills=True)`, the user-authored skill survives AND the prior-version GoC skill is gone — verifying the discriminator distinguishes the two categories
  - [ ] PROCESS: decision recorded in `## Decision (recorded)` section — which identification mechanism (sentinel file / SKILL.md frontmatter marker / historical-name registry / other) was chosen and why
  - [ ] MECHANICAL: identification mechanism implemented at all three sites — `_strip_claude_vendored_harness` (skills loop, hooks loop) and `_sync_skill_tree` `replace_skills` path — sharing one helper so future drift between sites is hard to introduce
  - [ ] EMPIRICAL: `uv run goc install --local-skills` followed by manual rename of one template skill, followed by another install, leaves no orphan dir in `.claude/skills/`; recipe and observed output captured in log.md
  - [ ] MECHANICAL: AGENTS.md "`.game-of-cards/` ownership model" subsection updated to describe how GoC-owned cleanup distinguishes prior-version GoC content from user-authored content
  - [ ] PROCESS: `uv run goc validate` passes; full unittest regression suite passes
---

# goc upgrade cleanup misses prior-version skills and hooks renamed since install

## Location

- `goc/install.py:773-819` — `_strip_claude_vendored_harness`, called from the vendored→plugin migration cleanup path (`install.py:1641-1653`)
- `goc/install.py:1140-1178` — `_sync_skill_tree` `replace_skills` path, called from the vendored in-place refresh during `goc upgrade --keep-local-skills`
- `goc/install.py:803-806` — hook-file enumeration inside `_strip_claude_vendored_harness` (same shape)

## What's broken

All three sites identify GoC-owned content by intersecting the on-disk
state with the **current** template tree. From `_strip_claude_vendored_harness`:

```python
skills_src = templates / "skills"
goc_owned = {
    p.name for p in skills_src.iterdir()
    if p.is_dir() and skill_for_agent(p.name, "claude")
}
for child in list(skills_dir.iterdir()):
    if child.is_dir() and child.name in goc_owned:
        shutil.rmtree(child)
```

`goc_owned` enumerates whatever `goc/templates/skills/` ships *today*.
A skill GoC shipped in a prior release — but has since been renamed
or removed — does not appear in `goc_owned`, so the `shutil.rmtree`
silently skips it. The doctring claims it "removes only the skill
directories whose names match GoC templates," which is true to the
letter but obscures the consequence: anything not currently shipped
is, by this rule, indistinguishable from user-authored content.

The hooks loop at lines 803-806 has the same shape:

```python
for cmd in GOC_CLAUDE_HOOKS.values():
    m = _HOOK_FILE_RE.search(cmd)
    if m:
        files_to_remove.add(target / m.group(1))
```

`GOC_CLAUDE_HOOKS` enumerates the *current* registration set. A hook
file GoC registered in a prior release but has since dropped from the
manifest is not in the iteration and survives.

`_sync_skill_tree(replace_skills=True)` (install.py:1162-1166) repeats
the pattern for the in-place vendored refresh:

```python
eligible = {
    p.name for p in skills_src.iterdir() if p.is_dir() and skill_for_agent(p.name, agent)
}
if replace_skills:
    for name in sorted(eligible):
        target = skills_dst / name
        if target.exists():
            shutil.rmtree(target)
```

Only `eligible` (current-template) dirs are wiped before recopy. A
prior-version dir that current templates no longer ship is left in
place untouched.

## Why it matters

This is the inverted-failure-mode sibling of the closed card
[`goc-upgrade-clobbers-non-goc-skills-and-validate-fails-in-plugin-mode`](../goc-upgrade-clobbers-non-goc-skills-and-validate-fails-in-plugin-mode/).
That card protected user-authored skills by narrowing the cleanup
set to "names matching current templates." The tightening was
correct for user content but accidentally protected GoC's *own*
prior content too, because the discriminator can't tell the two
categories apart.

Reachability path (concrete consumer flow):

1. Consumer installs GoC at version *N* via
   `uv run goc install --local-skills`. Vendored layout lands in
   `.claude/skills/` including a skill named `bootstrap/`.
2. GoC ships version *N+M* in which `bootstrap/` was renamed to
   `kickoff/` — this rename actually happened, per the closed card
   [`rename-bootstrap-to-kickoff-as-onboarding-dialog`](../rename-bootstrap-to-kickoff-as-onboarding-dialog/).
3. Consumer runs `uv run goc upgrade --keep-local-skills` (or
   migrates `skills_source` to `plugin` and confirms cleanup).
4. `_sync_skill_tree(replace_skills=True)` refreshes
   `.claude/skills/kickoff/` from current templates, but the orphan
   `.claude/skills/bootstrap/` is preserved — `kickoff` is in
   `eligible`, `bootstrap` is not, the rmtree loop skips it.
5. The user now has a stale `bootstrap/` skill on disk that GoC's
   normal upgrade flow won't touch, references a `goc` API surface
   from version *N*, and silently shadows nothing useful — pure clutter
   accumulating across the version boundary.

The same pattern applies symmetrically for hook files removed from
`GOC_CLAUDE_HOOKS` between releases.

Consumer impact is bounded (only fires when GoC renames/removes
content across an upgrade boundary), but the cleanup contract
documented at install.py:776-779 ("removes only the skill directories
whose names match GoC templates") quietly under-delivers in the worst
case it can fire.

## Empirical evidence

`uv run python .game-of-cards/deck/goc-upgrade-cleanup-misses-prior-version-skills-and-hooks-renamed-since-install/reproduce.py`:

```
current-template skill removed by cleanup: True
prior-version skill survives cleanup:      True

BUG REPRODUCED: prior-version GoC content survives cleanup
because the discriminator is the current-templates name set,
which does not include skills that have been renamed/removed.
```

Exit code 1 (bug reproduced). The current-template skill (`kickoff`)
is correctly removed; the prior-version GoC skill (`bootstrap`)
survives despite being equally GoC-owned content. The reproducer
exercises `_strip_claude_vendored_harness` directly; the analogous
hook-loop omission (install.py:803-806) is verified by reading —
`GOC_CLAUDE_HOOKS` only enumerates the current registration set.

## Decision required

Pick the discriminator that distinguishes GoC-owned content from
user-authored content WITHOUT relying on the current-templates name
intersection. The options:

**Option A — Sentinel marker file inside each GoC-managed dir.**
`goc install --local-skills` writes a hidden `.goc-managed` marker
into each generated skill/hook directory. Cleanup uses presence of
the marker as the discriminator.
- ➕ Stable across renames; survives if the skill is moved/renamed
  by hand.
- ➖ Adds one hidden file per dir; needs a one-time migration for
  prior-version installs that lack the marker (which is the very
  case this card is trying to fix).
- ➖ Marker-less existing installs need a fallback — likely the
  current behavior — which re-introduces the orphan problem for the
  transition period.

**Option B — Read SKILL.md frontmatter for a `source: goc` key.**
The skill template generator writes `source: goc` into every shipped
SKILL.md. Cleanup parses the YAML frontmatter and removes any
directory whose SKILL.md carries that key.
- ➕ Single change to the template; no separate marker file.
- ➕ Survives renames and is observable by reading the file.
- ➖ Requires backfilling existing installs (same transition issue
  as Option A).
- ➖ Couples cleanup to a frontmatter parser; if a user's SKILL.md
  has malformed YAML, behavior under cleanup is murky.

**Option C — Historical-name registry shipped in the engine.**
`goc/install.py` exposes `GOC_HISTORICAL_SKILL_NAMES` and
`GOC_HISTORICAL_HOOK_PATHS` listing every skill / hook GoC has ever
shipped. Cleanup unions current templates with the historical set.
- ➕ No on-disk migration needed; existing installs benefit
  immediately.
- ➕ Pure code change; no file-format change.
- ➖ Release discipline burden: every rename/removal must be
  accompanied by an entry in the historical registry, easy to forget.
- ➖ Registry grows unboundedly; conceptually a "what we used to be"
  list inside a tool that doesn't otherwise track history.

**Option D — Compose Option B (forward) with Option C (backward).**
New installs write `source: goc`; the engine also ships a
historical-name registry covering pre-marker versions. Marker takes
precedence; registry is the fallback for un-markered legacy installs.
- ➕ Cleanest separation between forward and backward concerns.
- ➖ Two mechanisms to maintain.

**Recommendation (non-binding, for the human picker):** Option C
keeps the immediate scope small (no on-disk migration, no template-
generator change, no marker rollout), and the maintenance burden is
visible to whoever proposes a rename/removal in a PR. Option D's
extra complexity only pays off if we expect another round of skill
renames, which we don't.

## Fix sketch (once a decision lands)

A single helper `_is_goc_owned_dir(path, agent) -> bool` lives in
`install.py`; the three sites all call it. For the chosen mechanism
the helper inspects either (A) the sentinel file, (B) the SKILL.md
frontmatter, or (C) the union of current-template names plus the
historical-name registry.

## Cross-references

- `goc-upgrade-clobbers-non-goc-skills-and-validate-fails-in-plugin-mode` — the closed predecessor that introduced the tightened-cleanup contract this card refines.
- `rename-bootstrap-to-kickoff-as-onboarding-dialog` — the closed card that documents the real rename which surfaces the orphan in the wild.
- `goc-upgrade-cleanup-deletes-user-authored-empty-hook-event-lists` and `goc-upgrade-cleanup-deletes-user-authored-empty-hook-group-lists` — sibling refinements to the user-content preservation contract.
- `sync-plugin-assets-leaves-orphaned-empty-skill-dirs-and-check-passes` — sibling shape inside `scripts/sync_plugin_assets.py` (different code path, same root architectural pattern).
