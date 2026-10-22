---
title: double-fire-warning-goes-silent-once-hook-commands-quote-their-script-path
summary: "FIXED: the plugin-plus-vendored hook double-fire warning learned GoC's hook script names from _goc_hook_basenames, which split each GOC_CLAUDE_HOOKS command on '/' instead of reading it through claude_hook_bindings, the single walk that registry's own docstring mandates. Quoting the registry path — the fix the open spaces-in-path card prescribes — left a trailing quote on every name, so the warning would never fire again while its regression test, built on a hardcoded unquoted fixture, stayed green. _goc_hook_basenames now reads claude_hook_bindings."
status: done
stage: null
contribution: medium
created: "2026-10-18T04:32:56Z"
closed_at: "2026-10-18T04:38:55Z"
human_gate: none
advances:
  - hook-command-registrations-word-split-on-install-paths-with-spaces
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero — under the quoted registry `_goc_hook_basenames` agrees with `claude_hook_bindings` and the double-fire warning still fires
  - [x] TDD: `tests/test_validate_plugin_hook_double_fire.py` gains a case that writes the vendored registrations through `_merge_claude_settings` under a quoted `GOC_CLAUDE_HOOKS` and asserts the warning fires — red on the current parse, green after the fix
  - [x] TDD: a test pins `engine._goc_hook_basenames()` to the script names `install.claude_hook_bindings()` yields, so a second command parse cannot return
  - [x] MECHANICAL: `_goc_hook_basenames` reads the registry through `claude_hook_bindings` (no command parse of its own left in `goc/engine.py`); plugin mirrors synced; full regression suite and `goc validate` green
worker: {who: "claude[bot]", where: main}
---

# The hook double-fire warning goes silent once hook commands quote their script path

## Location

- `goc/engine.py:5851` — `_goc_hook_basenames`, the stray parse
- `goc/engine.py:5867` — `_vendored_goc_hooks_registered`, its only caller
- `goc/engine.py:5885` — `validate_plugin_hook_double_fire`, the `goc validate` warning that goes dark
- `goc/install.py:618` — `claude_hook_bindings`, the registry's one command-to-script walk
- `tests/test_validate_plugin_hook_double_fire.py:20` — the hardcoded `VENDORED_HOOKS` fixture

## What's broken

`goc validate` warns `PLUGIN_AND_VENDORED_HOOKS_DOUBLE_FIRE` when the Claude
Code plugin is enabled and GoC's hooks are also vendored into
`.claude/settings.json`. It learns which scripts are GoC's from a parse of
`GOC_CLAUDE_HOOKS` it does by hand:

```python
def _goc_hook_basenames() -> set[str]:
    """The GoC lifecycle-hook script basenames, derived from the registry."""
    from goc.install import GOC_CLAUDE_HOOKS

    return {command.split("/")[-1].strip() for command in GOC_CLAUDE_HOOKS.values()}
```

The registry already has a single reader, and its docstring forbids exactly
this:

```python
def claude_hook_bindings() -> tuple[dict[str, set[str]], list[str]]:
    """`GOC_CLAUDE_HOOKS` inverted to script basename → the events it is bound to.

    Both hook validators read the registry through this one walk: [...]
    Keeping the command-to-script parse in one place is deliberate — the second
    reader of a hand-maintained registry is exactly where a divergent copy of
    the transform would otherwise start.
```

`claude_hook_bindings` extracts the script with `_HOOK_FILE_RE`
(`\$\{CLAUDE_PROJECT_DIR\}/(.+?\.py)`), which stops at `.py`. The stray parse
takes everything after the last `/`, so it keeps whatever follows the script
name. For today's unquoted commands the two agree. Under the quoted form
`python3 "${CLAUDE_PROJECT_DIR}/.claude/hooks/deck_session_start.py"` every
stray name ends in `"`. `_vendored_goc_hooks_registered` then looks for
`.claude/hooks/deck_session_start.py"` in `json.dumps` of the settings, where
the quoted command appears escaped as `.../deck_session_start.py\"`. It finds
nothing, and the warning never fires.

The regression test cannot notice. Its `VENDORED_HOOKS` fixture hardcodes the
unquoted command, and `json.dumps` puts the JSON string's own closing quote
right after `.py`. So the fixture still contains `.../deck_session_start.py"`,
and the test passes because of that coincidence, while a consumer whose
settings hold the quoted command gets no warning.

## Empirical evidence

`uv run python .game-of-cards/deck/double-fire-warning-goes-silent-once-hook-commands-quote-their-script-path/reproduce.py`
writes the vendored registrations through `_merge_claude_settings` (the real
install writer), enables the plugin in a scratch home, and runs the validator.
It does this once with the registry as shipped and once with the script paths
quoted. Output before the fix:

```
[registry as shipped]
  sample command               : python3 ${CLAUDE_PROJECT_DIR}/.claude/hooks/deck_session_start.py
  claude_hook_bindings names   : ['deck_prompt_router.py', 'deck_session_start.py', 'pattern_generalization_check.py']
  _goc_hook_basenames names    : ['deck_prompt_router.py', 'deck_session_start.py', 'pattern_generalization_check.py']
  double-fire warnings (want 1): 1
[registry with quoted script paths]
  sample command               : python3 "${CLAUDE_PROJECT_DIR}/.claude/hooks/deck_session_start.py"
  claude_hook_bindings names   : ['deck_prompt_router.py', 'deck_session_start.py', 'pattern_generalization_check.py']
  _goc_hook_basenames names    : ['deck_prompt_router.py"', 'deck_session_start.py"', 'pattern_generalization_check.py"']
  double-fire warnings (want 1): 0
  existing double-fire suite under the quoted registry: 8 run, 0 failed, 0 errors
DEFECT: _goc_hook_basenames diverges from claude_hook_bindings under the quoted registry and the plugin+vendored double-fire warning goes silent
exit=1
```

After the fix, exit 0. The suite line now counts the three new cases:

```
[registry with quoted script paths]
  sample command               : python3 "${CLAUDE_PROJECT_DIR}/.claude/hooks/deck_session_start.py"
  claude_hook_bindings names   : ['deck_prompt_router.py', 'deck_session_start.py', 'pattern_generalization_check.py']
  _goc_hook_basenames names    : ['deck_prompt_router.py', 'deck_session_start.py', 'pattern_generalization_check.py']
  double-fire warnings (want 1): 1
  existing double-fire suite under the quoted registry: 11 run, 0 failed, 0 errors
OK: both parses agree and the double-fire warning survives the quoted registry
```

## Why it matters

The quoted form is not hypothetical. It is the determined fix of
[hook-command-registrations-word-split-on-install-paths-with-spaces](../hook-command-registrations-word-split-on-install-paths-with-spaces/),
which is parked only on how to migrate existing installs. That card checked
the readers that go through `_HOOK_FILE_RE` and concluded "GoC-managed entry
detection survives". This reader does not use `_HOOK_FILE_RE`, so it is the
one that breaks. Landing that fix as written would turn off the double-fire
warning for every consumer who installs or upgrades afterwards, with CI green.
A double-registered hook fires twice per turn: two session primers, two
prompt-router reminders, and a Stop hook that can block twice. This warning is
the only thing that names that state
([goc-validate-misses-plugin-and-vendored-hook-double-registration](../goc-validate-misses-plugin-and-vendored-hook-double-registration/)).

The edge to the spaces card records the ordering: this fix has to land first
(or alongside it) for that card's quoting change to be safe.

This is not another instance of the reimplementation-drift families. The
consolidation for this registry already exists.
[nothing-checks-which-event-a-hook-is-bound-to-across-the-three-registries](../nothing-checks-which-event-a-hook-is-bound-to-across-the-three-registries/)
moved the two validators it knew about onto `claude_hook_bindings` and missed
this third reader, which an earlier card had added. Routing the third reader
through the same walk finishes that consolidation.

## Fix (applied)

- `goc/engine.py:5851`: `_goc_hook_basenames` now returns the keys of
  `claude_hook_bindings()[0]` and no longer splits commands itself. A command
  with no recognizable script path is already reported by
  `validate_hook_registration` through that walk's error list, so dropping it
  here loses nothing. The old parse returned the whole command string as a
  "basename" in that case.
- `goc/install.py:618`: the `claude_hook_bindings` docstring names all three
  readers instead of "both hook validators", and records how the third one
  drifted.
- `tests/test_validate_plugin_hook_double_fire.py`: three new cases.
  - `test_installed_registry_warns` and `test_installed_quoted_registry_warns`
    write the settings through `_merge_claude_settings` instead of a
    hand-copied fixture, the second with `GOC_CLAUDE_HOOKS` patched to the
    quoted form. Both assert the warning fires and names every script.
  - `test_hook_names_come_from_claude_hook_bindings` pins
    `_goc_hook_basenames()` to the walk's names under both the shipped and the
    quoted registry.

  Against the old parse, the quoted-install case failed with `0 != 1` and the
  pin failed on `'deck_session_start.py"'` and the two other quote-suffixed
  names.
