## 2026-09-21 — CONFIRMED then fixed

Ran the card's falsification recipe as `reproduce.py`: a throwaway
`REPO_ROOT`-shaped tree with one eligible skill mirrored into
`codex-plugin/skills/`, then a CRLF rewrite of a non-`SKILL.md` sibling and an
empty orphan subdirectory planted in the mirror. Both guards run over the same
tree. The unmutated tree is clean to both, so the verdicts below are the two
mutations and nothing else.

Both guards' verdicts, side by side:

| | `scripts/sync_plugin_assets.py` `_check_codex_skill_tree` | `engine.validate_plugin_mirror_parity` |
|---|---|---|
| **before** | `codex-plugin/skills/foo-skill/reference.md`, `codex-plugin/skills/zzz-orphan-dir` | *(no `codex-plugin/skills` findings)* |
| **after** | unchanged | `plugin mirror drift: goc/templates/skills vs codex-plugin/skills: foo-skill/reference.md (differs), zzz-orphan-dir (only in codex-plugin/skills)` |

**DEFECT confirmed**, exactly as hypothesised — the engine returned `[]` for
`codex-plugin/skills` in both cases while the sync check named both paths. The
`unverified` tag is dropped.

Fix in `goc/engine.py`, `_validate_codex_skill_mirror` inside
`validate_plugin_mirror_parity`:

- Sibling comparison: `read_bytes()` instead of `read_text()`. `read_text()`
  applies universal-newline translation, so the CRLF mirror copy read
  text-identical to its LF source (`reproduce.py` asserts that precondition
  rather than assuming it). `SKILL.md` stays a text comparison — that is what
  `_check_codex_skill_tree` does too, and the target is lockstep with the sync
  check, not a third policy.
- Destination walk: stop blanket-`continue`-ing on `is_dir()`. A directory with
  no source counterpart that is *empty* is now reported; a non-empty orphan
  still surfaces through its own files, so it is not double-counted. git masks
  empty dirs, so nothing else would have caught one.

Guard for the lockstep the card asks for:
`tests/test_codex_skill_transform_lockstep.py` (7 tests). It pins the two
directly-callable copies (`goc/install.py`, `scripts/sync_plugin_assets.py`)
head-on over a corpus of awkward frontmatter shapes — no frontmatter,
unterminated frontmatter, `---` inside the description, unicode, absent
`description` — plus every shipped codex-eligible template. The engine's third
copy is nested inside `validate_plugin_mirror_parity` and not directly
callable, so it is pinned by behaviour instead: a mirror written by the real
`_write_codex_skill` is drift-free to both readers, an untransformed one is
drift to both, and the CRLF sibling and empty orphan dir are drift to both.
Assertions are about output, not about how many functions produce it, so the
guard survives whichever consolidation the sibling card lands.

Discrimination checked rather than assumed: the suite was re-run against
`git show HEAD:goc/engine.py` in a temp package copy —
`test_crlf_sibling_is_drift_to_both` and `test_empty_orphan_dir_is_drift_to_both`
both FAIL there (`'reference.md' not found in ''`,
`'zzz-orphan-dir' not found in ''`) and pass on the fixed engine.

`codex-skill-frontmatter-normalization-reimplemented-in-install-and-sync`
(open, `human_gate: decision`) amended: its `## Location` now enumerates three
sites, `## What's broken` counts three, and `## Decision required` option 1
says the engine drops its nested copy while option 3 notes the parity test now
partly exists. Its title still reads `install-and-sync`; not renamed, because
it is parked in a human's triage queue and the body carries the correction.
The duplication itself stays open there — this card closed the *lag*, not the
root cause.

## 2026-09-21 — Closure

- **What changed**: `goc/engine.py` `_validate_codex_skill_mirror` — siblings
  compared by bytes, empty orphan directories reported; the shipped guard now
  matches `scripts/sync_plugin_assets.py --check` on both points. New
  `tests/test_codex_skill_transform_lockstep.py` pins all three copies.
  Sibling consolidation card amended to three sites.
- **Verification**: `reproduce.py` exits 0 (was 1 pre-fix, with the engine
  reporting nothing while the sync check named both paths).
- **Audit**: no rubric configured; mechanical fix — it adopts the shape
  `scripts/sync_plugin_assets.py` already shipped rather than inventing a
  third policy.
- **Project impact**: `goc validate` gets marginally stricter for consuming
  repos that vendor a Codex payload — a CRLF sibling or an empty orphan skill
  dir that used to pass now reports drift. That is the intended widening; the
  live tree is clean under it.
- **Tests**: `uv run python -m unittest discover -s tests` 1182 passed (7 new);
  `uv run goc validate` clean; `uv run python scripts/sync_plugin_assets.py
  --check` green after re-syncing the three engine mirrors.

## Closure verification (2026-09-21T05:19:24Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 6/6 ticked
- [x] log-md-closure-entry — '## 2026-09-21 — Closure' present
