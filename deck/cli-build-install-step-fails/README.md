---
title: cli-build-install-step-fails
summary: "GitHub Actions CI fails before the CLI smoke tests because the package install step passes `--system`, which makes uv ignore setup-uv's activated `.venv` and try Ubuntu's externally managed `/usr` Python."
status: done
stage: null
contribution: medium
created: 2026-05-04
closed_at: 2026-05-04
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [x] reproduce.py exits zero
  - [x] CI workflow package install no longer passes `--system`
  - [x] editable package install smoke test succeeds in an isolated venv
  - [x] regression tests pass locally
---

# CLI Build Install Step Fails

## Location

- `.github/workflows/ci.yml` - `Install package`

## What's Broken

The CI workflow used:

```yaml
- name: Install package
  run: uv pip install --system -e .
```

The failing GitHub Actions run `25318919272` shows `setup-uv@v5` setting
`VIRTUAL_ENV=/home/runner/work/game-of-cards/game-of-cards/.venv`, then the
install step forcing `--system`.

## Empirical Evidence

From job `74222788801`, step `Install package`:

```text
Using Python 3.12.3 environment at: /usr
error: The interpreter at /usr is externally managed
hint: Virtual environments were not considered due to the `--system` flag
```

## Why It Matters

The package never reaches the console-script smoke test, regression tests, or
deck validation in CI. Every matrix entry fails at install on Ubuntu.

## Fix

Install the editable package into the virtual environment that `setup-uv`
already activates:

```yaml
- name: Install package
  run: uv pip install -e .
```
