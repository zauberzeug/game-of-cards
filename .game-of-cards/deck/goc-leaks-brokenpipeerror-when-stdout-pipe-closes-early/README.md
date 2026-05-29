---
title: goc-leaks-brokenpipeerror-when-stdout-pipe-closes-early
summary: "When `goc` writes to a stdout pipe whose consumer closes early (e.g. `goc --done | head`), the process prints a Python `BrokenPipeError` traceback to stderr at interpreter shutdown because `cli.py` does not install a SIGPIPE handler. Output to the consumer is correct; the noise is purely a missing-handler artifact, but it pollutes terminals and breaks `set -e` / `set -o pipefail` shell pipelines and `grep -q` short-circuits."
status: done
stage: null
contribution: low
created: "2026-05-29T07:47:02Z"
closed_at: "2026-05-29T07:52:15Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [x] TDD: a regression test runs `goc --done` (or any large-output verb) through a closed pipe and asserts stderr contains no `BrokenPipeError` traceback.
  - [x] MECHANICAL: `goc/cli.py:main` installs a SIGPIPE handler (`signal.signal(signal.SIGPIPE, signal.SIG_DFL)`) or wraps stdout writes such that early pipe close exits cleanly without a Python-level traceback.
  - [x] MECHANICAL: `uv run goc --done | head -3` produces only the requested rows on stdout and an empty stderr.
  - [x] MECHANICAL: `uv run goc validate` clean; plugin-asset sync `--check` green.
worker: {who: "claude[bot]", where: main}
---

# `goc` leaks `BrokenPipeError` when its stdout pipe closes early

## Location

`goc/cli.py:26` — `main()` does not install a SIGPIPE handler. The
engine printers in `goc/engine.py` write to `sys.stdout` directly
(`print(...)`), so when the consumer of a pipeline closes its read
end, the interpreter shutdown flushes a partially-buffered stdout,
raises `BrokenPipeError`, and emits the canonical Python "Exception
ignored in: ..." traceback to stderr.

## What's broken

`grep -n "SIGPIPE\|BrokenPipeError\|signal" goc/engine.py goc/cli.py
goc/install.py` returns zero hits — no handler is installed anywhere
in the CLI entry path. Python's default behavior on a write to a
closed pipe is to translate the OS-level `SIGPIPE` to a
`BrokenPipeError` exception. If unhandled, the interpreter writes the
traceback to stderr during shutdown.

## Empirical evidence

Reproduced 2026-05-29 on `main` at HEAD:

```
$ uv run goc --done 2>/tmp/err | head -3 > /dev/null
$ cat /tmp/err
Exception ignored in: <_io.TextIOWrapper name='<stdout>' mode='w' encoding='utf-8'>
BrokenPipeError: [Errno 32] Broken pipe
```

stdout (suppressed above) carries the first three rows correctly; the
traceback is shutdown-time noise, not a content failure. See
`reproduce.py` for the executable form.

## Why it matters — reachability

Any pipeline that closes the consumer before `goc` finishes writing
triggers the bug. Concrete reach paths:

- Interactive triage: `uv run goc --done | head`, `... | less`,
  `... | grep -q <fragment>`, `... | sed -n '1,5p'`. Each shows the
  traceback even though the user sees the correct content first.
- Shell automation under `set -o pipefail`: the pipeline's exit
  status becomes non-zero because the producer was killed by
  `SIGPIPE` (Python converts it to exit 1 after the unhandled
  exception). A CI script doing `goc ... | grep -q SOMETHING && ...`
  fails on the producer side, not the grep, when the grep
  short-circuits.
- Skill / hook output: any project hook that pipes a `goc` query into
  a terminal-narrowing filter inherits the noise. The session-start
  hook's "Active card(s):" output was unaffected here only because it
  consumes the full stream — change the consumer to a `| head` and
  the noise surfaces.

The output Python writes to stdout *before* the pipe closes is still
correct. This card files the missing-handler defect, not a content
bug.

## Fix proposal

The standard CPython recipe for command-line tools is to restore the
default SIGPIPE disposition at process start so the OS terminates the
process cleanly when the pipe closes, instead of translating into a
Python-level exception. In `goc/cli.py:main()`, before any argv
dispatch:

```python
import signal
try:
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
except (AttributeError, ValueError):
    pass  # Windows / restricted thread context
```

The `try/except` guards Windows (no `SIGPIPE`) and any test harness
that imports `main` from a non-main thread (`signal.signal` raises
`ValueError` off the main thread).

Alternative if the handler approach is rejected: wrap `engine_cli`
and the install/upgrade paths in `try/except BrokenPipeError` and
exit silently. The signal-restore form is preferred — it lets the
kernel deliver the signal and avoids any per-write try/except churn.

## Notes

- Closely related but not a duplicate of
  [`closure-log-attestation-misfires-across-utc-midnight`](../closure-log-attestation-misfires-across-utc-midnight/)
  (different surface area; that card is about closure-log boundaries).
- No existing `disproved` rebuttal for this hypothesis (grepped 2026-05-29).
