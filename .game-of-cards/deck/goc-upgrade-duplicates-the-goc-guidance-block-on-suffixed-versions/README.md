---
title: goc-upgrade-duplicates-the-goc-guidance-block-on-suffixed-versions
summary: "`GOC_BEGIN_RE = re.compile(r\"<!-- BEGIN GOC v[\\d.]+ -->\")` matches only digits and dots, but `__version__` is a PEP 440 string that can carry letters (`.post1`, `.dev101`, `rc1`, `+local`). When the on-disk marker is suffixed, `_append_marker_block` can't find it and APPENDS a second GoC block instead of replacing in place — breaking the marker-bounded-merge idempotency contract. Hits every non-release build (editable/`uv run` source installs, pre-releases), i.e. the dogfood path; tagged releases report bare X.Y.Z and are unaffected."
status: active
stage: null
contribution: medium
created: "2026-05-26T22:38:59Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero — calling `_append_marker_block`
        twice with a suffixed version (e.g. `0.0.20.post1.dev101`)
        leaves exactly ONE BEGIN-GOC marker in the file.
  - [ ] TDD: the broadened regex matches every PEP 440 form
        (`1.2.3`, `1.2.3.post1`, `1.2.3.dev5`, `1.0.0rc1`, `2.0.0+local`)
        and still does NOT match the unrelated `<!-- BEGIN GOC IMPORT -->`
        marker.
  - [ ] MECHANICAL: the fix lands in `goc/templates/...`/`goc/install.py`
        source-of-truth (the engine is vendored into the plugin payloads);
        plugin mirrors re-sync and `python scripts/sync_plugin_assets.py
        --check` passes.
  - [ ] PROCESS: `uv run goc validate` is clean and the existing
        version-surface tests still pass.
worker: {who: "claude[bot]", where: main}
---

# `goc upgrade` duplicates the GoC guidance block on suffixed versions

## Location

`goc/install.py:31` — the marker regex. Downstream impact at
`goc/install.py:882-886` (`_append_marker_block`), and shared by
`_strip_goc_block` (`install.py:168`) and
`_detect_briefing_targets_on_disk` (`install.py:154`).

## What's broken

The BEGIN-marker regex only matches digits and dots:

```python
GOC_BEGIN = f"<!-- BEGIN GOC v{__version__} -->"   # line 30 — writer
GOC_BEGIN_RE = re.compile(r"<!-- BEGIN GOC v[\d.]+ -->")  # line 31 — matcher
```

`__version__` is a PEP 440 version string. On any non-release build it
carries letters: hatch-vcs `git describe` yields `.postN.devM` for
editable/`uv run` source installs, pre-releases are `rcN`/`aN`/`bN`,
local builds add `+local`. The marker WRITTEN to disk then contains
characters (`p`, `o`, `s`, `t`, `d`, `e`, `v`, `r`, `c`, `+`) that the
character class `[\d.]+` cannot match.

`_append_marker_block` relies on the regex to find-and-replace an
existing block:

```python
    pattern = re.compile(rf"{GOC_BEGIN_RE.pattern}.*?{re.escape(GOC_END)}\n?", re.DOTALL)
    if pattern.search(text):
        target.write_text(pattern.sub(lambda _: block, text))
        return
    target.write_text(text.rstrip() + "\n\n" + block)   # line 886 — append
```

When the on-disk marker is suffixed, `pattern.search(text)` returns
`None`, so the code falls into the append branch (line 886) and writes
a **second** GoC block — violating the marker-bounded-merge idempotency
contract documented in AGENTS.md ("rewrites only the content between the
markers; content above or below is preserved"). The same broken regex
makes `_strip_goc_block` and `_detect_briefing_targets_on_disk`
silently no-op on a suffixed install.

## Empirical evidence

```
version: 0.0.20.post1.dev101
marker : <!-- BEGIN GOC v0.0.20.post1.dev101 -->
matches: False
  1.2.3                     -> True
  1.2.3.post1               -> False
  0.0.20.post1.dev101       -> False
  1.0.0rc1                  -> False
  2.0.0+local               -> False
```

Run `uv run python deck/goc-upgrade-duplicates-the-goc-guidance-block-on-suffixed-versions/reproduce.py`
for the full append-twice → two-markers demonstration.

## Why it matters

Released wheels report bare `X.Y.Z` (the release workflow rewrites the
version literals), so production consumers on a tagged release are not
hit. But the breakage lands squarely on the dogfood path this repo runs
every day — editable installs and `uv run` report a `.postN.devM`
version — and on anyone trying a pre-release. A second `goc upgrade`
duplicates the entire guidance block in their AGENTS.md / CLAUDE.md, and
the briefing-migration strip silently stops working.

## Fix

Broaden `GOC_BEGIN_RE` to match a full PEP 440 version token rather than
just `[\d.]+` — e.g. `r"<!-- BEGIN GOC v[^>]+? -->"` or a
PEP-440-shaped pattern. Keep it from colliding with the distinct
`<!-- BEGIN GOC IMPORT -->` marker (`CLAUDE_IMPORT_BEGIN`). Verify
idempotency holds across all PEP 440 forms. **Do NOT apply the fix
here — this card is the briefing.**
