---
title: ctrl-d-at-a-goc-confirmation-prompt-crashes-with-a-traceback
summary: "Pressing Ctrl-D at any goc confirmation prompt raises an uncaught EOFError traceback. `confirm` (engine.py:3796), `install._confirm` (install.py:1448) and the briefing-target picker (install.py:1643) each branch on `sys.stdin.isatty()` and put the `except (EOFError, OSError)` on the non-TTY `readline()` branch — which returns `''` at EOF and cannot raise it — leaving the TTY `input()` branch, the only one that can, bare. So a piped empty stdin declines cleanly while an interactive Ctrl-D crashes, in front of `goc migrate`'s rmtree and two `goc upgrade` prompts."
status: active
stage: null
contribution: medium
created: "2026-08-20T04:38:59Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] TDD: a regression test drives `engine.confirm`, `install._confirm` and the briefing-target picker with stdin a tty at EOF and asserts no `EOFError` plus the prompt's `default` outcome
  - [ ] TDD: the same test asserts the already-working paths are unchanged — a piped answer, a bare Enter, and an empty pipe all keep their current results at all three sites
  - [ ] MECHANICAL: every `input()` call in `goc/engine.py` and `goc/install.py` reads through an EOF-safe helper, enforced by an AST guard widened from `tests/test_attest_prompt_eof.py`'s
  - [ ] TDD: reproduce.py exits zero (case 1 and case 2 no longer raise) with case 3's piped decline unchanged
  - [ ] MECHANICAL: the stale claim that these three sites "already guard exactly this case" is corrected in `attest-interactive-check-crashes-with-traceback-when-stdin-is-empty`'s body, with a forward pointer to this card in its log.md
  - [ ] MECHANICAL: `uv run goc validate` passes, the regression suite is green, and the four plugin engine mirrors are re-synced
worker: {who: "claude[bot]", where: main}
---

# Pressing Ctrl-D at a `goc` confirmation prompt crashes with a traceback

## Summary

Every interactive `goc` prompt raises an uncaught `EOFError` when the user
presses Ctrl-D. The three prompt sites each branch on `sys.stdin.isatty()`
and put the `except (EOFError, OSError)` on the **non-TTY** branch — the one
whose `readline()` signals EOF by returning `""` and therefore cannot raise
it — leaving the **TTY** `input()` branch, the only one that can, bare. The
guard is on the wrong side of the branch.

## Location

- `goc/engine.py:3796` — `confirm`, TTY branch
- `goc/install.py:1448` — `install._confirm`, TTY branch (same shape, second copy)
- `goc/install.py:1643` — the briefing-target picker in
  `install._resolve_briefing_target`, TTY branch (third copy)

Reached from:

- `goc/engine.py:7016` — `_cmd_migrate`, the confirmation in front of
  `shutil.rmtree(legacy)`
- `goc/engine.py:4604` — `quality-pass`'s interactive accept/reject walk
- `goc/install.py:1801` — `goc upgrade`'s "Remove leftover vendored layout?"
- `goc/install.py:1643` — `goc upgrade`'s briefing-target pick, which strips
  GoC marker blocks from the files not chosen

## What's broken

All three sites are this shape (`goc/engine.py:3795`):

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

`io.TextIOBase.readline()` returns `""` at end of file — it does not raise
`EOFError` — so the `except EOFError` on the guarded branch is dead code,
and the empty-string result falls through to the `if not ans: return
default` below it. `input()`, on the other hand, raises `EOFError` at EOF by
contract, and that is the branch a real terminal takes. Nothing between
there and `goc.cli:main` catches it: the only `EOFError` handler in the
package is `_prompt_line`'s (`goc/engine.py:5618`), and `_cmd_attest`'s loop
catches `KeyboardInterrupt` alone.

The result is inverted from what a reader would predict: **the automated
caller is handled and the human is not.** Piping empty stdin declines
cleanly; typing Ctrl-D at the same question produces a Python traceback.

## The convention this contradicts

The card closed one day earlier,
[attest-interactive-check-crashes-with-traceback-when-stdin-is-empty](../attest-interactive-check-crashes-with-traceback-when-stdin-is-empty/),
fixed this same shape in the four `attest` prompts, and its body argues from
these three sites as the settled standard:

> Every *other* interactive site in the codebase guards the same case.

> So the repo had a settled three-site convention for "prompt that may run
> without a terminal", and the four `attest` prompts were its only violators.

That is true only of the non-TTY branch. The three cited sites do not guard
the TTY branch at all, so the "settled convention" was half-implemented, and
the helper that card delivered — `_prompt_line`, which wraps `input()`
itself with no `isatty()` branch at all — is the *more* correct pattern of
the two. This card inverts the direction of the earlier one: the three older
sites should adopt `_prompt_line`'s posture, not the reverse.

## Empirical evidence

`uv run python .game-of-cards/deck/ctrl-d-at-a-goc-confirmation-prompt-crashes-with-a-traceback/reproduce.py`

```
=== case 1: Ctrl-D at the two confirm helpers (tty) ===
Remove legacy tree? [y/N]:   engine.confirm: EOFError(EOF when reading a line)  <-- CRASH
Remove leftover vendored layout? [y/N]:   install._confirm: EOFError(EOF when reading a line)  <-- CRASH
  (guarded branch: readline() at EOF -> '', never raises)

=== case 2: `goc migrate`, Ctrl-D at its rmtree confirmation (tty) ===
  exit=1  EOFError in stderr: True
        ans = input(f"{prompt} [{'Y/n' if default else 'y/N'}]: ").strip().lower()
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    EOFError: EOF when reading a line
  legacy deck/ still present: True

=== case 3: same question, empty pipe (the guarded branch) ===
  exit=1  EOFError in stderr: False
  stderr: ''
  legacy deck/ still present: True

DEFECT: the TTY branch raises EOFError out of the verb, while the same refusal on the non-TTY branch is handled.
Expected: Ctrl-D declines and returns the prompt's `default`, the outcome an empty pipe already produces.
```

Case 1 drives the helpers directly; case 2 runs the real CLI; case 3 is the
contrast that pins the defect — the identical question, answered by an empty
pipe, exits 1 with an empty stderr.

## Why it matters

Ctrl-D is the standard way to refuse a terminal prompt, and it is the only
refusal these three prompts do not understand. All four reachable prompts
gate an irreversible step — `goc migrate`'s `shutil.rmtree` of the legacy
tree, `goc upgrade`'s vendored-harness strip, `goc upgrade`'s marker-block
strip from the briefing files it was not pointed at — so the prompt is
exactly where a user is most likely to back out. The crash *fails safe* (it
fires before any of those steps; case 2 confirms the legacy tree survives),
so this is a diagnosis and trust defect rather than a data-loss one: a
traceback reads as "goc is broken", not "you declined", and it teaches users
that backing out of a destructive goc prompt is unsafe.

It also matters as an internal-consistency defect. `confirm` and
`install._confirm` are a duplicated pair — byte-identical bodies in two
modules — and the picker is a third open-coded copy of the same branch, so
the bug is stamped out three times. The family is the one named by
[attest-interactive-check-crashes-with-traceback-when-stdin-is-empty](../attest-interactive-check-crashes-with-traceback-when-stdin-is-empty/),
[attest-skip-summary-crashes-on-null-check-description](../attest-skip-summary-crashes-on-null-check-description/)
and
[closed-since-huge-window-crashes-with-overflowerror-traceback](../closed-since-huge-window-crashes-with-overflowerror-traceback/):
a reachable input turning a verb into a traceback instead of a handled
outcome.

## Fix

Route all three sites' reads through one EOF-safe helper, which is what
`_prompt_line` (`goc/engine.py:5604`) already is — `input()` wrapped in
`except EOFError`, no `isatty()` branch, because the branch was never what
made it safe:

- `goc/engine.py:3795` `confirm` — read the answer through an EOF-safe read
  on both branches and return `default` at EOF, which is what the non-TTY
  branch already promises and what `if not ans` already does for a bare
  Enter. `engine.confirm` can reuse `_prompt_line` directly.
- `goc/install.py:1447` `_confirm` — same change. `install.py` does not
  import from `engine`, so it needs its own small reader rather than a
  cross-module import.
- `goc/install.py:1643` — the picker's `raw = input(...)`, using the same
  `install.py` reader, so an EOF falls into the existing
  `if not raw: choice = found[0]` default rather than crashing.

An empty answer already means "take the default" at all three sites, so EOF
folding into it introduces no new semantics — it removes a crash from a path
that already had a defined outcome.

A guard test should assert the shape rather than only the behaviour: the
sibling card's `tests/test_attest_prompt_eof.py` added an AST check that
`_prompt_line` is the only sanctioned `input()` call site among the attest
prompt helpers. The same check, widened to `goc/engine.py` and
`goc/install.py` as a whole, is what stops a fourth copy of the branch from
re-opening this.
