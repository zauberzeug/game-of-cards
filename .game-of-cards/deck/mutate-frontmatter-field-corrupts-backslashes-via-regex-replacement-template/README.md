---
title: mutate-frontmatter-field-corrupts-backslashes-via-regex-replacement-template
summary: "`mutate_frontmatter_field` interpolates `new_value` into the *replacement* argument of `re.sub` (goc/engine.py:336), which interprets backslash escapes. Combined with `_yaml_inline`'s `\\`→`\\\\` quoting, any value containing a backslash is silently corrupted on round-trip — live via `quality-pass --llm` summary rewrites and `worker` rewrites. Same root-cause shape as the closed install.py card, whose sibling sweep missed this engine site."
status: active
stage: null
contribution: medium
created: "2026-05-26T23:59:41Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero — values containing backslashes (Windows paths, regex-backreference text) round-trip through `mutate_frontmatter_field` unchanged.
  - [ ] MECHANICAL: `goc/engine.py:336` no longer passes `new_value` as the `re.sub` *replacement template*; the replacement is made opaque (callable `lambda _: f"{field_name}: {new_value}"`, or equivalent literal-replacement form).
  - [ ] TDD: existing single-line and block-field replacement behavior is unchanged for escape-free values (the `_apply_summary_rewrite`, `worker`, `status`/`closed_at`, and `human_gate` callers still mutate correctly).
  - [ ] PROCESS: plugin mirrors re-synced (`python scripts/sync_plugin_assets.py --check` clean) and `goc validate` clean, since `engine.py` is vendored into the plugin payloads.
worker: {who: "claude[bot]", where: main}
---

# mutate_frontmatter_field corrupts values containing backslashes

## Location

- `goc/engine.py:336` — `fm_text = pattern.sub(f"{field_name}: {new_value}", fm_text, count=1)`

Live callers that feed externally-authored text through this helper:

- `goc/engine.py:2681` — `_apply_summary_rewrite`: `mutate_frontmatter_field(text, "summary", _yaml_inline(new_summary))` (the `goc quality-pass --llm` summary-rewrite path; `new_summary` is LLM-authored).
- `goc/engine.py:3468` — `worker` rewrite: `mutate_frontmatter_field(text, "worker", worker_yaml)` where `worker_yaml` is built from `_yaml_inline(who)` / `_yaml_inline(where)` (free-form worker identifier / branch context).

## What's broken

`re.sub(pattern, repl, string)` interprets the *replacement* argument
`repl` for backslash sequences (`\g<name>`, `\1`, `\\`→literal `\`).
`mutate_frontmatter_field` builds `repl` directly from caller data:

```python
fm_text = pattern.sub(f"{field_name}: {new_value}", fm_text, count=1)
```

The contract is supposed to be a verbatim field replacement (the
docstring says "Line-anchored regex replacement of `field: <whatever>`"),
but `<whatever>` is not treated verbatim — it is a regex replacement
template.

The corruption is *silent* (not a crash) precisely because of the
emitter's quoting. `_yaml_inline` (`goc/engine.py:229`) escapes a value
for double-quoted YAML by doubling backslashes:

```python
escaped = s.replace("\\", "\\\\").replace('"', '\\"')
return f'"{escaped}"'
```

So for `C:\Users` it correctly emits `"C:\\Users"`. But that doubled
backslash is then passed as the `re.sub` replacement, which collapses
`\\`→`\`, so the file is *written* as `"C:\Users"`. The vendored parser
`_parse_double_quoted` (`goc/_vendor/yaml_lite.py:289`) then un-escapes
`\U`→`U` (unknown escapes drop the backslash), yielding `C:Users`.
Net: a clean double-escape becomes a single-escape becomes corruption.

The field-absent branch (`goc/engine.py:334`) uses an f-string append,
not `re.sub`, so it is unaffected — only the replacement branch corrupts.

## Empirical evidence

```
case 1 (summary with backslashes):
  original   : 'path C:\\Users\\foo and a \\n literal'
  round-trip : 'path C:Usersfoo and a \n literal'
  OK?        : False
case 2 (summary with regex-backreference text):
  original   : 'backref \\g<1> and group \\1'
  round-trip : 'backref g<1> and group 1'
  OK?        : False

FAIL: 2 value(s) did not round-trip through mutate_frontmatter_field
```

(In case 1 the `\n` in the round-trip repr is a real newline injected by
the parser; in case 2 the `\g<1>` / `\1` backreference markers are eaten.)

## Why it matters

The summary-rewrite path is LLM-driven (`quality-pass --llm`), so a
model that proposes a summary mentioning a Windows path, a regex, or a
LaTeX-ish token writes a corrupted summary back to disk with no error.
The `worker` path takes free-form identifiers. Both are realistic
backslash carriers. Unlike a crash, nothing flags the loss.

## Same root-cause family — and the missed sibling

This is the same `re.sub`-replacement-template hazard documented (and
fixed for `install.py`) by the closed card
[append-marker-block-treats-briefing-text-as-regex-replacement-template](../append-marker-block-treats-briefing-text-as-regex-replacement-template/).
That card's MECHANICAL DoD enumerated "ALL sibling sites: lines 222,
884, 1040" — but all three are in `goc/install.py`; its sweep did not
reach `goc/engine.py:336`. Two differences make this site worse than
those: (1) the install.py sites are latent (escape-free templates) while
this one has live callers, and (2) those sites would *crash*
(`re.error` / `IndexError`) on a stray backslash, whereas the
`_yaml_inline` pre-escaping here suppresses the crash and turns it into
*silent* corruption.

Fixing the single helper at `goc/engine.py:336` cures every caller at
once (summary, worker, status, closed_at, human_gate), so this is one
helper-level bug rather than a multi-site family needing a meta-fix.

## Fix

Make the replacement opaque, exactly as the install.py card did:

```python
fm_text = pattern.sub(lambda _: f"{field_name}: {new_value}", fm_text, count=1)
```

A callable replacement is not parsed for backreferences, so `new_value`
lands verbatim. **Do NOT apply the fix as part of filing this card.**
