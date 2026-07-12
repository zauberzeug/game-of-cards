---
title: attest-timeout-cannot-fit-project-check-runtime
status: active
stage: null
contribution: medium
created: "2026-07-12T03:31:59Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
summary: |-
  `goc attest` hard-codes every automated check to 300 seconds, so a
  legitimate project gate whose measured runtime is longer can never attest
  green. Add a positive per-check `timeout_seconds` override while preserving
  the 300-second default for existing configurations.
definition_of_done: |
  - [ ] TDD: an automated check with `timeout_seconds: 1000` forwards `timeout=1000` to `subprocess.run` and reports `TIMEOUT (>1000s)` on expiry
  - [ ] TDD: an automated check without `timeout_seconds` preserves the existing 300-second default and timeout message
  - [ ] TDD: boolean, non-numeric, zero, and negative timeout values fail as a clear check result without invoking the subprocess or raising a traceback
  - [ ] MECHANICAL: the shipped config template documents `timeout_seconds` as an optional positive number with a 300-second default
  - [ ] MECHANICAL: package and Claude/Codex/OpenClaw plugin mirrors are synchronized and the full GoC regression suite passes
worker: {who: Rodja Trappe, where: main}
---

# Attest timeout cannot fit project-check runtime

## Location

- `goc/engine.py:_run_automated_check`
- `goc/templates/game_of_cards/config.yaml`

## What's broken

Every layer-2 automated check is executed with a fixed timeout:

```python
subprocess.run(..., timeout=300, ...)
```

The timeout result is likewise fixed as `TIMEOUT (>300s)`. A consuming
repository with a canonical read-only gate measured at roughly 400--570
seconds therefore cannot produce a truthful green attestation, even though
the identical command completes successfully when run directly.

The project config already owns each automated check's command, so the
timeout belongs beside that command rather than as a global engine constant.

## Evidence

The Phasor Agents consumer records repeated `repository-check` expiry at 300
seconds followed by successful direct runs of the same `make check` command.
The installed 0.0.26 package and current GoC source both contain the literal
300-second bound; no config override exists.

## Why it matters

Attestation should distinguish a failed project gate from an engine budget
that is too short for the project's declared check. Routine skips caused by a
fixed tool budget weaken the closure audit trail.

## Fix

Accept an optional positive numeric `timeout_seconds` field on each automated
check. Preserve 300 seconds when absent. Reject invalid values as a failed
check with a concise diagnostic before spawning the command. Use the effective
value in both `subprocess.run` and the timeout summary, and document the field
in the shipped config template.
