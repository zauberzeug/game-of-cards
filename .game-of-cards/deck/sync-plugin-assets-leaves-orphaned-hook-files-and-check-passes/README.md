---
title: sync-plugin-assets-leaves-orphaned-hook-files-and-check-passes
summary: "When a hook template under goc/templates/hooks/ is renamed or removed, the sync's single-file hook pairs are enumerated from the CURRENT template set, so the retired file is never pruned from the three flat hook mirrors (claude-plugin/hooks/, codex-plugin/hooks/, .claude/hooks/) and `--check` reports OK because it only compares pair-listed paths. The engine's validate_plugin_mirror_parity has the identical blind spot. Consumers keep executing the stale hook code that hooks.json still references — with every tripwire green. Skill DIRS got this exact fix already; the single-file hook pairs were left out."
status: active
stage: null
contribution: medium
created: "2026-06-12T04:43:21Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, meta-fix]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero — after a hook template is removed and sync runs, the corresponding file is gone from all three flat hook mirrors, and `--check` FAILs while a stale one remains.
  - [ ] TDD: non-GoC files in the hook mirror dirs (claude-plugin/hooks/hooks.json, codex-plugin/hooks/hooks.json) survive the sync untouched (no over-eager prune).
  - [ ] TDD: `validate_plugin_mirror_parity` (goc/engine.py) flags a dst-only hook file in claude-plugin/hooks/ and codex-plugin/hooks/ as drift.
  - [ ] PROCESS: `uv run python -m unittest discover -s tests` is green; `uv run goc validate` is clean.
worker: {who: "claude[bot]", where: main}
---

# `sync_plugin_assets.py` leaves orphaned hook files in plugin mirrors, and `--check` passes anyway

## Location

- `scripts/sync_plugin_assets.py:107-115` (claude), `:130-137` (codex),
  `:185-192` (dogfood `.claude/hooks/`) — hook mirrors are *single-file*
  sync pairs enumerated from the **current** template set:

  ```python
  for name in hook_names:
      pairs.append(
          (
              templates / "hooks" / name,
              ROOT / "claude-plugin" / "hooks" / name,
              frozenset(),
              frozenset(),
          )
      )
  ```

- `_sync_file` (`scripts/sync_plugin_assets.py:326-331`) only copies
  src → dst; it has no concept of an orphan.
- `_check_changes` single-file branch (`scripts/sync_plugin_assets.py:523-525`)
  only runs `filecmp.cmp` on pair-listed paths:

  ```python
  else:
      if not dst.exists() or not filecmp.cmp(src, dst, shallow=False):
          out.append(dst)
  ```

- `goc/engine.py:1204-1211` — `validate_plugin_mirror_parity` builds its hook
  pairs the same way (`for name in hook_names:` from
  `deck_hook_scripts(templates_root)`), so the engine tripwire shares the
  blind spot.

## What's broken

`hook_names = deck_hook_scripts(templates)` returns the basenames of the
`.py` files that exist under `goc/templates/hooks/` **today**. When a hook
template is renamed or removed, the retired basename simply vanishes from
the pair list — so the copy of it sitting in `claude-plugin/hooks/`,
`codex-plugin/hooks/`, and `.claude/hooks/` is invisible to both the sync
(nothing prunes it) and `--check` (nothing compares it). The deep mirrors
(`claude-plugin/goc/templates/hooks/` etc.) are dir-syncs and prune the
orphan correctly, so the payload becomes internally inconsistent: the deep
mirror says the hook is gone, the flat mirror still ships it.

Contrast: skill **directories** had this exact defect and got fixed —
[`sync-plugin-assets-leaves-orphaned-empty-skill-dirs-and-check-passes`](../sync-plugin-assets-leaves-orphaned-empty-skill-dirs-and-check-passes/)
added orphan pruning to `_sync_dir` and an orphan walk to `_check_changes`'s
dir branch. The single-file hook pairs were left out of that fix. This is
the third instance of the "mirror set derived from the current source set"
shape (porter → `openclaw-skill-porter-never-prunes-orphaned-ported-skills`,
dir-sync → the card above, now the single-file pairs), hence `meta-fix`.

## Empirical evidence

In a full `/tmp` copy of the repo: `git mv
goc/templates/hooks/deck_prompt_router.py deck_prompt_router_v2.py`, update
`GOC_CLAUDE_HOOKS`, then:

- `python3 scripts/sync_plugin_assets.py` → "synced 10 file(s)"
- `python3 scripts/sync_plugin_assets.py --check` → **"OK — … byte-for-byte.", exit 0**
- stale `deck_prompt_router.py` still present in all three flat mirrors
  (`claude-plugin/hooks/`, `codex-plugin/hooks/`, `.claude/hooks/`) while the
  deep mirror `claude-plugin/goc/templates/hooks/` correctly pruned it
- `uv run goc validate` → exit 0; `python -m unittest
  tests.test_plugin_mirror_parity` → OK

`reproduce.py` in this card dir drives the same scenario in-tree with a
temp hook template (cleaning up after itself; note the sync auto-stages, so
it may leave index entries to `git restore --staged`). Verbatim output
today:

```
DEFECT PRESENT:
  - stale claude-plugin/hooks/zzz_temp_reproduce_hook.py survives the sync
  - stale codex-plugin/hooks/zzz_temp_reproduce_hook.py survives the sync
  - stale .claude/hooks/zzz_temp_reproduce_hook.py survives the sync
  - --check exits 0 while a stale hook file sits in claude-plugin/hooks/
exit=1
```

## Why it matters (reachability path)

The offending state is produced by the ordinary maintenance action this
sync exists to support: renaming or retiring a hook template. The repo's
own docs (AGENTS.md, `deck_hook_scripts` docstring) advertise "dropping a
new `.py` file in templates/hooks/ wires it in automatically" — the
symmetric removal path silently doesn't work. Worse,
`claude-plugin/hooks/hooks.json` (hand-maintained, not auto-synced) keeps
its `"command": "python3 ${CLAUDE_PLUGIN_ROOT}/hooks/<old-name>.py"` entry
pointing at the *stale* file, which still exists — so plugin consumers keep
executing the retired hook logic indefinitely, with `--check`, `goc
validate`, and the parity tests all green.

## Fix

Follow the precedent set by the skill-dir fix (rubric-derived from the two
prior siblings; no open design question):

1. Replace the per-name single-file hook pairs with a **dir-sync** of
   `templates/hooks/` → each flat mirror, using the existing
   `preserve_files` mechanism (already used for `_goc-bootstrap.sh`) to
   protect the non-synced `hooks.json` in `claude-plugin/hooks/` and
   `codex-plugin/hooks/`. The dir-sync machinery already prunes orphans and
   already has the `--check` orphan walk. Alternatively, add an explicit
   orphan prune + check for dst `*.py` files not in `hook_names`.
2. Extend `validate_plugin_mirror_parity` (`goc/engine.py:1204`) the same
   way so the engine tripwire flags a dst-only hook file as drift.
3. Regression test in `tests/` (e.g. alongside
   `tests/test_plugin_mirror_parity.py`).

Out of scope (note for a future card if wanted): a validator check that
`hooks.json` entries reference existing hook files.

## Cross-references

- [`sync-plugin-assets-leaves-orphaned-empty-skill-dirs-and-check-passes`](../sync-plugin-assets-leaves-orphaned-empty-skill-dirs-and-check-passes/)
  — the skill-dir instance of the same shape (fixed; defines the fix
  pattern).
- [`openclaw-skill-porter-never-prunes-orphaned-ported-skills`](../openclaw-skill-porter-never-prunes-orphaned-ported-skills/)
  — the porter instance (fixed).
