---
title: global-cli-flags-silently-dropped-by-subcommand-flag-defaults
summary: "Several `goc` subcommands re-register a global flag's `dest` with a hard default in their own subparser. Argparse silently overwrites the parent value, so `goc --status done quality-pass`, `goc --done quality-pass`, `goc --contribution high new <title>`, and `goc --worker alice triage` all behave as if the user had not passed the global flag. The `--done` help text claims it is a `Shortcut for --status done` — for `quality-pass` neither form works."
status: active
stage: null
contribution: high
created: "2026-05-30T03:18:42Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, meta-fix]
definition_of_done: |
  - [ ] TDD: regression test asserts `parser.parse_args(["--status", "done", "quality-pass"]).status_flag == "done"`
  - [ ] TDD: regression test asserts `parser.parse_args(["--done", "quality-pass"])` causes `_cmd_quality_pass` to filter to `status == "done"` cards
  - [ ] TDD: regression test asserts `parser.parse_args(["--contribution", "high", "new", "<t>"]).contribution == "high"` (not silently coerced to the subparser default)
  - [ ] TDD: regression test asserts `parser.parse_args(["--worker", "alice", "triage"]).worker == "alice"`
  - [ ] PROCESS: decision recorded — which remedy was chosen (drop subparser dups / `default=argparse.SUPPRESS` / post-parse merge / distinct dests) and why
  - [ ] MECHANICAL: every sibling `dest=` collision identified by a grep sweep of `_build_parser` has the remedy applied uniformly
  - [ ] TDD: `reproduce.py` exits zero
worker: {who: "claude[bot]", where: main}
---

# global-cli-flags-silently-dropped-by-subcommand-flag-defaults

## Location

- `goc/engine.py:2531` — global `parser.add_argument("--status", dest="status_flag", ..., default=None)`
- `goc/engine.py:2537` — global `parser.add_argument("--done", dest="done_flag", action="store_true", help="Shortcut for --status done.")`
- `goc/engine.py:2578` — `p_qp.add_argument("--status", dest="status_flag", ..., default="open")` — **same dest, hard default**
- `goc/engine.py:2636` — `p_new.add_argument("--contribution", choices=..., default="medium")` — same dest as global `--contribution` (engine.py:2529), hard default
- `goc/engine.py:2723` — `p_triage.add_argument("--worker", default=os.environ.get("GOC_WORKER"))` — same dest as global `--worker` (engine.py:2554), default re-read at subparser build time

## What's broken

Argparse merges the parent namespace into the subparser namespace at parse time. When a subparser redeclares an argument with the same `dest`, its `default=` unconditionally overwrites whatever the parent argument wrote — even when the user explicitly passed the global flag and the subparser flag was *not* passed. There is no warning, no error, no help-text hint that the position matters.

The three confirmed sites in `_build_parser`:

```python
# engine.py:2531 (global)
parser.add_argument("--status", dest="status_flag", choices=list(STATUS_FILTER_VALUES), default=None, ...)
# engine.py:2578 (subcommand)
p_qp.add_argument("--status", dest="status_flag", choices=list(STATUS_FILTER_VALUES), default="open", ...)
```

```python
# engine.py:2529 (global)
parser.add_argument("--contribution", choices=["high", "medium", "low"], ...)
# engine.py:2636 (subcommand)
p_new.add_argument("--contribution", choices=schema.contribution_values, ...)  # default lives inside the call site
```

```python
# engine.py:2554 (global)
parser.add_argument("--worker", default=os.environ.get("GOC_WORKER"), ...)
# engine.py:2723 (subcommand)
p_triage.add_argument("--worker", default=os.environ.get("GOC_WORKER"), ...)  # default re-read at parser-build time
```

The `--done` shortcut is independently broken for `quality-pass`: `done_flag=True` writes to a separate dest, but `_cmd_quality_pass` (engine.py:3134) reads only `args.status_flag` and never inspects `args.done_flag`, so the documented "shortcut" silently expands to nothing.

## Empirical evidence

```
$ python3 /tmp/test_argparse_collision.py
goc --status done quality-pass                           status_flag='open'      done_flag=False
goc --done quality-pass                                  status_flag='open'      done_flag=True
goc quality-pass --status done                           status_flag='done'      done_flag=False
goc --status all quality-pass                            status_flag='open'      done_flag=False
goc --status done quality-pass --status done             status_flag='done'      done_flag=False
goc quality-pass                                         status_flag='open'      done_flag=False

goc --contribution high new foo -> contribution='medium'
goc --worker alice triage       -> worker=None
```

The `quality-pass --help` page documents the subparser `--status` with its own default `(default: open)`, but the help text for the global `--status` says "One status, or 'all'. Default: open." — neither help text tells the user that putting the flag in the wrong position silently drops it.

## Why it matters

User-facing: when a maintainer runs `goc --done quality-pass` to audit closed-card titles for jargon (the natural invocation; `--done` is documented as the shortcut), they audit open cards instead. When someone tries to reproduce `goc-quality-pass-mutates-summary-and-dod-on-terminal-status-cards` — which names `goc --status all quality-pass` as the entry point — that invocation no longer reaches the bug. The drop is silent: no error, no diagnostic.

Reachability: every consumer who reads the documented `--done` shortcut and follows it, every script that composes global filters with a subcommand, and every contributor exploring `goc <cmd> --help` after seeing global flags at `goc --help`. The drop also affects `goc --contribution high new <title>` (filed card gets `contribution: medium`, not `high`) and `goc --worker alice triage` (worker filter ignored).

The shape is a meta-fix family: the fix at one site is a five-character argparse change, but applying it consistently across three subcommands (and any future subcommand that redeclares a global dest) needs a chosen mechanism + a sweep, not a one-off patch. Hence the `meta-fix` tag.

## Decision

*Resolved 2026-05-30T14:00:21Z:* Option B: set default=argparse.SUPPRESS on the three redeclared subparser flags (--status on quality-pass, --contribution on new, --worker on triage) so the parent value survives when unpassed; add a goc validate (or unit-test) tripwire that fails when any subparser redeclares a parent dest without SUPPRESS; wire _cmd_quality_pass to honour the global --done shortcut

*Reasoning:* smallest behavioral change that preserves both --help surfaces and back-compat with the flag passed in either position, while the tripwire prevents the collision from drifting back in across the three sites and any future one

## Fix sketch

```python
# engine.py:2578
p_qp.add_argument("--status", dest="status_flag",
                  choices=list(STATUS_FILTER_VALUES),
                  default=argparse.SUPPRESS,
                  help="Filter by status (overrides global --status; default: open).")

# engine.py:3136
status_flag = getattr(args, "status_flag", None)
if getattr(args, "done_flag", False) and status_flag is None:
    status_flag = "done"
if status_flag is None:
    status_flag = "open"
```

Mirror the `default=argparse.SUPPRESS` change at engine.py:2636 (`--contribution`) and engine.py:2723 (`--worker`); they currently silently shadow the parent value the same way.

## Related

- `goc-quality-pass-mutates-summary-and-dod-on-terminal-status-cards` — a downstream defect whose documented entry point (`goc --status all quality-pass`) is itself blocked by this collision; closing this card unblocks reproduction of that one.
