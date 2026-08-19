---
title: attest-interactive-check-crashes-with-traceback-when-stdin-is-empty
summary: "`goc attest` raises an uncaught `EOFError` when a `manual` or `agent` closure check is reached with nothing on stdin: `_prompt_yes_no` calls bare `input()`, so an agent harness running the `Skill(finish-card)` Step-5 command gets a traceback and exit 1 instead of the declined outcome `--non-interactive` already defines. Three sibling prompt sites (`confirm`, `install._confirm`, the briefing-target picker) already guard exactly this case; only the four attest prompts do not."
status: done
stage: null
contribution: medium
created: "2026-08-19T04:49:06Z"
closed_at: "2026-08-19T04:58:12Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: a regression test drives `_prompt_manual` / `_prompt_agent` with stdin at EOF and asserts no `EOFError` plus a declined result
  - [x] TDD: the same test covers the `agent` kind (including its `n-a` answer) and asserts the already-working piped-answer path is unchanged
  - [x] MECHANICAL: the four `input()` sites in `_prompt_yes_no` / `_prompt_manual` / `_prompt_agent` read through one EOF-safe helper, enforced by an AST guard over `goc/engine.py`
  - [x] TDD: reproduce.py exits zero (the crash no longer fires) and asserts the piped-answer and `--non-interactive` paths are unchanged
  - [x] MECHANICAL: `uv run goc validate` passes and the three plugin engine mirrors are re-synced
worker: {who: "claude[bot]", where: main}
---

# `goc attest` crashes with a traceback when an interactive check runs with empty stdin

## Summary

`goc attest` raised an uncaught `EOFError` when a `manual` or `agent`
closure check was reached with nothing on stdin — the condition an agent
harness runs it under. The four prompt call sites used bare `input()`,
while the three other interactive sites in the codebase already guard the
same case. Fixed: the prompts now read through one EOF-safe helper and
degrade to the declined outcome `--non-interactive` already defines.

## Location

- `goc/engine.py:5549` — `_prompt_line`, the new EOF-safe reader
- `goc/engine.py:5570` — `_prompt_yes_no`
- `goc/engine.py:5574` — `_prompt_manual`
- `goc/engine.py:5582` — `_prompt_agent`
- `goc/engine.py:5693` — the `_cmd_attest` check loop, which catches
  `KeyboardInterrupt` only, so `EOFError` escaped to the interpreter

## What was broken

The prompt helpers called `input()` with no EOF handling:

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

`install._confirm` (`goc/install.py:1447`) is the same shape, and the
briefing-target picker (`goc/install.py:1644`) repeats it a third time. So
the repo had a settled three-site convention for "prompt that may run
without a terminal", and the four `attest` prompts were its only violators.

`_cmd_attest` already *defined* the right answer for "cannot ask the
human" — its `--non-interactive` branch:

```python
elif kind == "manual":
    if non_interactive:
        passed, summary = False, "non-interactive: manual check declined"
    else:
        passed, summary = _prompt_manual(check)
```

The defect was only that reaching EOF *without* that flag produced a
traceback instead of the outcome the flag already names.

## Empirical evidence

`uv run python .game-of-cards/deck/attest-interactive-check-crashes-with-traceback-when-stdin-is-empty/reproduce.py`

Before the fix:

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

After:

```
=== case 1: stdin at EOF (agent harness) ===
exit=2  EOFError in stderr: False
stderr tail: ERROR: attestation has failures; finish-card will block closure.

FIXED: case 1 no longer raises EOFError.
case 1 docs-updated line: [ ] docs-updated — (declined)
cases 2 and 3 unchanged.
```

Cases 2 and 3 exit 2 because the probe card's placeholder DoD legitimately
fails `dod-100-percent`; the `docs-updated` line is the part under test.
Case 2 fixes the scope of the defect: **piping an answer always worked**,
because `input()` reads whatever is on stdin. The single broken input was
EOF.

## Why it mattered

`Skill(finish-card)` Step 5 tells agents to run `goc attest <title>` with no
`--non-interactive` flag, and no skill mentions the flag at all. Agent
harnesses run shell commands with stdin at `/dev/null`, so in any consuming
repo that configures a `manual` or `agent` check in
`.game-of-cards/config.yaml`, the documented closure path ended in a Python
traceback. The card could not be closed (`goc done` needs the attestation
block, which is written *after* the crash point), and the failure read as a
goc bug rather than as "this check needs a human".

The reachability path is the shipped default plus one config edit: goc's own
`goc/templates/game_of_cards/config.yaml` ships `derived` checks only, which
is why this stayed invisible in this repo — but `manual` and `agent` are
first-class `kind` values that `_cmd_attest` dispatches on, and
`Skill(card-schema)` documents layer-2 checks as the project's own DoD.

Same family as the closed [attest-skip-summary-crashes-on-null-check-description](../attest-skip-summary-crashes-on-null-check-description/)
and [closed-since-huge-window-crashes-with-overflowerror-traceback](../closed-since-huge-window-crashes-with-overflowerror-traceback/):
a reachable input turning a verb into a traceback instead of a handled
outcome.

## Fix (delivered)

The four `input()` calls now route through one EOF-safe helper,
`_prompt_line`, which mirrors `confirm`'s non-TTY contract — a piped answer
is honoured (already the behaviour), and EOF returns `""` rather than
raising:

```python
def _prompt_line(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except EOFError:
        print()
        return ""
```

`""` falls through to the callers' existing declined path:
`passed = answer in ("y", "yes")` is `False` and the rationale defaults to
`"(declined)"` — precisely what `--non-interactive` produces. No semantics
are chosen here that the module did not already fix.

`tests/test_attest_prompt_eof.py` covers both kinds at EOF, the surviving
piped-answer and `n-a` paths, and adds an AST guard asserting `_prompt_line`
is the only sanctioned `input()` call site among the prompt helpers — so a
future prompt cannot silently re-open the crash. The guard was verified
against the pre-fix engine: 3 errors + 1 failure, i.e. it catches the real
offender rather than merely passing.
