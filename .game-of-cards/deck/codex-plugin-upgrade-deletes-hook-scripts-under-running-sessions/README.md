---
title: codex-plugin-upgrade-deletes-hook-scripts-under-running-sessions
summary: "Codex expands ${PLUGIN_ROOT} to a versioned cache dir at session start, and a marketplace upgrade deletes that dir — so every hook fire in an already-running session execs a deleted script and ENOENTs (observed live on the 0.0.26→0.0.27 upgrade). Fixed by self-healing hook commands that fall back to the newest surviving install; regression-tested under both plausible substitution models."
status: done
stage: null
contribution: medium
created: "2026-07-14T04:54:23Z"
closed_at: "2026-07-14T05:08:55Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero — every hooks.json command survives a
    simulated upgrade that deletes the session's PLUGIN_ROOT, under both
    textual-template and env-var substitution models.
  - [x] TDD: tests/test_codex_hooks_survive_upgrade.py passes (registration
    shape, happy path prefers the session's own install, fallback resolves
    the newest surviving install by mtime — 0.0.100 beats 0.0.9 despite
    lexical order — and a fully-deleted plugin still fails loudly).
  - [x] EMPIRICAL: the live incident is repaired — a 0.0.26 → 0.0.27 compat
    symlink in the affected machine's Codex cache restores the running
    sessions' hook paths; the router exits 0 at the old path again.
  - [x] PROCESS: `uv run goc validate` and the full regression suite pass
    (sole remaining failure is the pre-existing macOS sed portability bug
    tracked in rebase-guard-test-uses-gnu-sed-syntax-and-fails-on-macos).
worker: {who: Rodja Trappe, where: main}
---

# codex-plugin-upgrade-deletes-hook-scripts-under-running-sessions

## Why

Upgrading the Codex plugin (0.0.26 → 0.0.27 via
`codex plugin marketplace upgrade game-of-cards`) broke a *running*
Codex session: every subsequent hook fire printed

```
python3: can't open file '~/.codex/plugins/cache/game-of-cards/game-of-cards/0.0.26/hooks/deck_prompt_router.py': [Errno 2] No such file or directory
```

Codex materializes the plugin under a versioned cache dir and expands
`${PLUGIN_ROOT}` in hook commands when the session starts. The upgrade
replaces the version dir wholesale — after it, the cache contains only
`0.0.27/` while the running session's hook registry still holds the
expanded `0.0.26/...` paths. (Claude Code is immune by platform design:
it retains old version dirs with `.in_use` PID markers while sessions
reference them. Codex has no such retention.)

## What's broken

`codex-plugin/hooks/hooks.json` registered each hook as a bare

```json
"command": "python3 ${PLUGIN_ROOT}/hooks/deck_prompt_router.py"
```

which has no resilience to the expanded path vanishing mid-session. The
fix cannot live in the hook *scripts* — the script file is exactly what
the upgrade deletes, so no code of ours runs; only the command string
survives inside the session.

## Empirical evidence

`reproduce.py` (sibling file) simulates the incident against the
committed hooks.json: a cache holding only `0.0.27/` while the
session's `PLUGIN_ROOT` still says `0.0.26`. Pre-fix, all six
invocations (3 events × 2 substitution models) failed with the exact
live error shape:

```
FAIL  UserPromptSubmit [textual substitution]: python3: can't open file
'.../game-of-cards/0.0.26/hooks/deck_prompt_router.py': [Errno 2] No such file or directory
...
6 hook invocation(s) still break after an upgrade deletes the session's PLUGIN_ROOT.
```

Post-fix all six pass, each resolving the surviving
`0.0.27/hooks/<script>`.

## Fix

`codex-plugin/hooks/hooks.json` (a Codex-specific file outside the
auto-sync set) now wraps each command in a self-healing shell fallback:

```sh
sh -c 'p="${PLUGIN_ROOT}/hooks/<script>.py"; if [ ! -f "$p" ]; then
  d="$(dirname "${PLUGIN_ROOT}")";
  p="$(ls -t "$d"/*/hooks/<script>.py 2>/dev/null | head -n 1)";
fi; exec python3 "$p"'
```

Design notes:

- Works under **both** substitution models, since it is not observable
  which one Codex uses: textual replacement of the `${PLUGIN_ROOT}`
  token before execution, and env-var expansion by the shell. (Quoted
  commands are known-good in Codex hooks — user-level registrations
  like `bash '/path/x.sh'` execute fine.)
- The fallback picks the newest surviving install **by mtime**
  (`ls -t`), not lexically — `0.0.100` sorts before `0.0.9` as a
  string, and newest-mtime is by definition the install the upgrade
  just wrote. The glob only matches existing files, so a dangling
  leftover symlink can never win.
- A fully-deleted plugin still fails loudly (`python3 ""`) rather than
  silently skipping the hook.

Live repair on the affected machine (running sessions, immediate):
`ln -s 0.0.27 ~/.codex/plugins/cache/game-of-cards/game-of-cards/0.0.26`
— verified the router exits 0 at the old path. The symlink dangles
harmlessly after the next upgrade; the shipped fallback (picked up by
sessions started on ≥ this fix) makes future upgrades self-healing.
