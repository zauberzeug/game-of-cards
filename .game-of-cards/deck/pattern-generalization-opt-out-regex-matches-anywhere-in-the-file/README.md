---
title: pattern-generalization-opt-out-regex-matches-anywhere-in-the-file
summary: "The pattern-generalization Stop hook's opt-out check parses `.game-of-cards/config.yaml` with `re.search(r\"pattern_generalization_check\\s*:\\s*(false|true)\", ...)`. The regex is unanchored to YAML structure, so any literal occurrence of `pattern_generalization_check: false` — under an unrelated parent key, inside a quoted scalar value, or inside a YAML comment — silently opts the entire repo out of the Stop reminder. Sibling defect to `pattern-generalization-opt-out-regex-misses-quoted-yaml-values`; same root cause (regex instead of YAML parsing)."
status: open
stage: null
contribution: medium
created: "2026-05-30T07:22:05Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [ ] PROCESS: Decision recorded in the body's `## Decision required` section (regex-anchor vs YAML-parse, and whether to bundle with the sibling card) and gate lowered to `none`.
  - [ ] TDD: `reproduce.py` exits zero — all three non-key occurrences are recognized as NOT opt-out, the real `hooks:` block setting wins.
  - [ ] MECHANICAL: the fix lands in `goc/templates/hooks/pattern_generalization_check.py` and the three mirrors are re-synced (pre-commit `sync-plugin-assets` covers `.claude/hooks/`, `claude-plugin/hooks/`, `codex-plugin/hooks/`).
  - [ ] TDD: a regression test under `tests/` exercises `_opted_out` against the three over-match shapes (unrelated-parent, quoted-scalar, comment) and asserts `False` for each.
  - [ ] TDD: `uv run goc validate` passes and `uv run python -m unittest discover -s tests` is green.
---

# Pattern-generalization opt-out regex matches anywhere in the file

## Location

`goc/templates/hooks/pattern_generalization_check.py:33-43`

```python
def _opted_out(project_dir: str) -> bool:
    config = Path(project_dir) / ".game-of-cards" / "config.yaml"
    if not config.exists():
        return False
    try:
        m = re.search(
            r"pattern_generalization_check\s*:\s*(false|true)", config.read_text()
        )
        return bool(m and m.group(1) == "false")
    except OSError:
        return False
```

## What's broken

The opt-out check uses `re.search` with a pattern that has no
anchoring to YAML structure. The regex matches the literal string
`pattern_generalization_check: false` *anywhere* in the file —
regardless of whether that occurrence is actually the hook's
configuration key.

The docstring at the top of the same file documents the intended
format as:

```yaml
hooks:
  pattern_generalization_check: false
```

— a key under the `hooks:` mapping. But because `re.search` walks
the whole file looking for any substring match, *any* of the
following silently opt the entire repo out of the Stop reminder:

1. **Under an unrelated parent key.** A `notes:` or `description:`
   block-string that warns contributors against the setting — the
   warning's own text triggers opt-out:

   ```yaml
   notes: |
     Reminder for new contributors: do not set
     pattern_generalization_check: false
     in this repo's config — we want the Stop reminder on every turn.

   hooks:
     pattern_generalization_check: true
   ```

   The intent is the opposite of what the file produces.

2. **Inside a quoted scalar value.** A `description:` line that
   mentions the setting in prose triggers opt-out:

   ```yaml
   description: "Set pattern_generalization_check: false to silence the Stop hook."

   hooks:
     pattern_generalization_check: true
   ```

3. **Inside a YAML comment.** A comment retained from a prior
   experiment triggers opt-out:

   ```yaml
   # Historically we tried pattern_generalization_check: false here;
   # we now leave the hook on for every code-mutating turn.
   hooks:
     pattern_generalization_check: true
   ```

In all three cases the actual `hooks:` block sets the key to
`true`, so the correct verdict is `_opted_out() -> False` (the
hook should fire on every code-mutating turn). The current
implementation returns `True` for all three: the first lexical
match anywhere in the file decides.

## Empirical evidence

`reproduce.py` writes the three configs above and calls
`_opted_out` on each:

```
[FAIL] under_unrelated_parent_key: _opted_out() -> True (expected False)
[FAIL] inside_quoted_scalar_value: _opted_out() -> True (expected False)
[FAIL] inside_yaml_comment: _opted_out() -> True (expected False)

DEFECT REPRODUCED: 3/3 non-key occurrences silently opt the repo out: ['under_unrelated_parent_key', 'inside_quoted_scalar_value', 'inside_yaml_comment']
```

The script exits 1; the fix will turn it to exit 0.

## Why it matters

The Stop hook is the runtime nudge that asks the agent to file a
generalization card when its change is an instance of a broader
pattern (Andon-style self-assessment, see
`goc/templates/hooks/pattern_generalization_check.py:25-30`). It
fires on *every* code-mutating turn for *every* consumer of the
plugin. Getting opt-out wrong in the over-match direction is a
**silent feature-killer**: the hook never runs in repos whose
config happens to contain the literal substring for any reason
(documentation, comment, warning, copy-paste of upstream prose),
and there is no diagnostic — the hook simply stops nudging.

Reachability path: every Stop event in any consumer Claude Code
repo executes this hook (configured by `goc install` /
`goc upgrade` in `.claude/settings.json` under the `Stop` event).
The hook reads the consumer's own `.game-of-cards/config.yaml`,
which is user-edited and may contain documentation, comments, or
descriptive prose alongside the actual configuration. Any such
content with the matching substring silently disables the hook
for every code-mutating turn thereafter.

This is a sibling defect to
[pattern-generalization-opt-out-regex-misses-quoted-yaml-values](../pattern-generalization-opt-out-regex-misses-quoted-yaml-values/),
which documents the *under-match* failure (quoted-scalar opt-out
values are not recognized). Both defects share the same root
cause — parsing a structured format with an unanchored regex —
and the proper fix (parse the file as YAML and look up
`hooks.pattern_generalization_check` as a structured lookup)
resolves both at once.

## Decision required

The fix mechanism is shared with the sibling card; the human
should pick one path here that resolves both:

1. **Anchor the regex more tightly** (e.g. require start-of-line
   indent + the literal key followed by structure). Tightens the
   over-match but still requires a separate fix for the sibling's
   under-match, and is fragile against any YAML formatting drift.
2. **Parse the file as YAML and do a structured lookup of
   `hooks.pattern_generalization_check`.** The vendored YAML
   parser in `goc/engine.py` is available; using it inside the
   hook makes both this card and the sibling collapse into one
   fix. Slightly heavier per-event cost (full-file YAML parse on
   every Stop event), but the file is small.
3. **Strip comments + parse with `yaml.safe_load` if available,
   else fall back to a tightened regex.** Belt-and-braces. More
   code; same effective semantics as (2) when PyYAML is present.

Also: should this card and
`pattern-generalization-opt-out-regex-misses-quoted-yaml-values`
be merged into one filing, or kept as siblings with one fix
landing under one and a forward pointer from the other?
