---
title: pattern-generalization-hook-enable-regex-misses-capitalized-and-yes-yaml-booleans
summary: "`_enabled()` in the pattern-generalization Stop hook matched only lowercase `true`, so opting in with any other YAML-true spelling (`True`, `TRUE`, `yes`, ...) silently left the hook disabled — intended-on quietly became actually-off. Fixed to accept every spelling the engine's own `yaml_lite` coerces to True, converging with the already case-insensitive OpenClaw port and covered by a regression test."
status: done
stage: null
contribution: low
created: "2026-06-29T02:44:58Z"
closed_at: "2026-06-30T01:20:15Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [x] `_enabled()` in `goc/templates/hooks/pattern_generalization_check.py` enables the hook for every YAML-true spelling the engine's own `yaml_lite` coerces to True: `true`, `True`, `TRUE`, `yes`, `Yes`, `YES`.
  - [x] `false`/absent/absent-key still leave the hook disabled (opt-in default off preserved).
  - [x] Regression test added covering the capitalized + `yes` spellings.
  - [x] `reproduce.py` prints PASS after the fix.
  - [x] Plugin mirrors re-synced (`sync_plugin_assets.py --check` green); cross-host divergence with `openclaw-plugin/index.ts:474` (already case-insensitive) noted/resolved.
worker: {who: "claude[bot]", where: main}
---

# Pattern-generalization hook enable-regex only matches lowercase `true`

## Problem

`_enabled()` decides whether the opt-in pattern-generalization self-check
runs by matching `.game-of-cards/config.yaml` against
(`goc/templates/hooks/pattern_generalization_check.py:97-100`):

```python
m = re.search(
    r"pattern_generalization_check\s*:\s*(false|true)", config.read_text()
)
return bool(m and m.group(1) == "true")
```

The regex only matches lowercase `true`, and the comparison is the exact
literal `"true"`. So a user who enables the hook with any other
YAML-canonical boolean-true spelling — `True`, `TRUE`, `yes`, `Yes`, `YES`
— gets it silently left **disabled**, with no error and no signal.

This is a code-vs-code inconsistency: the repo's own `yaml_lite` parser (and
PyYAML/ruamel) coerce all of those spellings to `True`. The sibling hook
`deck_session_start.py` already defines a `_TRUE_SET`
(`("true","True","TRUE","yes","Yes","YES")`) for exactly this reason — this
hook ignores that precedent.

## Why it matters

Reachability path: any consumer who opts into the hook by writing the
perfectly valid `pattern_generalization_check: True` (the spelling most YAML
authors reach for) ends up with the feature off while believing it on. The
opt-out default-off contract still holds for `false`/absent, so the failure
is silent in the worst direction (intended-on → actually-off).

Cross-host divergence (corroborating, not the primary claim): the OpenClaw
TS port at `openclaw-plugin/index.ts:474` uses a **case-insensitive** regex
(`/pattern_generalization_check\s*:\s*true/i`), so `True`/`TRUE` enable the
hook on OpenClaw but NOT on Claude Code/Codex from identical config —
though `yes` still fails everywhere. The Python fix should converge the two
hosts on the same accepted-spelling set.

## Reproduction (observed during audit, to be captured in `reproduce.py`)

Loading the actual hook module against a config that sets each spelling:

```
true   -> _enabled=True
True   -> _enabled=False   <-- BUG (yaml_lite parses this as True)
TRUE   -> _enabled=False   <-- BUG
yes    -> _enabled=False   <-- BUG
Yes    -> _enabled=False   <-- BUG
YES    -> _enabled=False   <-- BUG
```

## Proposed fix

Normalize the matched token before comparing — reuse the `_TRUE_SET`
spellings the sibling `deck_session_start.py` already standardizes on (case
plus the `yes` family), e.g. extend the alternation to
`(false|true|yes|...)` with case-insensitivity and test membership in the
true-set rather than against the single literal `"true"`. Keep `false`
(and any unrecognized value) disabling the hook. Edit the **template**
(`goc/templates/hooks/...`) so the sync regenerates the four mirrors; align
the OpenClaw TS regex with the same accepted set.

## Dedup

Closest existing card: `pattern-generalization-opt-out-regex-misses-quoted-yaml-values`
(open) — a *distinct* defect about surrounding quote characters
(`"false"` / `'false'`) on the now-superseded opt-*out* code; its body
never mentions capitalization or the `yes`/`True` spellings. The
`pattern-generalization-mutation-detector-*` cards are about git-command
tokenizing and are unrelated. This capitalization/YAML-1.1-boolean gap on
the current opt-*in* check is previously undocumented.
