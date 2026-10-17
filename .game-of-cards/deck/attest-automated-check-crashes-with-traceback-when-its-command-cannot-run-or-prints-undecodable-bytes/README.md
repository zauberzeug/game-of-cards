---
title: attest-automated-check-crashes-with-traceback-when-its-command-cannot-run-or-prints-undecodable-bytes
summary: "goc attest runs each kind: automated check through _run_automated_check, which turns only subprocess.TimeoutExpired and FileNotFoundError into a FAIL row. A check script missing its executable bit (PermissionError), one missing its shebang line (OSError Exec format error), or a check whose output holds bytes that do not decode (UnicodeDecodeError from text=True) instead kills the verb with a raw traceback and exit 1. No closure-verification block is written and the remaining checks never run, where the contract is a FAIL row in log.md and exit 2."
status: active
stage: null
contribution: medium
created: "2026-10-17T05:00:26Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero — the non-executable script, the shebang-less script and the undecodable-output check each make `goc attest` exit 2 with a `[ ] <check> — <why>` row and a closure-verification block in log.md, and no `Traceback` on stderr (today all three exit 1 with a traceback and write no block).
  - [ ] TDD: a regression test in `tests/` runs `_run_automated_check` against a real non-executable script, a real executable script without a shebang, and a real command whose output holds undecodable bytes, and asserts each returns a `(passed, summary)` tuple instead of raising — the two exec failures as `(False, ...)` naming the program and the OS reason. It fails against today's code.
  - [ ] TDD: undecodable output no longer decides the verdict — a check exiting 0 while printing undecodable bytes passes and one exiting non-zero fails, with the offending bytes rendered as visible ASCII escapes in the summary.
  - [ ] MECHANICAL: the `FileNotFoundError` branch and its `command not found: {cmd[0]}` message are unchanged — the `cmd` shape contract they sit on belongs to attest-cmd-as-string-fails-with-misleading-single-character-not-found-error.
  - [ ] PROCESS: `uv run python -m unittest discover -s tests` is green, `uv run goc validate` is clean, and `python scripts/sync_plugin_assets.py --check` passes after the mirrors regenerate.
worker: {who: "claude[bot]", where: main}
---

# `goc attest` crashes with a traceback when an automated check cannot run or prints undecodable bytes

## Location

`goc/engine.py:5927-5949` — `_run_automated_check(check)`, reached from
`_cmd_attest` (`goc/engine.py:6131`) for every `kind: automated` entry in
`layer_2_project_dod` / `layer_3_goc_dod` of `.game-of-cards/config.yaml`:

```python
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            cwd=str(REPO_ROOT),
            check=False,
        )
    except subprocess.TimeoutExpired:
        return False, f"TIMEOUT (>{timeout_seconds}s)"
    except FileNotFoundError:
        return False, f"command not found: {cmd[0]}"
```

## What's broken

The function's contract is that a check which cannot complete is a failed
check: it returns `(False, <why>)`, `_cmd_attest` prints `[ ] <name> — <why>`,
writes the closure-verification block to `log.md` with a `FAIL` row, and exits
2 with `attestation has failures; finish-card will block closure`. The two
`except` branches above implement that contract for a hung check and a missing
command. Three equally ordinary failures fall outside both branches and escape
as raw exceptions — `_cmd_attest` wraps the call in `except KeyboardInterrupt`
only (`goc/engine.py:6146`):

1. **A check script without its executable bit.** `cmd: ["./scripts/check.sh"]`
   on a file that was never `chmod +x`-ed makes `Popen` raise
   `PermissionError: [Errno 13] Permission denied` — an `OSError` sibling of
   `FileNotFoundError`, not a subclass of it.
2. **An executable script without a shebang line.** `subprocess` calls
   `execve` directly, with no `/bin/sh` fallback, so the kernel refuses the
   file: `OSError: [Errno 8] Exec format error`.
3. **A check whose output does not decode.** `text=True` decodes stdout and
   stderr with the locale codec and `errors="strict"`, so one byte that is not
   valid in that codec raises `UnicodeDecodeError` out of `subprocess.run` —
   after the check has finished and its exit code is already known.

Each kills `goc attest` with a traceback and exit 1. No closure-verification
block is written, the results of the checks that already ran are discarded, and
the checks after the crashing one never run.

## Empirical evidence

`reproduce.py` builds a throwaway deck per case (one card, one automated
layer-2 check) and runs `goc attest probe-card --non-interactive` from the
source tree. Output today (temp paths vary per run):

```
control — check command does not exist (FileNotFoundError, already handled)
  exit=2  traceback=no  closure block written=yes
  row: [ ] missing-command — command not found: /tmp/tmp0vpckor0/no-such-check
case 1 — check script without the executable bit (PermissionError)
  exit=1  traceback=YES  closure block written=NO
  row: (none)
  stderr tail: PermissionError: [Errno 13] Permission denied: '/tmp/tmp7si7a3hd/check.sh'
case 2 — executable check script without a shebang line (ENOEXEC)
  exit=1  traceback=YES  closure block written=NO
  row: (none)
  stderr tail: OSError: [Errno 8] Exec format error: '/tmp/tmptbd0iw23/check.sh'
case 3 — check exits 1 and prints bytes that are not UTF-8 (UnicodeDecodeError)
  exit=1  traceback=YES  closure block written=NO
  row: (none)
  stderr tail: UnicodeDecodeError: 'utf-8' codec can't decode byte 0xe9 in position 3: invalid continuation byte

DEFECT CONFIRMED: 3 of 3 check shapes crash `goc attest` with a traceback instead of recording a FAIL row.
```

The control row is the contract the three crash cases should meet. Case 3 ran
on a UTF-8 host: the crash needs no exotic locale, only a byte that is not
valid UTF-8.

## Why it matters

Reachability is the normal way a project wires its own closure checks. The
config template invites `layer_2_project_dod` entries pointing at the project's
scripts; a freshly written script lacks the executable bit until someone runs
`chmod +x`, and a two-line script often has no shebang. Test runners, linters
and compilers routinely emit bytes outside UTF-8 — Latin-1 file names, binary
diff hunks, tool output in a legacy locale — and the decode happens whether the
check passed or failed. In each case `Skill(finish-card)` receives a Python
traceback where it expects a failed check it can name and act on, and an agent
running attest headless has nothing in `log.md` to cite.

Related cards:

- [attest-cmd-as-string-fails-with-misleading-single-character-not-found-error](../attest-cmd-as-string-fails-with-misleading-single-character-not-found-error/)
  — parked on a decision about the *shape* of `cmd` (scalar string, missing
  keys). The other shape errors are its territory too: a non-string element
  (`cmd: ["sleep", 5]`) raises `TypeError` and an empty list raises
  `IndexError` from the same `subprocess.run` call. This card is about a
  well-shaped `cmd` that cannot run, which needs no decision.
- [goc-crashes-on-hosts-whose-default-encoding-is-not-utf-8](../goc-crashes-on-hosts-whose-default-encoding-is-not-utf-8/)
  — parked on which codec goc pins. Case 3 is independent of that choice:
  strict decoding of arbitrary tool output fails under any codec.
- [attest-interactive-check-crashes-with-traceback-when-stdin-is-empty](../attest-interactive-check-crashes-with-traceback-when-stdin-is-empty/)
  — the closed sibling for the manual/agent check kinds: an unanswerable
  prompt became a declined check, not a traceback.

## Fix

In `_run_automated_check` (`goc/engine.py:5933-5944`):

- Add `except OSError as exc:` after the `FileNotFoundError` branch, returning
  `(False, f"cannot run {program}: {reason}")` with the program taken from
  `exc.filename` (which `Popen` sets to the executable it tried) and the reason
  from `exc.strerror`. That covers EACCES, ENOEXEC and any other failure to
  start the process, and it never indexes `cmd`.
- Pass `errors="backslashreplace"` to `subprocess.run`, so decoding the output
  cannot raise and the exit code alone decides the verdict. The escapes are
  ASCII, so the summary that `_cmd_attest` prints and writes to `log.md` stays
  encodable under any host codec — `"replace"` would add U+FFFD, which a
  non-UTF-8 host cannot write.

Leave the `FileNotFoundError` branch and its message as they are (DoD item 4).
The fix stays inside this one function, plus its test and the regenerated
plugin mirrors.
