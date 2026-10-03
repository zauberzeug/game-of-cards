---
title: upgrade-re-offers-the-plugin-cleanup-on-every-run-when-the-repo-keeps-its-own-skills
summary: "In plugin mode, goc upgrade offered the vendored-layout cleanup whenever a .claude/skills/ directory existed, but the cleanup deliberately keeps the repo's own skills there. So after a completed switch every later goc upgrade asked again and its already-at-version no-op verdict could never fire, while GoC hook scripts and settings entries left without a .claude/skills/ dir were never offered for removal (verified by reproduce.py). The offer now asks _strip_claude_vendored_harness in probe mode whether it has GoC content to remove, the prompt and dry-run note stop naming .claude/skills/ as what was found, and four regression tests in tests/test_install.py pin both directions and the probe."
status: done
stage: null
contribution: medium
created: "2026-10-02T04:45:40Z"
closed_at: "2026-10-03T04:46:31Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero — after a confirmed cleanup that kept a repo-owned skill, the next `goc upgrade` neither offers the cleanup nor announces it under `--dry-run`, and a plugin-mode repo holding GoC hook scripts and settings entries but no `.claude/skills/` is offered the cleanup and ends with none of them
  - [x] TDD: regression tests in `tests/test_install.py` pin both directions, plus `_strip_claude_vendored_harness(..., probe=True)` reporting the pending removal while changing nothing on disk
  - [x] MECHANICAL: the offer asks the cleanup executor in `probe=True` mode instead of restating it as a directory test, and the prompt text and dry-run note stop naming `.claude/skills/` as what was found; `AGENTS.md`'s switch paragraph says what the detection keys on
  - [x] PROCESS: `uv run python -m unittest discover -s tests` and `uv run goc validate` pass
worker: {who: "claude[bot]", where: main}
---

# goc upgrade re-offered the plugin cleanup on every run once the repo kept its own skills

> **Fixed 2026-10-03.** Filed and claimed on 2026-10-02 as a side finding of
> [cli-reference-plugin-switch-recipe-deletes-user-skills-and-the-next-upgrade-reverts-it](../cli-reference-plugin-switch-recipe-deletes-user-skills-and-the-next-upgrade-reverts-it/).
> That run ended before fixing it through, and the next pull resumed it.
> The offer now asks the cleanup, in probe mode, what it would remove.

## What was broken

`goc/install.py`, `upgrade()`, decided whether to offer the plugin-mode
cleanup with a directory test:

```python
    claude_has_vendored = False
    if "claude" in agents:
        claude_shim = _load_agent_shim(templates, "claude")
        claude_has_vendored = bool(claude_shim.skills and (target / claude_shim.skills.target).is_dir())

    needs_vendored_cleanup = claude_skills_mode == "plugin" and claude_has_vendored
```

`needs_vendored_cleanup` drove the prompt, the `--dry-run` note
("will offer cleanup of leftover .claude/skills/ (plugin mode)"), and
`pending_cleanup`, one of the terms in the "already at goc X — nothing to
do." short-circuit.

The executor it stood in for, `_strip_claude_vendored_harness`, removes
three things: the skill dirs named like GoC's skill templates, the GoC hook
scripts (plus the `_goc-bootstrap.sh` shim file), and the GoC entries in
`.claude/settings.json`. It keeps user-authored skills with other names,
and the prompt tells the user so.

The offer tested whether a directory existed, while the cleanup works on
GoC content. The two disagreed in both directions:

1. **A completed switch was offered again, forever.** The cleanup keeps the
   repo's own skills, so `.claude/skills/` survives it whenever the repo
   has one. Every later `goc upgrade` then printed "a leftover
   .claude/skills/ from a prior vendored install was found" and asked
   again. `pending_cleanup` stayed true, so the "already at goc X — nothing
   to do." verdict could never fire. On a TTY the user was asked on every
   upgrade; with empty stdin it printed "Skipping cleanup" on every run.
2. **GoC leftovers without a skills dir were never offered.** A repo in
   plugin mode that still had `.claude/hooks/deck_*.py` and the GoC
   registrations in `settings.json`, but no `.claude/skills/`, was never
   offered the cleanup. Those hooks kept firing beside the plugin's.
   `goc validate`'s `PLUGIN_AND_VENDORED_HOOKS_DOUBLE_FIRE` warning tells
   the user to run `goc upgrade` and accept its cleanup, and in this state
   there was no cleanup to accept.

## Evidence

`reproduce.py` builds two scratch `goc install --local-skills` repos and
switches each with `skills_source: plugin`, the documented way. Repo A
keeps a skill of its own. Repo B lost `.claude/skills/` to a hand cleanup
but kept the GoC hooks and settings entries. Before the fix (exit 1):

```
[A] switch upgrade: offered=True; .claude/skills/ now holds ['my-own-skill']
[A] next routine upgrade: offered again=True; no-op verdict=False
[A] --dry-run announces cleanup=True
[B] before upgrade: 3 GoC hook scripts, 3 GoC settings entries
[B] upgrade offered the cleanup=False; after: 3 scripts, 3 entries

FAIL:
  A: the cleanup is re-offered after it ran, for a layout holding only the repo's own skill
  B: GoC hook scripts / settings entries survive because no .claude/skills/ dir triggers the offer
```

After the fix (exit 0):

```
[A] switch upgrade: offered=True; .claude/skills/ now holds ['my-own-skill']
[A] next routine upgrade: offered again=False; no-op verdict=True
[A] --dry-run announces cleanup=False
[B] before upgrade: 3 GoC hook scripts, 3 GoC settings entries
[B] upgrade offered the cleanup=True; after: 0 scripts, 0 entries

OK: the cleanup is offered exactly when it has GoC content to remove.
```

## Why it matters

[cli-reference-plugin-switch-recipe-deletes-user-skills-and-the-next-upgrade-reverts-it](../cli-reference-plugin-switch-recipe-deletes-user-skills-and-the-next-upgrade-reverts-it/)
made `goc.md` send consumers through this exact switch, and it stresses
that the cleanup keeps the repo's own skills. Case 1 was therefore the
normal outcome for any repo that keeps a skill of its own. Case 2 is the
state a partial hand cleanup leaves, and it is the state where duplicate
hook firing persists.

## Fix

The offer now asks the executor rather than restating it. This is the
repo's convention for upgrade-time work signals
(`_write_skills_source(probe=True)`, `_sync_skill_tree(probe=True)`;
`AGENTS.md` § "`.game-of-cards/` ownership model and `goc upgrade`
contract"):

- `_strip_claude_vendored_harness(target, templates, *, probe=False) -> bool`
  works out the GoC skill dirs, hook/shim files and settings entries once.
  With `probe=True` it returns whether there are any and touches nothing.
  The real run removes them in the same order as before and returns the
  same answer.
- `_strip_goc_settings_entries(settings_path, *, probe=False) -> bool`
  returns whether it would change the file. With `probe=True` it skips the
  write and the malformed-file warnings, which the real run still prints.
- `upgrade()` sets `needs_vendored_cleanup` from
  `_strip_claude_vendored_harness(target, templates, probe=True)` in plugin
  mode, so the prompt, the `--dry-run` note and `pending_cleanup` all read
  the cleanup's own answer.
- The prompt says "GoC files from a prior vendored install were found",
  and the dry-run note says "will offer cleanup of GoC files from a prior
  vendored install (plugin mode)". Neither names `.claude/skills/` as what
  was found.
- `AGENTS.md`'s switch paragraph says the offer keys on GoC-owned leftovers
  (GoC-named skill dirs, the bootstrap shim, hook scripts, settings
  entries) rather than on the directory. Its upgrade-contract paragraph
  names the probe next to the `skills_source` pin's.

Regression tests in `tests/test_install.py`, all four failing on the
pre-fix code:

- `test_upgrade_does_not_reoffer_cleanup_once_only_repo_owned_skills_remain`
  covers direction 1. The routine upgrade after the switch reaches the
  no-op verdict without an offer. With the version stamp rolled back, the
  `--dry-run` output carries no cleanup note and the real run asks
  nothing.
- `test_upgrade_offers_cleanup_for_goc_hooks_left_without_a_skills_dir`
  covers direction 2, through `--dry-run` and an accepted upgrade.
- `test_strip_vendored_harness_probe_reports_pending_removal_without_touching_disk`
  shows the probe is true for each kind of leftover on its own, false once
  only the repo's own files remain, and leaves every byte on disk as it was.
- `test_strip_goc_settings_entries_probe_writes_and_warns_nothing` pins the
  settings half of the probe.

Scope: the probe inherits the executor's identification rule (current
template names). Prior-version names stay the business of
[goc-upgrade-cleanup-misses-prior-version-skills-and-hooks-renamed-since-install](../goc-upgrade-cleanup-misses-prior-version-skills-and-hooks-renamed-since-install/).
Whatever rule that card adopts, the offer follows it without a second site
to change. Under the plugin's bundled engine, which cannot name GoC's skill
dirs
([plugin-engine-cleanup-leaves-every-goc-skill-dir-its-prompt-promises-to-remove](../plugin-engine-cleanup-leaves-every-goc-skill-dir-its-prompt-promises-to-remove/)),
the offer now also stops once the hooks and settings entries are gone,
because that cleanup has nothing left it can remove. That card's
`reproduce.py` still exits 1, as before.
