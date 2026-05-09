---
title: plugin-wrapper-drops-uv
summary: "Once `pyyaml` and `click` are gone from the engine, `claude-plugin/bin/goc` no longer needs `uv` to materialize a venv. Switch the wrapper to invoke `python3 -m goc.cli \"$@\"` directly against the bundled `claude-plugin/goc/` package. Remove the `uv run --project ${PLUGIN_ROOT}` shell-out, the `.venv/` cache it creates on first call, and any documentation about `uv` as a plugin runtime requirement. This is the prize the whole `drop-third-party-runtime-dependencies-from-goc` epic is aimed at — `uv` becomes a fallback for older Python only, not a hard prerequisite. Sequenced last: blocked until both child stories close (engine must actually be pure-stdlib)."
status: open
stage: null
contribution: low
created: 2026-05-09
closed_at: null
human_gate: none
advances:
  - drop-third-party-runtime-dependencies-from-goc
advanced_by: []
tags: [story, infra]
definition_of_done: |
  - [ ] `claude-plugin/bin/goc` invokes `python3 -m goc.cli "$@"` (or equivalent stdlib-only form) — no `uv`, no `--project`, no `.venv/` materialization.
  - [ ] First-call latency is gone: a fresh plugin install runs `goc <verb>` without provisioning a venv.
  - [ ] `claude-plugin/.venv/` is removed from `.gitignore` if it was only there for the old wrapper behavior.
  - [ ] Plugin README (`claude-plugin/README.md`) and any user-facing install docs no longer list `uv` as a runtime prerequisite — only Python 3.10+ on PATH.
  - [ ] `pipx install game-of-cards` remains the documented fallback for environments without Python 3.10+.
  - [ ] CI plugin byte-for-byte parity tripwire still passes.
  - [ ] Manual smoke: install plugin in a fresh Claude Code, invoke a GoC skill, verify no first-call latency and no `uv` invocation.
---

# plugin-wrapper-drops-uv

Child of `drop-third-party-runtime-dependencies-from-goc`. **Sequenced
last** — depends on the other two children landing first because the
bundled engine must be genuinely pure-stdlib before `python3` can
invoke it.

## Why this is the prize

The current wrapper at `claude-plugin/bin/goc` shells out to
`uv run --project ${PLUGIN_ROOT}` so the bundled engine can
resolve `click` + `pyyaml` inside an isolated venv. That works,
but it forces every plugin user to have `uv` on PATH and pays a
first-call latency penalty when the venv is materialized.

Once the engine drops both runtime deps, the wrapper becomes a
one-liner that just runs Python:

```sh
#!/usr/bin/env bash
exec python3 -m goc.cli "$@"
```

(plus a `PYTHONPATH` adjustment so `${CLAUDE_PLUGIN_ROOT}` is
discoverable, or by relying on the plugin runtime to set it
already — verify during implementation.)

## Sequencing

This card is `human_gate: none` so it's discoverable in the queue,
but the implementer must verify both prerequisites are closed
before starting:

- `replace-pyyaml-with-vendored-parser` — done
- `replace-click-with-argparse` — done

If pulled before either is done, switch status to `blocked` with a
log entry pointing at the missing prerequisite, or pick a
different card.

## Implementation notes

- Confirm the plugin runtime sets `PYTHONPATH` to include
  `${CLAUDE_PLUGIN_ROOT}` before invoking `bin/goc`. If not, the
  wrapper sets it explicitly: `PYTHONPATH="${PLUGIN_ROOT}" python3
  -m goc.cli "$@"`.
- Update `claude-plugin/README.md` to document Python 3.10+ as
  the only runtime prerequisite. Move the `uv` and `pipx` lines
  to a "Fallbacks for older Python" subsection.
- The `pipx install game-of-cards` recipe stays documented as
  the canonical fallback — environments without Python 3.10+ are
  still served.
- Update the byte-for-byte CI tripwire if the wrapper script
  diverges from any source-of-truth template (it currently does
  not — `claude-plugin/bin/goc` has no template counterpart).
- Drop `claude-plugin/.venv/` from `.gitignore` only if grep
  confirms nothing else writes there.
