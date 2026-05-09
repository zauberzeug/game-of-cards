---
title: replace-click-with-argparse
summary: "Replace click decorators with stdlib `argparse` across ~245 call sites (engine 211, install 33, cli 1). Mechanical swap: `@click.option` → `add_argument`, `click.Choice` → `choices=[...]`, `click.echo` → `print`, `click.confirm` → small TTY-aware helper that auto-declines on non-interactive stdin. Click is doing zero color work — `engine.py:929-941` already owns its own ANSI escapes — so dropping click puts no color rendering at risk. CLI surface (every `goc <verb>` and flag) is preserved by name and short-form. Second piece of the `drop-third-party-runtime-dependencies-from-goc` epic."
status: active
stage: null
contribution: high
created: 2026-05-09
closed_at: null
human_gate: none
advances:
  - drop-third-party-runtime-dependencies-from-goc
advanced_by: []
tags: [story, infra]
definition_of_done: |
  - [ ] All `import click` and `@click.*` decorators are removed from `goc/cli.py`, `goc/engine.py`, `goc/install.py`.
  - [ ] CLI surface is preserved by name and short-form: every existing `goc <verb>` command, option, flag, and choice list still works; `--help` output is structurally equivalent.
  - [ ] `goc upgrade` and the kickoff path still confirm interactively when stdin is a TTY; auto-decline on non-interactive stdin so CI flows do not hang.
  - [ ] `click` is removed from `project.dependencies` in `pyproject.toml`.
  - [ ] CI smoke matrix on Python 3.10–3.13 passes with `click` uninstalled (`pip install --no-deps`).
  - [ ] Manual end-to-end: `goc new`, `goc status`, `goc done`, `goc decide`, `goc advance`, `goc unadvance`, `goc move`, `goc triage`, `goc show`, `goc quality-pass`, `goc validate`, `goc install --dry-run`, `goc upgrade --dry-run` all behave identically to the click-backed versions.
  - [ ] Color rendering is unchanged: `_color_enabled`, `NO_COLOR`, and TTY detection still work (no regression in board / status / standup output).
worker: {who: "claude[bot]", where: main}
---

# replace-click-with-argparse

Child of `drop-third-party-runtime-dependencies-from-goc`. See
the epic body for the broader motivation and survey.

## Why this is mechanical, not creative

Grep settles the surface: click is purely doing what `argparse`
does, just with a decorator-based API.

| API | Calls (engine + install + cli) |
|---|---|
| `click.secho` / `click.style` | **0** |
| `click.echo` (no color) | 153 |
| `@click.command/group/option/argument/pass_context` | 75 |
| `click.confirm` | 3 |
| `click.BadParameter` / `UsageError` / `ClickException` / `Abort` | 11 |
| `click.Choice` | 7 |

Color is already pure-stdlib — `engine.py:929-941` defines ANSI
escape constants; `_color_enabled` (L945) honors `NO_COLOR` and
TTY detection. None of that changes.

## Mechanical mapping

| Click | argparse equivalent |
|---|---|
| `@click.group` (top-level) | `argparse.ArgumentParser` + subparsers |
| `@click.group` (nested) | `add_subparsers().add_parser(...)` then nested `add_subparsers()` |
| `@click.command` | `add_parser(...)` under the right subparser |
| `@click.option('--x', type=...)` | `add_argument('--x', type=...)` |
| `@click.option('--x', is_flag=True)` | `add_argument('--x', action='store_true')` |
| `@click.argument('TITLE')` | `add_argument('title')` |
| `click.Choice([...])` | `choices=[...]` |
| `click.echo(...)` | `print(...)` |
| `click.confirm(...)` | small TTY-aware helper (see below) |
| `click.BadParameter / UsageError` | `parser.error(...)` |
| `click.ClickException / Abort` | `sys.exit(N)` with stderr message |
| `click.pass_context` | drop; pass needed state explicitly |

## The confirm helper

Click's `confirm` returns the default and does not block when stdin
is non-tty. CI runs and pipe invocations rely on that. The
replacement must match:

```python
def confirm(prompt: str, *, default: bool = False) -> bool:
    if not sys.stdin.isatty():
        return default
    ans = input(f"{prompt} [{'Y/n' if default else 'y/N'}]: ").strip().lower()
    if not ans:
        return default
    return ans.startswith("y")
```

`goc upgrade` and the kickoff path are the two callers that must
keep working after the swap.

## Implementation notes

- This is the largest of the three children by line count — the
  pyyaml replacement should ship first as the proof-out of the
  vendoring approach before this rewrite begins.
- Land subcommand-by-subcommand if useful, but the final commit
  should remove `click` from `project.dependencies` in one step.
- The CI matrix already runs `goc validate` on every supported
  Python version. Add a job that uses `pip install --no-deps`
  to prove the dependency drop.
- Update the consumer-copy `claude-plugin/goc/` package in
  lockstep — the byte-for-byte tripwire will fail otherwise.
