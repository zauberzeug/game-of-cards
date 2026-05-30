---
title: attest-cmd-as-string-fails-with-misleading-single-character-not-found-error
summary: "`_run_automated_check` reads `layer_2_project_dod[*].cmd` from `.game-of-cards/config.yaml` and passes it to `subprocess.run` without `shell=True`. A user who writes the natural YAML shorthand `cmd: \"pytest -q\"` (scalar string) hits `FileNotFoundError`, and the handler at `goc/engine.py:3758` formats the error as `f\"command not found: {cmd[0]}\"` — for a string, `cmd[0]` is the FIRST CHARACTER, so the message reads `command not found: p`. The contract that `cmd` must be a token list is undocumented in the template config and unvalidated in `load_deck_config`."
status: open
stage: null
contribution: medium
created: "2026-05-30T11:24:11Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract, documentation]
definition_of_done: |
  - [ ] TDD: `.game-of-cards/deck/attest-cmd-as-string-fails-with-misleading-single-character-not-found-error/reproduce.py` exits zero after the fix (today it exits 1).
  - [ ] MECHANICAL: `goc/engine.py:_run_automated_check` no longer indexes `cmd[0]` against a string — either reject scalar-string `cmd` at load time with a clear shape error, or render the missing-cmd message from the original `cmd` value regardless of type.
  - [ ] MECHANICAL: `goc/templates/game_of_cards/config.yaml` shows at least one commented-out `layer_2_project_dod` example demonstrating the list shape (e.g. `cmd: ["pytest", "-q"]`).
  - [ ] TDD: a regression test under `tests/` exercises `_run_automated_check` (or `_cmd_attest`) with a scalar-string `cmd` and asserts the user sees the chosen contract — either a shape-validation error citing the cmd, or a `command not found: <full cmd>` message.
  - [ ] PROCESS: `uv run python -m unittest discover -s tests` is green; `uv run goc validate` is clean.
---

# `goc attest` reports `command not found: p` when a YAML scalar string is used for `cmd`

## Location

`goc/engine.py:3751-3763` — `_run_automated_check(check: dict)`:

```python
def _run_automated_check(check: dict) -> tuple[bool, str]:
    cmd = check["cmd"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, cwd=str(REPO_ROOT), check=False)
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT (>300s)"
    except FileNotFoundError:
        return False, f"command not found: {cmd[0]}"
```

Reached from `_cmd_attest` (`goc/engine.py:3883`), which iterates
`layer_2_project_dod` from `.game-of-cards/config.yaml` and dispatches
to `_run_automated_check` for any check with `kind: automated`.

## What's broken

Two coupled defects in the same five-line handler:

1. **Undocumented shape contract.** `cmd` is passed verbatim to
   `subprocess.run` without `shell=True`. The implicit contract is
   "list of tokens" (`["pytest", "-q"]`), but neither
   `goc/templates/game_of_cards/config.yaml` nor `load_deck_config`
   (`goc/engine.py:3662`) documents or validates this. The template
   ships `layer_2_project_dod: []` with no commented example.

   ```yaml
   # goc/templates/game_of_cards/config.yaml (lines 1-8 verbatim)
   # Runtime-neutral Game of Cards configuration.
   #
   # `goc attest <title>` reads the closure sections below and records their
   # results in `deck/<title>/log.md`. Keep project-specific closure checks here,
   # not under an agent-specific directory such as `.claude/`.

   layer_2_project_dod: []
   ```

2. **`cmd[0]` indexes the wrong thing when `cmd` is a string.** When a
   user writes the natural YAML shorthand `cmd: "pytest -q"`,
   `subprocess.run` treats the whole string as the program name and
   raises `FileNotFoundError`. The `except` branch then formats
   `f"command not found: {cmd[0]}"` — for a string, `cmd[0]` is the
   first character (`"p"`), so the message reads `command not found: p`.
   The user has no signal pointing at the shape mistake.

## Empirical evidence

`reproduce.py` (verbatim output today):

```
Case 1 — cmd as a list (correct shape).
  cmd=['true']      passed=True  summary='OK'
Case 2 — cmd as a YAML scalar string with whitespace.
  cmd='pytest -q'   passed=False  summary='command not found: p'

DEFECT CONFIRMED: scalar-string cmd is silently accepted and the
missing-command error reports just the first character of the cmd
string. After a fix that validates the cmd shape or formats the
error without cmd[0]-indexing a string, this script exits zero.
exit=1
```

A direct Python verification of `subprocess.run`'s string semantics:

```
>>> subprocess.run('pytest -q', capture_output=True, text=True, check=False)
FileNotFoundError: [Errno 2] No such file or directory: 'pytest -q'
```

## Why it matters (reachability path)

The offending input shape — a scalar-string `cmd` — is produced
directly by a human editing `.game-of-cards/config.yaml`. The YAML
shorthand for "a list with one item that is a string" is itself a
string, so a copy of the closure-checks reference table from any
modern test runner's CLI page reads as

```yaml
- name: tests
  kind: automated
  cmd: pytest -q          # natural — but a scalar string
```

That YAML is consumed verbatim by `yaml.safe_load` in
`load_deck_config` and flowed unchanged into `_run_automated_check`.
There is no shape gate between the user's keyboard and the
`subprocess.run` call. The first time the user runs `goc attest`, they
see `[ ] tests — command not found: p` recorded into the card's
`log.md`. From the recorded line, the actual cause (string vs list) is
unrecoverable — the original `cmd` string is no longer on screen.

This repo's own `layer_2_project_dod: []` keeps the bug latent here,
but every consumer who adopts `goc attest` for project-specific
closure checks hits this on the first attempt to wire it.

## Decision required (2026-05-30)

The fix is a real human pick between two coherent shapes — both fit
the codebase, with different costs:

### Option A — strict list contract, validate at load

1. `load_deck_config()` validates `layer_2_project_dod[*].cmd`: must
   be a non-empty list of strings. Reject scalar strings with a clear
   error citing the offending check name and the expected shape.
2. Add a commented example to
   `goc/templates/game_of_cards/config.yaml` showing the list shape.
3. Repair `_run_automated_check`'s error path so the missing-cmd
   message renders the *original* cmd (e.g. `" ".join(cmd)` or
   `repr(cmd[0])`), insulating the message from future shape drift.

   **Pro:** keeps the API surface narrow; validation fires once
   per attest invocation; the template documents the shape.
   **Con:** an existing user whose config is "working by accident"
   with `cmd: "true"` (single-token strings *do* resolve, see the
   Annex below) gets a hard error on upgrade.

### Option B — lenient parsing, accept scalar strings

1. `_run_automated_check` detects a scalar-string `cmd` and runs
   `shlex.split(cmd)` before handing it to `subprocess.run`.
2. Document both shapes (string and list) in the template config.
3. Still repair the `cmd[0]` formatter so the message is well-formed
   for either shape.

   **Pro:** matches user intuition (the YAML shorthand "just works");
   no breaking change for consumers who got lucky with single-token
   strings.
   **Con:** doubles the contract surface; shlex semantics diverge
   from the user's actual shell in subtle ways (quoting, env-var
   expansion, glob handling); harder to write future checks against.

### Annex — single-token strings silently work today

`subprocess.run("true", ...)` resolves to `/usr/bin/true` on this
platform and returns exit 0. So a user who writes `cmd: pytest`
(no flags) gets "accidentally working" behavior, masking the
contract until they add a flag. This is part of why the defect
escapes notice — the first failure looks like "my command is broken"
not "the shape is wrong."

A human must pick A or B. The reproduce script and the formatter fix
are common to both branches.

## Cross-references

- [`bundled-closure-skips-configured-attestation-checks`](../bundled-closure-skips-configured-attestation-checks/)
  — a parallel attestation-layer defect; `_cmd_done_bundle` skips
  the same `_run_automated_check` dispatch entirely. Fix scoping
  for this card and that one share the `_cmd_attest` dispatch
  helper proposed in that card's body.
- [`attest-treats-dangling-advanced-by-refs-as-closed`](../attest-treats-dangling-advanced-by-refs-as-closed/)
  — adjacent defect in `_run_derived_check`, the sibling of
  `_run_automated_check`.
