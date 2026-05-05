---
title: second-install-exits-nonzero
summary: "The installer is documented as idempotent and the original install card says a second run exits cleanly, but `goc install` currently returns exit code 1 when `deck/.goc-version` already exists. That turns a no-op reinstall into a script failure."
status: done
stage: null
contribution: medium
created: 2026-05-04
closed_at: 2026-05-05
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [x] `uv run python .game-of-cards/deck/second-install-exits-nonzero/reproduce.py` exits zero
  - [x] Re-running `goc install` in an already-installed repo exits zero when it makes no changes
  - [x] The "already installed; run goc upgrade" message remains visible to the user
  - [x] Regression coverage asserts the second install return code and zero filesystem changes
---

# second-install-exits-nonzero

## Location

- `goc/install.py:8`
- `goc/install.py:491`
- `goc/install.py:493`
- `deck/install-command-scaffolds-repo/README.md:17`
- `deck/install-command-scaffolds-repo/README.md:70`

## What's broken

The installer module docstring promises clean idempotency:

```python
Idempotent — second runs detect existing installs via `deck/.goc-version` and
exit clean.
```

The original install card's DoD and implementation notes say the same:

```markdown
`goc install` is idempotent: running twice in the same repo detects existing install and exits with "already installed; run `goc upgrade` to sync templates"
```

But the implementation exits non-zero after printing the already-installed
message:

```python
if existing is not None:
    click.echo(f"already installed (deck/.goc-version → {existing})", err=True)
    click.echo("run `goc upgrade` to re-sync templates.")
    sys.exit(1)
```

## Empirical evidence

Current output from `uv run python deck/second-install-exits-nonzero/reproduce.py`:

```text
first_exit=0
second_exit=1
second_stdout=run `goc upgrade` to re-sync templates.
second_stderr=already installed (deck/.goc-version → 0.0.3)
defect present: second goc install exits non-zero
```

## Why it matters

Installers are commonly run from scripts and bootstrap recipes. If the
target repo is already installed and nothing changes, exit code 1 makes
idempotent setup fail even though the repository is in the desired state.

## Fix

Return zero for the already-installed no-op path. Keep the advisory
message that tells users to run `goc upgrade` for template refreshes.
