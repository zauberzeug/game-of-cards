---
title: version-flag-only-recognized-as-first-argument
summary: "`goc --version` only prints the version when `--version` is the literal first argument. Any global flag ahead of it (`goc --no-color --version`) or its appearance after a subcommand falls through to the engine argparse parser, which has no `--version` action and exits 2 with `unrecognized arguments: --version`. The flag is also absent from `goc --help`. Register it as a proper argparse `action=\"version\"` on the main parser."
status: open
stage: null
contribution: medium
created: "2026-06-07T05:11:45Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, infra]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero — `goc --no-color --version` and `goc --status all --version` print the version and exit 0 instead of argparse-erroring with exit 2.
  - [ ] TDD: regression test asserts `--version` is honored when it is not the first token, and that it appears in `goc --help` output.
  - [ ] MECHANICAL: `--version`/`-V` registered as an argparse `action="version"` on the engine main parser so it works at any top-level position and is listed in help.
  - [ ] MECHANICAL: version string format preserved as `goc, version <X>`.
  - [ ] `uv run goc validate` passes and the existing regression suite is green.
---

# `--version` is only recognized as the first argument

## Location

`goc/cli.py:40-43` — the hand-rolled pre-parse intercept:

```python
    # --version / -V before any other parsing
    if argv and argv[0] in ("-V", "--version"):
        print(f"goc, version {__version__}")
        return
```

The engine's argparse parser (`goc/engine.py:_build_parser`, line 2817)
never registers a `--version` / `-V` action.

## What's broken

The version flag is intercepted by a literal `argv[0]` check *before*
argparse runs. It is honored only when `--version` is the very first
token. Any global flag placed ahead of it, or the flag appearing after
a subcommand, falls through to `engine_cli` → `parser.parse_args`, which
rejects it as an unrecognized argument and exits 2.

This contradicts the module docstring (`goc/cli.py:4`, "wires up the
`--version` flag") and the universal argparse/Unix convention that
`--version` is position-independent among the program's own options.
It is also missing from `goc --help` entirely, because argparse — the
thing that prints help — never learns the option exists.

## Empirical evidence

```
$ goc --version            → goc, version 0.0.23.post1.dev58   (exit 0)  ✓
$ goc -V                   → goc, version 0.0.23.post1.dev58   (exit 0)  ✓
$ goc --no-color --version → goc: error: unrecognized arguments: --version   (exit 2)  ✗
$ goc --status all --version → goc: error: unrecognized arguments: --version (exit 2)  ✗
$ goc --help | grep -i version → (no match)   ✗
```

See `reproduce.py` for the executable proof.

## Why it matters

`goc --version` is the canonical way a consumer, a CI step, or a bug
report confirms which build is running. The current intercept makes it
brittle: the moment a user composes it with any other top-level flag —
exactly what someone debugging reaches for (`goc --no-color --version`
to capture clean output) — it fails with a confusing argparse usage
dump instead of the version string. The reachability path is the CLI
entry point itself: every invocation flows through `cli.main` →
`engine_cli`, and the only argv shape that reaches the intercept's
happy path is `argv[0] in ("-V", "--version")`.

## Fix

Register the flag as a first-class argparse action on the engine main
parser in `_build_parser` (`goc/engine.py:2817`), and drop the
now-redundant hand-rolled intercept in `cli.py`:

```python
from goc import __version__
...
    parser.add_argument(
        "--version", "-V", action="version",
        version=f"goc, version {__version__}",
    )
```

`parser.parse_args` handles `action="version"` during parsing — before
the dual-tree / legacy-tree guards in `engine.cli` — printing the
version and exiting 0. This makes `--version` work at any top-level
position and lists it in `goc --help` for free. The `goc, version <X>`
string format is preserved. (`goc install --version` / subcommand-scoped
`--version` remain out of scope — argparse subparsers carry their own
namespace, which matches standard tool behavior.)
