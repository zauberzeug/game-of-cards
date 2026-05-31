---
title: goc-attest-reports-ok-and-writes-empty-stub-when-no-checks-are-configured
summary: "`goc attest <title>` with both `layer_2_project_dod` and `layer_3_goc_dod` set to `[]` runs zero checks, prints `Attestation OK`, and still writes a bare `## Closure verification (TIMESTAMP)` header (no rows) to `log.md`. Subsequent calls append another empty header. The `log-md-closure-entry` derived check then sees a header and accepts closure as if attestation actually ran."
status: active
stage: null
contribution: medium
created: "2026-05-31T03:54:51Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, meta-fix]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero (defect no longer fires) — current behavior asserted, then re-asserted after the fix
  - [ ] MECHANICAL: `_cmd_attest` refuses to attest (or no-ops without mutating `log.md`) when both layer config arrays are empty / unset; the chosen behavior is documented in this card's `## Fix` section
  - [ ] TDD: a new regression test in `tests/` exercises empty-config attest and verifies log.md is untouched and the exit code matches the chosen contract
  - [ ] MECHANICAL: `goc validate` passes
  - [ ] PROCESS: `goc attest` ships its decision on whether "empty config" is an error or a no-op (one-line note in `_format_attestation_block` or a docstring)
worker: {who: "claude[bot]", where: main}
---

# `goc attest` reports OK and writes an empty closure-verification stub when no checks are configured

## Location

- `goc/engine.py:4115-4186` — `_cmd_attest`
- `goc/engine.py:4099-4112` — `_format_attestation_block`

## What's broken

When `.game-of-cards/config.yaml` has *both* layer arrays empty —

```yaml
layer_2_project_dod: []
layer_3_goc_dod: []
```

— `_cmd_attest` iterates the two layer keys at `engine.py:4129-4132`:

```python
for layer_key, layer_num in [("layer_2_project_dod", 2), ("layer_3_goc_dod", 3)]:
    layer_checks = config.get(layer_key) or []
    if not layer_checks:
        continue
    ...
```

Both layers `continue`. `results` stays `[]`. Execution then falls through
to the unconditional log-write at `engine.py:4176-4180`:

```python
log_path = card_dir / "log.md"
block = _format_attestation_block(today, results)
existing = log_path.read_text() if log_path.exists() else ""
log_path.write_text((existing.rstrip() + "\n\n" + block) if existing.strip() else block)
print(f"\nWrote attestation to {log_path}")
```

`_format_attestation_block` with an empty `results` list returns just
the header line:

```python
def _format_attestation_block(today: str, results: list[dict]) -> str:
    lines = [f"## Closure verification ({today})", ""]
    for layer_num, label in [(2, "Layer-2 (project DoD)"), (3, "Layer-3 (GoC DoD)")]:
        layer_results = [r for r in results if r["layer"] == layer_num]
        if not layer_results:
            continue
        ...
    return "\n".join(lines).rstrip() + "\n"
```

`any_failed` stays `False` so `_cmd_attest` prints `Attestation OK.` and
exits zero.

## Empirical evidence

Run on a scratch repo with `.game-of-cards/config.yaml` containing both
layers empty (see `reproduce.py`):

```
Wrote attestation to /tmp/attest_test/.game-of-cards/deck/sample-card/log.md

Attestation OK.
Next: goc done sample-card to close once all DoD items are ticked.
---LOG.MD---
## Closure verification (2026-05-31T03:54:20Z)
```

Calling `goc attest` a second time appends another bare header — log.md
grows on every invocation, each entry indistinguishable from a real
attestation that simply happened to find zero failures.

## Reachability

- A consumer drops `layer_3_goc_dod` (or sets it to `[]`) in their
  config because they want to defer to a custom closure flow.
- A fresh project that scaffolds its own config from scratch (the
  goc-shipped default at `goc/templates/game_of_cards/config.yaml`
  has `layer_2_project_dod: []` plus three layer-3 checks, but a
  consumer who customizes by replacement, not patch, can land here).
- A migration / repair tool that rewrites config with empty layer
  scaffolds before a human fills them in.

## Why it matters

The `layer_3_goc_dod` ships a `log-md-closure-entry` derived check
(see the default config) whose contract is "the card's `log.md`
contains a `## Closure verification` heading." Today's empty-stub
behavior *satisfies* that check with content that proves nothing —
the check finds the header `_cmd_attest` itself wrote. A consumer who
disables both layers is no longer protected against a downstream
closure check passing on attestation that never ran.

Even without that derived check, "Attestation OK" is a contract
violation when zero checks ran. Silent no-ops in a closure-verification
verb are the same failure mode this repo has filed a sibling family
for — see [bundled-closure-skips-configured-attestation-checks](../bundled-closure-skips-configured-attestation-checks/),
[goc-attest-mutates-log-md-on-already-closed-cards](../goc-attest-mutates-log-md-on-already-closed-cards/),
[goc-attest-silently-ignores-unknown-skip-names](../goc-attest-silently-ignores-unknown-skip-names/).

## Fix

Two credible mechanisms; the card is `--gate none` because the choice
is small and either is acceptable:

1. **Refuse to attest** — at `engine.py:4129-4132`, after both loops
   skip, if `results == []` print
   `ERROR: no closure checks configured (layer_2_project_dod and layer_3_goc_dod are both empty)`
   to stderr and exit non-zero, without touching `log.md`.
2. **No-op without writing** — same condition, but print
   `Nothing to attest (no checks configured).` and exit zero, again
   without touching `log.md`.

Mechanism (1) is consistent with `goc done`'s general posture of
"refuse to close when prerequisites are unmet"; mechanism (2) is more
lenient and matches `goc move`'s "if there's nothing to do, say so."
The implementer picks one and notes the choice in the docstring; the
DoD's regression test asserts whichever was chosen.

The fix is single-site (around `engine.py:4126-4180`) plus a regression
test under `tests/`.
