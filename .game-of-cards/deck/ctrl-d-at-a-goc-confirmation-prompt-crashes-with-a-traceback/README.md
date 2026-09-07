---
title: ctrl-d-at-a-goc-confirmation-prompt-crashes-with-a-traceback
summary: "Pressing Ctrl-D at any goc confirmation prompt raises an uncaught EOFError traceback. `confirm` (engine.py:3796), `install._confirm` (install.py:1448) and the briefing-target picker (install.py:1643) each branch on `sys.stdin.isatty()` and put the `except (EOFError, OSError)` on the non-TTY `readline()` branch — which returns `''` at EOF and cannot raise it — leaving the TTY `input()` branch, the only one that can, bare. So a piped empty stdin declines cleanly while an interactive Ctrl-D crashes, in front of `goc migrate`'s rmtree and two `goc upgrade` prompts."
status: done
stage: null
contribution: medium
created: "2026-08-20T04:38:59Z"
closed_at: "2026-08-20T04:50:36Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: a regression test drives `engine.confirm`, `install._confirm` and the briefing-target picker with stdin a tty at EOF and asserts no `EOFError` plus the prompt's `default` outcome
  - [x] TDD: the same test asserts the already-working paths are unchanged — a piped answer, a bare Enter, and an empty pipe all keep their current results at all three sites
  - [x] MECHANICAL: every `input()` call in `goc/engine.py` and `goc/install.py` reads through an EOF-safe helper, enforced by an AST guard widened from `tests/test_attest_prompt_eof.py`'s
  - [x] TDD: reproduce.py exits zero (case 1 and case 2 no longer raise) with case 3's piped decline unchanged
  - [x] MECHANICAL: the stale claim that these three sites "already guard exactly this case" is corrected in `attest-interactive-check-crashes-with-traceback-when-stdin-is-empty`'s body, with a forward pointer to this card in its log.md
  - [x] MECHANICAL: `uv run goc validate` passes, the regression suite is green, and the four plugin engine mirrors are re-synced
worker: {who: "claude[bot]", where: main}
---

# Pressing Ctrl-D at a `goc` confirmation prompt crashes with a traceback

## Summary

Every interactive `goc` prompt raised an uncaught `EOFError` when the user
pressed Ctrl-D. The three prompt sites each branch on `sys.stdin.isatty()`
and put the `except (EOFError, OSError)` on the **non-TTY** branch — the one
whose `readline()` signals EOF by returning `""` and therefore cannot raise
it — leaving the **TTY** `input()` branch, the only one that can, bare. The
guard was on the wrong side of the branch. Fixed: all three sites read
through an EOF-safe helper, and Ctrl-D now takes the same `default` a bare
Enter already took.

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

Before the fix:

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

After:

```
=== case 1: Ctrl-D at the two confirm helpers (tty) ===
Remove legacy tree? [y/N]:
  engine.confirm: returned False
Remove leftover vendored layout? [y/N]:
  install._confirm: returned False
  (guarded branch: readline() at EOF -> '', never raises)

=== case 2: `goc migrate`, Ctrl-D at its rmtree confirmation (tty) ===
  exit=1  EOFError in stderr: False
  legacy deck/ still present: True

=== case 3: same question, empty pipe (the guarded branch) ===
  exit=1  EOFError in stderr: False
  stderr: ''
  legacy deck/ still present: True

FIXED: Ctrl-D no longer raises out of any confirmation prompt, and the piped decline is unchanged.
```

Case 1 drives the helpers directly; case 2 runs the real CLI; case 3 is the
contrast that pins the defect — the identical question, answered by an empty
pipe, exits 1 with an empty stderr, before and after. Both `goc migrate`
outcomes are still exit 1 with the legacy tree intact: the fix changes how
the refusal is reported, not what it does.

## Why it matters

Ctrl-D is the standard way to refuse a terminal prompt, and it was the only
refusal these three prompts did not understand. All four reachable prompts
gate an irreversible step — `goc migrate`'s `shutil.rmtree` of the legacy
tree, `goc upgrade`'s vendored-harness strip, `goc upgrade`'s marker-block
strip from the briefing files it was not pointed at — so the prompt is
exactly where a user is most likely to back out. The crash *fails safe* (it
fires before any of those steps; case 2 confirms the legacy tree survives),
so this is a diagnosis and trust defect rather than a data-loss one: a
traceback reads as "goc is broken", not "you declined", and it teaches users
that backing out of a destructive goc prompt is unsafe.

It also mattered as an internal-consistency defect. `confirm` and
`install._confirm` are a duplicated pair — byte-identical bodies in two
modules — and the picker is a third open-coded copy of the same branch, so
the bug is stamped out three times. The family is the one named by
[attest-interactive-check-crashes-with-traceback-when-stdin-is-empty](../attest-interactive-check-crashes-with-traceback-when-stdin-is-empty/),
[attest-skip-summary-crashes-on-null-check-description](../attest-skip-summary-crashes-on-null-check-description/)
and
[closed-since-huge-window-crashes-with-overflowerror-traceback](../closed-since-huge-window-crashes-with-overflowerror-traceback/):
a reachable input turning a verb into a traceback instead of a handled
outcome.

## Fix (delivered)

All three sites now read through an EOF-safe reader — `input()` wrapped in
`except EOFError`, with no `isatty()` branch of its own, because that branch
was never what made a read safe:

- `goc/engine.py:3795` `confirm` — the TTY read goes through `_prompt_line`
  (`goc/engine.py:5616`), the reader the sibling card introduced. EOF returns
  `""`, which the pre-existing `if not ans: return default` already handles,
  so the outcome is the caller's `default`.
- `goc/install.py:1447` `_confirm` — same change against a second copy of the
  reader added at `goc/install.py:1447`. `install.py` cannot import from
  `engine` (the dependency runs the other way), so the helper is duplicated
  rather than shared, with a docstring on each saying so.
- `goc/install.py:1668` — the picker's `raw = input(...)`, through the same
  `install.py` reader, so EOF lands in the existing
  `if not raw: choice = found[0]` default.

The `isatty()` branch is kept everywhere it was: it selects whether the
question is *echoed*, and a piped caller must not have it interleaved into
captured stdout. `tests/test_confirm_prompt_eof.py::test_piped_branch_does_not_echo_the_prompt`
pins that, so a later "just always use `_prompt_line`" simplification cannot
quietly change what a scripted caller sees. The dead `except EOFError` on the
non-TTY branches is kept too, for a substituted stdin object that raises
instead of returning `""`; each docstring now says which branch the guard is
load-bearing on.

No new semantics: an empty answer already meant "take the default" at all
three sites. The change removes a crash from a path that already had a
defined outcome.

`tests/test_confirm_prompt_eof.py` (10 tests) covers EOF at all three sites
in both `default` directions, the unchanged typed/bare-Enter/piped paths, the
picker's surviving out-of-range abort, and the prompt-echo contract. Its AST
guard widens the sibling card's: `_prompt_line` must be the *only* `input()`
call site in `goc/engine.py` and in `goc/install.py`, and must handle
`EOFError` — so a fourth copy of the bare branch fails the build instead of
re-opening this. Verified against the pre-fix engine (`git archive HEAD`):
4 errors + 2 failures, i.e. it catches the real offender. Full suite 1028
passed (was 1018).

The claims this card contradicts are corrected in
[attest-interactive-check-crashes-with-traceback-when-stdin-is-empty](../attest-interactive-check-crashes-with-traceback-when-stdin-is-empty/)'s
body, with a forward pointer in its `log.md` — closure is not frozenness, and
that card's own delivered fix is unaffected.
