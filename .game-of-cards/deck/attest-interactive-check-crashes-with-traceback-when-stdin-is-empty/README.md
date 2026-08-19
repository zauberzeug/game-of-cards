---
title: attest-interactive-check-crashes-with-traceback-when-stdin-is-empty
summary: "`goc attest` raises an uncaught `EOFError` when a `manual` or `agent` closure check is reached with nothing on stdin: `_prompt_yes_no` calls bare `input()`, so an agent harness running the `Skill(finish-card)` Step-5 command gets a traceback and exit 1 instead of the declined outcome `--non-interactive` already defines. Three sibling prompt sites (`confirm`, `install._confirm`, the briefing-target picker) already guard exactly this case; only the four attest prompts do not."
status: open
stage: null
contribution: medium
created: "2026-08-19T04:49:06Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
draft: true
definition_of_done: |
  - [ ] TDD: a regression test runs `_cmd_attest` (or `_prompt_manual` / `_prompt_agent` directly) with a `manual` check and stdin at EOF, and asserts no `EOFError` plus a declined result
  - [ ] TDD: the same test covers the `agent` kind, and asserts the already-working piped-answer and `--non-interactive` paths are unchanged
  - [ ] MECHANICAL: the four `input()` sites in `_prompt_yes_no` / `_prompt_manual` / `_prompt_agent` read through one EOF-safe helper that mirrors `confirm`'s non-TTY contract
  - [ ] TDD: reproduce.py exits zero (the crash no longer fires) on a clean checkout
  - [ ] MECHANICAL: `uv run goc validate` passes and the plugin engine mirrors are re-synced
---

# attest-interactive-check-crashes-with-traceback-when-stdin-is-empty

`goc attest` dies with an unhandled `EOFError` traceback when a `manual` or
`agent` closure check is reached and stdin is at EOF — the exact condition an
agent harness runs it under.

## Location

- `goc/engine.py:5549` — `_prompt_yes_no`, bare `input()`
- `goc/engine.py:5553` — `_prompt_manual`, bare `input()` for the rationale
- `goc/engine.py:5561` — `_prompt_agent`, two more bare `input()` calls
- `goc/engine.py:5672` — the `_cmd_attest` check loop catches `KeyboardInterrupt`
  only, so `EOFError` escapes to the interpreter

## What's broken

The prompt helpers call `input()` with no EOF handling:

```python
def _prompt_yes_no(prompt: str) -> str:
    return input(f"  {prompt} ").strip().lower()
```

Every *other* interactive site in the codebase guards the same case. The
engine's own `confirm` (`goc/engine.py:3740`):

```python
def confirm(prompt: str, *, default: bool = False) -> bool:
    if sys.stdin.isatty():
        ans = input(f"{prompt} [{'Y/n' if default else 'y/N'}]: ").strip().lower()
    else:
        try:
            ans = sys.stdin.readline().strip().lower()
        except (EOFError, OSError):
            return default
```

`install._confirm` (`goc/install.py:1447`) is byte-for-byte the same shape, and
the briefing-target picker (`goc/install.py:1644`) repeats it a third time. So
the repo has a settled three-site convention for "prompt that may run without a
terminal", and the four `attest` prompts are its only violators.

`_cmd_attest` already *defines* the right answer for "cannot ask the human" —
its `--non-interactive` branch:

```python
elif kind == "manual":
    if non_interactive:
        passed, summary = False, "non-interactive: manual check declined"
    else:
        passed, summary = _prompt_manual(check)
```

The defect is only that reaching EOF without that flag produces a traceback
instead of the outcome the flag already names.

## Empirical evidence

`uv run python .game-of-cards/deck/attest-interactive-check-crashes-with-traceback-when-stdin-is-empty/reproduce.py`:

```
=== case 1: stdin at EOF (agent harness) ===
exit=1  EOFError in stderr: True
stderr tail: EOFError: EOF when reading a line

=== case 2: stdin piped 'y' (works today) ===
exit=2  docs-updated line: Docs updated? (y/n)   [x] docs-updated — OK

=== case 3: --non-interactive (works today) ===
exit=2  docs-updated line: [ ] docs-updated — non-interactive: manual check declined

DEFECT: case 1 died with an unhandled EOFError traceback.
Expected: the same declined outcome case 3 already produces.
```

Cases 2 and 3 exit 2 because the probe card's placeholder DoD legitimately
fails `dod-100-percent`; the `docs-updated` line is the part under test. Case 2
confirms the scope: **piping an answer already works**, because `input()` reads
whatever is on stdin. The single broken input is EOF.

## Why it matters

`Skill(finish-card)` Step 5 tells agents to run `goc attest <title>` with no
`--non-interactive` flag, and no skill mentions the flag at all. Agent harnesses
run shell commands with stdin at `/dev/null`, so in any consuming repo that
configures a `manual` or `agent` check in `.game-of-cards/config.yaml`, the
documented closure path ends in a Python traceback. The card cannot be closed
(`goc done` needs the attestation block, which is written *after* the crash
point), and the failure reads as a goc bug rather than as "this check needs a
human".

The reachability path is the shipped default plus one config edit: goc's own
`goc/templates/game_of_cards/config.yaml` ships `derived` checks only, which is
why this has stayed invisible in this repo — but `manual` and `agent` are
first-class `kind` values that `_cmd_attest` dispatches on, and
`Skill(card-schema)` documents layer-2 checks as the project's own DoD.

Same family as the closed [attest-skip-summary-crashes-on-null-check-description](../attest-skip-summary-crashes-on-null-check-description/)
and [closed-since-huge-window-crashes-with-overflowerror-traceback](../closed-since-huge-window-crashes-with-overflowerror-traceback/):
a reachable input turning a verb into a traceback instead of a handled outcome.

## Fix

Route the four `input()` calls through one EOF-safe helper that mirrors
`confirm`'s non-TTY contract — honour a piped answer (already the behaviour),
and on EOF return `""` rather than raising. `""` already falls through to the
existing declined path: `passed = answer in ("y", "yes")` is `False` and the
rationale defaults to `"(declined)"`, which is precisely what `--non-interactive`
produces. No semantics are chosen here that the module does not already fix.

This is a fourth copy of a convention rather than a new one, so the helper lives
next to the prompts it serves; `confirm` keeps its own boolean-with-default
contract, which is a different question than "what did the human type".
