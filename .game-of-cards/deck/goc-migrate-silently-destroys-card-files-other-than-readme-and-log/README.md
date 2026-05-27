---
title: goc-migrate-silently-destroys-card-files-other-than-readme-and-log
summary: "`goc migrate` classifies a card present in both the legacy `deck/` and canonical `.game-of-cards/deck/` trees as `identical` using only a README.md + log.md byte comparison, skips it from the copy loop, then `shutil.rmtree`s the whole legacy tree — silently destroying any legacy-only file in that card dir (reproduce.py, notes, attachments). One-time migration data loss."
status: open
stage: null
contribution: medium
created: "2026-05-27T13:40:59Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero — a legacy-only `reproduce.py` (and any other extra file) survives `goc migrate` into the canonical card dir.
  - [ ] TDD: a regression test in `tests/` covers the both-trees-identical-README-but-extra-legacy-file case (legacy-only file is preserved, not lost).
  - [ ] MECHANICAL: the chosen fix path (see `## Decision required`) is implemented in `_cmd_migrate` (`goc/engine.py`).
  - [ ] PROCESS: `uv run goc validate` clean; full regression suite green; plugin-asset sync `--check` green.
---

# `goc migrate` silently destroys card files other than README.md and log.md

## Location

`goc/engine.py:4391-4449` — the drift/identity check and the unconditional
`shutil.rmtree(legacy)` in `_cmd_migrate`.

## What's broken

`goc migrate` merges the legacy `deck/` tree into the canonical
`.game-of-cards/deck/` tree. For a card directory present in **both**
trees, it decides whether the two copies have "drifted" by comparing
**only** `README.md` and `log.md`:

```python
for name in sorted(legacy_dirs):
    if name not in canonical_dirs:
        to_copy.append(name)
        continue
    drifted = False
    for fname in ["README.md", "log.md"]:
        lf = legacy_dirs[name] / fname
        cf = canonical_dirs[name] / fname
        if lf.exists() and cf.exists() and lf.read_text() != cf.read_text():
            conflicts.append(...)
            drifted = True
        elif lf.exists() and not cf.exists():
            conflicts.append(...)
            drifted = True
    if not drifted:
        identical.append(name)
```

A card whose README + log match byte-for-byte across the two trees is
appended to `identical`. Cards in `identical` are **never copied** — the
copy loop only iterates `to_copy` (legacy-only card names):

```python
for name in to_copy:
    shutil.copytree(str(legacy_dirs[name]), str(canonical / name))
    print(f"  migrated: {name}")

shutil.rmtree(legacy)
```

Then the entire legacy tree is removed. So any file that lives **only**
in the legacy copy of an `identical` card — `reproduce.py`, `notes.md`,
HTML/SVG decision artifacts (all first-class card-dir files; see
`Skill(create-card)` Steps 6-7) — is silently destroyed. The file-set is
never compared, and the `elif ... not cf.exists()` conflict branch only
fires for `README.md`/`log.md`, never for arbitrary extra files.

## Empirical evidence

`reproduce.py` builds a temp tree where card `foo` exists in both trees
with identical README + log, but the legacy copy also carries
`reproduce.py`. After `_cmd_migrate(auto_yes=True)`:

```
Cards already in canonical tree (identical, will skip): 1
Removed legacy tree: /tmp/.../deck
Migration complete. Run `goc validate` to confirm.
legacy tree removed: True
canonical foo/reproduce.py exists: False

FAIL: reproduce.py was destroyed by goc migrate
expected: .game-of-cards/deck/foo/reproduce.py exists
actual:   missing (legacy tree deleted, card classified 'identical', never copied)
```

## Why it matters

`reproduce.py` is the executable proof-of-defect that bug-class cards
ship (dozens of cards in this repo's own deck carry one). The migrate
verb is the one-time legacy→canonical path consumers run exactly once;
it is destructive and irreversible (`shutil.rmtree`). A migration that
claims "identical, will skip" while quietly deleting bug reproducers,
notes, and decision artifacts violates the project's data-safety
discipline and the migrate verb's implicit contract that a card already
in the canonical tree is left whole.

## Decision required

The fix path is not fully mechanical — two credible behaviors, and the
choice changes the verb's contract:

- **Option A — copy the union (merge, lossless-by-default).** Before
  `rmtree`, for each `identical` card copy any legacy-only file into the
  canonical card dir (don't overwrite canonical files). Migration stays
  one-shot and never loses data, but it silently introduces files the
  canonical tree didn't have.
- **Option B — treat any extra legacy-only file as a conflict.** Extend
  the drift check to compare the full file set (not just README/log);
  a legacy-only extra file becomes a `conflicts` entry, so migrate
  refuses and the human resolves manually — same discipline already
  applied to drifted README/log. Safer/explicit, but turns a
  previously-silent "identical" into a hard stop.

Recommended: **Option A** (the verb's job is to consolidate without
loss; a missing reproducer is strictly worse than an extra file
appearing in canonical). Pick before implementing.
