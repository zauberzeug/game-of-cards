---
title: dod-rewrite-trailing-newline-reconstruction-is-inverted
summary: "`_apply_dod_rewrite` reconstructs the DoD text as `\"\\n\".join(lines) + (\"\\n\" if not dod_text.endswith(\"\\n\") else \"\")` — but the join never produces a trailing newline, so the condition is backwards: a newline-terminated DoD (the common block-scalar shape) loses its trailing newline, while a non-terminated one gains a spurious one. Currently MASKED because `_emit_block_field` rstrips trailing newlines on emit, so the written file is byte-identical either way. Unverified — no reproduce.py proving an observable difference."
status: open
stage: null
contribution: low
created: "2026-05-27T01:54:46Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, unverified]
definition_of_done: |
  - [ ] PROCESS: decide whether to fix the inverted condition or disprove as harmless given the emit-time rstrip masking. Record the verdict in log.md.
  - [ ] TDD: if fixed, a unit test on `_apply_dod_rewrite` (or the emitted text) showing the trailing-newline state matches the input's, for both newline-terminated and non-terminated `definition_of_done` inputs.
  - [ ] MECHANICAL: if fixed, promotion — drop the `unverified` tag once a reproduce.py shows a written-file difference attributable to this line (requires a code path where the emit-time rstrip does NOT run, or removing the masking).
---

# DoD-rewrite trailing-newline reconstruction is inverted

## Hypothesis (file:line)

`goc/engine.py:2704`, inside `_apply_dod_rewrite`:

```python
lines = dod_text.splitlines()
...
fm["definition_of_done"] = "\n".join(lines) + ("\n" if not dod_text.endswith("\n") else "")
```

`"\n".join(lines)` produces a string with **no** trailing newline,
regardless of the input. To faithfully restore the original trailing
state you would append `"\n"` exactly when `dod_text` **did** end in a
newline. The code does the opposite — it appends `"\n"` when the input
does **not** end in a newline:

- Input ends in `\n` (the common block-scalar DoD): condition
  `not dod_text.endswith("\n")` is `False` → no newline appended → the
  rejoined DoD **loses** its trailing newline.
- Input lacks a trailing `\n`: condition is `True` → a `\n` is appended
  → a spurious trailing newline is **added**.

Either branch sets the trailing-newline state to the inverse of the
input's.

## Why this is currently masked (and why it's `unverified`)

`_apply_dod_rewrite` writes the value through `emit_frontmatter`, whose
block-field emitter (`_emit_block_field`) `rstrip("\n")`s the scalar
before re-emitting it under a `|`-style block. So whatever trailing
newline this line produces (or drops) is normalized away on write, and
the file on disk is byte-identical either way. No user observes a
difference today — hence `unverified`, with no reproduce.py through a
public surface.

## Falsification / promotion recipe

Promote (drop `unverified`, file a real fix) only if a code path uses the
`fm["definition_of_done"]` value *without* routing it through
`_emit_block_field`'s rstrip — e.g. a future direct serialization, a diff
that compares the in-memory value, or removal of the emit-time
normalization. Otherwise disprove as harmless-but-inverted dead logic
(consider correcting the condition anyway as cheap correctness hygiene,
but it is not a behavioral defect today).

Surfaced by: audit-deck general-purpose hunter, 2026-05-27 (candidate #3 of 3).
