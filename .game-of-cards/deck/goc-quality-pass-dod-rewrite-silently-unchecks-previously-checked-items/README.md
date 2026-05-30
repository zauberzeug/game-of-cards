---
title: goc-quality-pass-dod-rewrite-silently-unchecks-previously-checked-items
summary: "`_apply_dod_rewrite` (engine.py:3068) hardcodes `- [ ]` when reconstructing a DoD item whose LLM-proposed `fix` text lacks an explicit checkbox prefix. The documented LLM contract (in `_QUALITY_PROMPT_TEMPLATE` at engine.py:2937) asks for `fix: \"rewrite...\"` — just the body text — so a fix accepted for a previously-checked `- [x]` item silently flips it to `- [ ]`. Attested completion is erased, and the card's close-readiness drops without any user-visible signal."
status: open
stage: null
contribution: medium
created: "2026-05-30T06:37:45Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] TDD: `deck/<title>/reproduce.py` constructs a card with DoD `- [x] item zero` + `- [ ] item one`, drives `_apply_dod_rewrite` with a verdict targeting `idx: 0` whose `fix` is bare text (no checkbox prefix), and asserts the resulting line is `- [x] <new text>` (state preserved) — not `- [ ] <new text>`
  - [ ] Decide the fix path (see `## Decision required`) and implement it in `goc/engine.py`
  - [ ] EMPIRICAL: rerun reproduce.py against the patched engine; expected output recorded in the body's "Empirical evidence" section
  - [ ] PROCESS: a regression test in `tests/` exercises the preserved-checkbox-state invariant
  - [ ] `uv run goc validate` passes
---

# `goc quality-pass --llm` DoD rewrite silently unchecks previously-checked items

## Location

- `goc/engine.py:3068-3085` — `_apply_dod_rewrite`. Line 3082 unconditionally
  prepends `- [ ]` whenever the LLM's `fix` payload does not start with
  `- [`.
- `goc/engine.py:2937-2981` — `_QUALITY_PROMPT_TEMPLATE`. Documents the
  `fix` field as the rewritten *text* (not a full markdown line), so the
  LLM legitimately returns bare body strings.

## What's broken

`_apply_dod_rewrite` reconstructs each rewritten DoD line as:

```python
new_text = fix_by_idx[box_idx]
new_text = new_text.lstrip()
if not new_text.startswith("- ["):
    new_text = f"- [ ] {new_text}"
lines[line_idx] = new_text
```

The branch at `engine.py:3081-3082` hardcodes the unchecked-box prefix
`- [ ]`, regardless of whether the original line was `- [ ]` or `- [x]`.
The LLM prompt teaches the model to return only the rewrite text — see
the documented schema at `engine.py:2964`:

```
For each item that's NOT verifiable, return
{idx: N (0-based), issue: "...", fix: "rewrite..."}.
```

The prompt never requests a checkbox prefix in `fix`, so a well-behaved
LLM returns bare text. The rewriter then writes `- [ ] <new text>` to
every accepted item — silently flipping `[x]` → `[ ]` whenever the
original was checked.

## Empirical evidence

Direct call into the engine, constructed card with one checked +
one unchecked DoD item, verdict targeting the checked one (idx 0)
with a bare-text fix (as the LLM emits per the prompt schema):

```
BEFORE DoD:
- [x] item zero was already done
- [ ] item one is open

AFTER README:
...
definition_of_done: |
  - [ ] item zero meets metric Y across N trials
  - [ ] item one is open
...
```

The previously-checked `[x]` is gone — replaced with `[ ]`. No
confirmation prompt distinguishes "rewriting wording" from "resetting
attested completion."

## Why it matters

The reachable consumer flow is `goc quality-pass --llm` →
`_apply_verdict_interactive` (`engine.py:3088-3138`) → user (or
`--auto-yes`) accepts the DoD fix → `_apply_dod_rewrite` writes the
README. A card whose `- [x]` items represent prior attestation (manual
edits, `goc attest`, or `goc done` mid-flight checkmarks) loses that
state on the very first quality-pass rewrite that touches a checked
item. Symptoms a future reader sees:

- DoD progress counter (e.g. `4/6`) silently drops by one or more.
- `goc done` refuses to close a card that *was* close-ready, because
  the previously-attested item is now unchecked.
- The closure log loses any breadcrumb of the prior attestation —
  log.md only records the quality-pass rewrite acceptance, not that
  a `[x]` was rebuilt as `[ ]`.

Adjacent card `dod-rewrite-box-index-skips-uppercase-checked-boxes`
fixed the misaligned box-counter; this card targets a separate
defect in the same rewriter: even with the indices correct, the
state is not preserved when the LLM omits the prefix.

## Fix — see `## Decision required` below

## Decision required

Two credible fix paths:

**Option A — preserve original checkbox state in the rewriter.**
Capture the original `[ ]` / `[x]` / `[X]` token from
`lines[line_idx]` before substitution and re-emit the same token in
the reconstructed line. Tolerates LLM payloads that include OR omit
the checkbox prefix; the latter case keeps the original state instead
of forcing unchecked. Code change is local to `_apply_dod_rewrite`
(~5 lines). Disadvantage: when the LLM intentionally returns a
checkbox prefix that differs from the original (rare, but possible
for `- [ ]` → `- [x]`), this option overrides the LLM's choice.

**Option B — change the LLM contract to require the full line.**
Update `_QUALITY_PROMPT_TEMPLATE` so `fix` must include the markdown
checkbox prefix (`- [ ] ...` or `- [x] ...`), and have the LLM
explicitly copy the original state through. Make `_apply_dod_rewrite`
reject bare-text `fix` payloads with a clear error. Disadvantage:
breaks any caller that already drives quality-pass with bare-text
fixes (script users, the existing test corpus). Larger change,
prompt-engineering risk that the LLM still occasionally omits the
prefix.

Recommendation: **Option A** — defensive in the rewriter, no LLM
contract change, no test breakage. The rewriter already special-cases
the prefix-present branch, so preserving original state when the
prefix is absent is the natural generalization.

Once decided, lower the gate via `Skill(decide-card)` and implement.
