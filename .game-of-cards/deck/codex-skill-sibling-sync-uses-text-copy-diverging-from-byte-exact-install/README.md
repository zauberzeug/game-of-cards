---
title: codex-skill-sibling-sync-uses-text-copy-diverging-from-byte-exact-install
summary: "`_sync_codex_skill_tree` copies non-`SKILL.md` sibling assets through a text round-trip (`read_text()` → `write_text()` at sync_plugin_assets.py:380,383), which LF-normalizes line endings. Every other mirror path copies siblings byte-for-byte: `goc install` via `shutil.copy2`, the OpenClaw porter, and the Claude dir-sync. So a CRLF (or otherwise text-round-trip-sensitive) sibling asset lands byte-exact via `goc install --codex` but LF-normalized in `.codex/skills/` and `codex-plugin/skills/` — and `_check_codex_skill_tree` compares text-to-text, so CI cannot detect the skew. Latent today (the one shipped sibling, `card-schema/schema.yaml`, is ASCII-LF)."
status: active
stage: null
contribution: low
created: "2026-06-10T04:40:20Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [ ] TDD: `deck/<title>/reproduce.py` shows `shutil.copy2` and `read_text()`→`write_text()` producing different bytes for a CRLF sibling (the copy-mode divergence)
  - [ ] MECHANICAL: `_sync_codex_skill_tree` copies non-`SKILL.md` siblings byte-for-byte (e.g. `shutil.copy2`), matching `goc install`, the OpenClaw porter, and the Claude dir-sync
  - [ ] MECHANICAL: `_check_codex_skill_tree` compares siblings byte-for-byte so install-vs-mirror skew is CI-detectable
  - [ ] PROCESS: `python scripts/sync_plugin_assets.py --check` passes and the dogfooded `.codex/skills/` + `codex-plugin/skills/` mirrors are byte-identical to a `goc install --codex` of the same templates
  - [ ] PROCESS: `uv run goc validate` passes
worker: {who: "claude[bot]", where: main}
---

# Codex skill-sibling sync uses text copy, diverging from byte-exact `goc install`

## Location

- `scripts/sync_plugin_assets.py:377-384` — `_sync_codex_skill_tree`. Line
  380 reads a non-`SKILL.md` sibling via `src_item.read_text()`; line 383
  writes it via `dst_item.write_text(expected)` — a universal-newline text
  round-trip.
- `scripts/sync_plugin_assets.py:404-424` — `_check_codex_skill_tree`. Line
  423 compares `dst_item.read_text() != expected` — the same text lens, so
  it cannot see a byte-level newline skew.
- Contrast `goc/install.py` `_sync_skill_tree` (siblings fall through to
  `shutil.copy2`, byte-exact), `scripts/port_skills_to_openclaw.py`
  `port_sibling` (`shutil.copy2`), and `_sync_dir` in this same file
  (`scripts/sync_plugin_assets.py:276,324`, `shutil.copy2`).

## What's broken

`_sync_codex_skill_tree` is the only mirror path that round-trips sibling
assets through text decode/encode:

```python
expected = (
    _codex_skill_text(src_item, skill_name=rel.parts[0])
    if src_item.name == "SKILL.md"
    else src_item.read_text()          # <-- text round-trip for siblings
)
if not dst_item.exists() or dst_item.read_text() != expected:
    dst_item.write_text(expected)      # <-- re-encodes with os.linesep / \n
```

`Path.read_text()` applies universal-newline decoding and `write_text()`
re-encodes, so `\r\n` → `\n`. The byte-exact path that this mirror is
meant to reproduce — what a consumer's `goc install --codex` writes — uses
`shutil.copy2` and preserves the original bytes.

## Empirical evidence

`deck/<title>/reproduce.py` copies a CRLF sibling through both modes:

```
source bytes        : b'key: value\r\nother: thing\r\n'
goc install (copy2) : b'key: value\r\nother: thing\r\n'
codex sync (text)   : b'key: value\nother: thing\n'

DEFECT CONFIRMED: the Codex sibling sync LF-normalizes a CRLF
asset that `goc install --codex` preserves byte-for-byte. ...
```

## Why it matters

The dogfooded `.codex/skills/` and `codex-plugin/skills/` trees are
supposed to be byte-identical to what a consumer's `goc install --codex`
produces — that is the whole point of the sync + `--check` tripwire. For
any sibling asset whose bytes survive a text round-trip unchanged (today's
single ASCII-LF `card-schema/schema.yaml`) the defect is **latent**. It
activates the moment a sibling with CRLF (or any text-round-trip-sensitive
bytes) is added to a Codex-eligible skill dir: the mirror silently diverges
from the install output, and because `_check_codex_skill_tree` compares
through the same text lens, `--check` stays green and CI cannot catch it.
This is the inverse-fidelity sibling of
[install-marker-merge-rewrites-crlf-briefing-files-to-lf](../install-marker-merge-rewrites-crlf-briefing-files-to-lf/)
and distinct from
[openclaw-skill-porter-drops-sibling-asset-files-from-skill-directories](../openclaw-skill-porter-drops-sibling-asset-files-from-skill-directories/)
(missing siblings, not newline fidelity).

## Fix

Switch the sibling branch in `_sync_codex_skill_tree` to byte-exact copy
(`shutil.copy2(src_item, dst_item)` for non-`SKILL.md` files), matching the
other three mirror paths, and make `_check_codex_skill_tree` compare
siblings by bytes (`dst_item.read_bytes() != src_item.read_bytes()`) so the
tripwire detects install-vs-mirror skew. `SKILL.md` keeps the
`_codex_skill_text` frontmatter-normalization path. Mechanical, single-site,
no contract choice — hence `human_gate: none`.
