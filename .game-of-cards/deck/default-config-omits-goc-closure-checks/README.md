---
title: default-config-omits-goc-closure-checks
summary: "The shipped `.game-of-cards/config.yaml` leaves `layer_3_goc_dod` empty, so a fresh install's `goc attest` writes an empty Closure verification block and passes. The finish-card/card-schema guidance says GoC-wide checks such as DoD 100% and log closure are universal and recorded by attest."
status: done
stage: null
contribution: high
created: 2026-05-04
closed_at: 2026-05-05
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [x] `uv run python deck/default-config-omits-goc-closure-checks/reproduce.py` exits zero
  - [x] Fresh installs include default layer-3 GoC checks for `advanced-by-closed`, `dod-100-percent`, and `log-md-closure-entry`
  - [x] `goc attest` on a fresh install records non-empty Layer-3 results in `log.md`
  - [x] Regression coverage proves the packaged config template and self-hosted `.game-of-cards/config.yaml` contain the universal layer-3 checks
---

# default-config-omits-goc-closure-checks

## Location

- `goc/templates/game_of_cards/config.yaml:8`
- `.game-of-cards/config.yaml:8`
- `goc/templates/skills/card-schema/SKILL.md:197`
- `goc/templates/skills/finish-card/SKILL.md:24`
- `goc/engine.py:1429`
- `goc/engine.py:1438`
- `goc/engine.py:1444`

## What's broken

The shipped config template has no GoC-wide layer-3 checks:

```yaml
layer_3_goc_dod: []
```

The finish-card and card-schema guidance describe layer 3 as universal
and visible since the attestation work:

```markdown
Run `goc attest <title>` to record the Closure-verification block in `log.md` (layer-2 + layer-3 DoDs from `.game-of-cards/config.yaml`).
```

The engine already implements the derived checks:

```python
if name == "advanced-by-closed": ...
if name == "dod-100-percent": ...
if name == "log-md-closure-entry": ...
```

But fresh installs do not enable them, so `goc attest` can pass while
recording no layer-3 verification.

## Empirical evidence

Current output from `uv run python deck/default-config-omits-goc-closure-checks/reproduce.py`:

```text
install_exit=0
new_exit=0
attest_exit=0
config_has_dod_100=False
log_has_layer3=False
log_has_dod_100=False
log_has_log_check=False
attest_stdout_last_line=Attestation OK.
defect present: fresh install attestation passes with no layer-3 checks
```

## Why it matters

The closure-attestation card was about making implicit DoDs auditable.
With an empty default layer-3 config, the default installed methodology
records only an empty header:

```markdown
## Closure verification (2026-05-04)
```

That gives a false sense of closure rigor. Users must manually know the
hidden check names and edit config before `attest` does what the shipped
guidance says.

## Fix

Populate the default config template and this repo's self-hosted config
with the universal derived checks:

```yaml
layer_3_goc_dod:
  - name: advanced-by-closed
    kind: derived
  - name: dod-100-percent
    kind: derived
  - name: log-md-closure-entry
    kind: derived
```

Then update tests so a fresh install's `goc attest` records Layer-3
checks without the test manually rewriting config first.
