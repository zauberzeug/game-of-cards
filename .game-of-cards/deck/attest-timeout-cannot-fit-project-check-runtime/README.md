---
title: attest-timeout-cannot-fit-project-check-runtime
status: done
stage: null
contribution: medium
created: "2026-07-12T03:31:59Z"
closed_at: "2026-07-12T03:41:48Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
summary: |-
  `goc attest` now accepts a positive-integer `timeout_seconds` override on
  each automated check while preserving the 300-second default. Invalid or
  subprocess-overflowing values fail cleanly before a command is spawned.
definition_of_done: |
  - [x] TDD: an automated check with `timeout_seconds: 1000` forwards `timeout=1000` to `subprocess.run` and reports `TIMEOUT (>1000s)` on expiry
  - [x] TDD: an automated check without `timeout_seconds` preserves the existing 300-second default and timeout message
  - [x] TDD: boolean, non-integer, zero, negative, and subprocess-overflowing timeout values fail as a clear check result without invoking the subprocess or raising a traceback
  - [x] MECHANICAL: the shipped config template documents `timeout_seconds` as an optional positive integer with a 300-second default
  - [x] MECHANICAL: package and Claude/Codex/OpenClaw plugin mirrors are synchronized; 713 tests and 198 subtests pass with only the documented macOS-local interactive-rebase setup test excluded
worker: {who: Rodja Trappe, where: main}
---

# Attest timeout cannot fit project-check runtime

## Location

- `goc/engine.py:_run_automated_check`
- `goc/templates/game_of_cards/config.yaml`

## Resolved defect

Before this change, every layer-2 automated check was executed with a fixed
timeout:

```python
subprocess.run(..., timeout=300, ...)
```

The timeout result was likewise fixed as `TIMEOUT (>300s)`. A consuming
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

## Resolution

Automated checks accept an optional positive integer `timeout_seconds` field.
The engine preserves 300 seconds when absent, rejects invalid values as a
failed check before spawning the command, and uses the effective value in both
`subprocess.run` and the timeout summary. The shipped config template documents
the field, and all bundled plugin engines carry the same implementation.
