---
title: plugin-payload-hooks-json-never-registers-a-newly-added-hook-script
summary: "`claude-plugin/hooks/hooks.json` and `codex-plugin/hooks/hooks.json` are the event registries for the default (plugin) install path, and nothing ties them to `goc/templates/hooks/*.py`. `validate_hook_registration` enforces exactly that script-to-registration invariant, but only for `GOC_CLAUDE_HOOKS` — the vendored `--local-skills` path — so adding a hook template ships it into both plugin payloads as a file no host ever invokes, with `goc validate`, `sync_plugin_assets.py --check` and all 964 regression tests green. Retiring one leaves the inverse: both registries keep a command pointing at a script the sync has already pruned."
status: done
stage: null
contribution: medium
created: "2026-08-13T05:28:56Z"
closed_at: "2026-08-13T05:37:34Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, test]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero — a hook template added to `goc/templates/hooks/` is registered in both plugin `hooks.json` files, and no registration points at a script the payload does not ship
  - [x] MECHANICAL: the parity check lands in `goc/engine.py` beside `validate_hook_registration` and `validate_plugin_mirror_parity`, gated on the payload roots existing at `REPO_ROOT` so it stays inert in consuming repos
  - [x] TDD: a regression test drives BOTH directions (shipped-but-unregistered, registered-but-not-shipped) and asserts each produces an error; a control asserts the shipped tree is clean
  - [x] TDD: the check parses a malformed `hooks.json` (non-dict root, non-list event value, non-dict hook entry) without raising — matching the defensive posture of the other JSON loaders in this repo
  - [x] MECHANICAL: `AGENTS.md`'s hook-derivation paragraph names the two plugin registries as covered, so the next reader is not told the guard is broader than it is
  - [x] PROCESS: `uv run python -m unittest discover -s tests` and `uv run goc validate` both run, and any pre-existing failure is named rather than absorbed
---

# A new hook script ships into both plugin payloads without ever being registered

## Location

- `goc/engine.py:1351` — `validate_hook_registration`, the guard that
  enforces script ↔ registration parity for the **vendored** path only.
- `goc/engine.py:1427` — `validate_plugin_mirror_parity`, which copies the
  payloads byte-for-byte and whose docstring records the exclusion:
  *"The hand-maintained `hooks.json` is excluded from that comparison."*
- `claude-plugin/hooks/hooks.json`, `codex-plugin/hooks/hooks.json` — the two
  unguarded registries.
- `goc/install.py:541` — `GOC_CLAUDE_HOOKS`, the registry that *is* guarded.

## What's broken

Hook scripts live in `goc/templates/hooks/*.py`. Reaching a running agent takes
two things: the **file** has to be copied into whatever tree the host reads, and
an **event registration** has to point at it. There are three registries, and
only one of them is checked.

`validate_hook_registration` states the invariant precisely, for `GOC_CLAUDE_HOOKS`:

```python
# goc/engine.py:1389
for name in sorted(scripts - registered):
    errors.append(
        f"hook registration: templates/hooks/{name} has no event entry in "
        "GOC_CLAUDE_HOOKS — file would be copied to .claude/hooks/ but never "
        "invoked. Add a mapping in goc/install.py."
    )
```

"Copied but never invoked" is exactly the failure mode. `GOC_CLAUDE_HOOKS`
drives `.claude/settings.json` on the `--local-skills` install — the *opt-in
minority* path. The **default** path writes `skills_source: plugin`, and there
the registry is `claude-plugin/hooks/hooks.json` (or `codex-plugin/`'s), which
nothing compares against `goc/templates/hooks/`.

The sync widens the gap rather than closing it. `scripts/sync_plugin_assets.py`
copies the hook *files* into all three flat mirrors and protects `hooks.json`
from being pruned as a non-source file (`preserve_files`), so the registry is
deliberately left behind while the files move. `validate_plugin_mirror_parity`
records the same exclusion in prose (quoted above). Both are correct decisions
in isolation — `hooks.json` carries host-specific command grammar that is not
derivable from a template name — but between them no mechanism owns the
question "is every shipped script actually registered?".

## Empirical evidence

`uv run python .game-of-cards/deck/plugin-payload-hooks-json-never-registers-a-newly-added-hook-script/reproduce.py`
stages the repo into a temp dir, adds (then, in a second tree, removes) a hook
template, runs the real sync script, and asks `goc validate`'s hook guards what
they noticed. The drift the sync produces is unchanged by the fix — that is the
input, not the bug; what changed is whether anything reports it:

```
plugin hooks.json ← goc/templates/hooks/ registration parity

  ADDED goc/templates/hooks/probe_new_hook.py, then ran sync_plugin_assets.py

    claude-plugin  ships the file: True   hooks.json registers it: False
    codex-plugin   ships the file: True   hooks.json registers it: False

    reported by goc validate's guards: True

  REMOVED goc/templates/hooks/deck_prompt_router.py, then ran sync_plugin_assets.py

    claude-plugin  ships the file: False  hooks.json registers it: True
    codex-plugin   ships the file: False  hooks.json registers it: True

    reported by goc validate's guards: True

  CONTROL — untouched tree, hook-registration errors: 0

OK — a shipped-but-unregistered hook script and a registration pointing
at a pruned one are both reported, and the shipped tree stays clean.
```

Both `reported by` lines read `False` before the fix, and the run exits 1 —
confirmed by re-running the same script with `validate_plugin_hook_registration`
deleted from the module, which reproduces the original verdict:

```
DEFECT PRESENT — the two plugin hooks.json registries are unguarded:
  - a payload shipping an unregistered probe_new_hook.py goes unreported
  - a registration pointing at pruned deck_prompt_router.py goes unreported
```

What the pre-fix tree looked like to every other mechanism, measured with a
fourth hook template added and a `GOC_CLAUDE_HOOKS` entry supplied so the one
existing guard was satisfied:

| mechanism | verdict |
|---|---|
| `python3 scripts/sync_plugin_assets.py --check` | OK (exit 0) |
| `goc validate` | clean (exit 0) |
| `python -m unittest discover -s tests` | 964 tests, only the pre-existing `test_canonical_tag_rows` failure |

So the hook shipped into both plugin payloads as a dead file with every tripwire
in the repo green.

## Why it matters

The reachability path is the ordinary one: a maintainer drops a `.py` into
`goc/templates/hooks/`, adds the `GOC_CLAUDE_HOOKS` line the one existing guard
demands, runs `pre-commit` (which syncs the payloads), and ships. Nothing asks
for the plugin-side registration, and nothing reports its absence. The hook then
works for `--local-skills` installs and silently does nothing for everyone else.

Silence is the whole cost. A hook that never fires is indistinguishable from a
hook that fires and has nothing to say — which is precisely how
[pattern-generalization-hook-missing-from-local-skills-install](../pattern-generalization-hook-missing-from-local-skills-install/)
(closed 2026-05-09, `contribution: high`) went unnoticed. That card is this one
with the two sides swapped: there the script was *registered but not shipped*,
and the fix added the file-copy plus a `validate_plugin_mirror_parity` pair.
Here the script is *shipped but not registered*, on the path that card noted was
unaffected — "Plugin-path users are unaffected because
`claude-plugin/hooks/pattern_generalization_check.py` is a real file and is
auto-discovered." Auto-discovery of the *file* is not registration of the
*event*; `hooks.json` is what the host reads.

The direct predecessor is
[derive-claude-hook-manifest-from-templates](../derive-claude-hook-manifest-from-templates/)
(closed 2026-05-09), which found the hook list hand-maintained in three places
and closed by deriving two and tripwiring the third. Its enumeration —
`goc/templates/agents/claude/manifest.json`, `GOC_CLAUDE_HOOKS`,
`validate_plugin_mirror_parity` — predates the plugin payloads carrying their
own `hooks.json`. Those two files are the fourth and fifth registration sites,
and they inherited neither the derivation nor the tripwire. This card is that
card's forward pointer.

Distinct from
[sync-mechanisms-reimplement-orphan-pruning-and-drift-detection-and-keep-drifting](../sync-mechanisms-reimplement-orphan-pruning-and-drift-detection-and-keep-drifting/):
that umbrella is about the two sync mechanisms each reimplementing orphan
pruning. `hooks.json` is not an orphan — the sync deliberately preserves it. The
gap is a registry with no parity check, not a prune that misses a file.

## Fix (applied)

`validate_plugin_hook_registration` in `goc/engine.py`, sitting between
`validate_hook_registration` and `validate_plugin_mirror_parity` and wired into
`_cmd_validate` beside them:

- For each of `claude-plugin/hooks/hooks.json` and `codex-plugin/hooks/hooks.json`
  that exists at `REPO_ROOT`, `_plugin_registered_hook_scripts` collects every
  `.py` basename the commands mention. Claude's command names the script once
  (`python3 ${CLAUDE_PLUGIN_ROOT}/hooks/<name>.py`); Codex's version-fallback
  shell wrapper names it three times, so a set collapses both shapes without
  either grammar being hard-coded.
- Every script the payload ships must appear in that set (`shipped -
  registered` → "installed and never invoked"), and every name in that set must
  exist in `<plugin>/hooks/` (`registered - shipped` → "fails with 'no such
  file' on every fire"). When the payload's hook dir is absent — a fresh clone
  before the sync has copied anything — the template set stands in for it.
- Parsing is defensive at each level: a non-dict root, a non-list event value, a
  group without a `hooks` list, an entry without a string `command`, and
  unparseable JSON each produce a diagnostic rather than a traceback. This repo
  has a standing family of cards about loaders that trusted their input shape
  ([claude-settings-json-that-parses-to-a-non-dict-crashes-install-with-attributeerror](../claude-settings-json-that-parses-to-a-non-dict-crashes-install-with-attributeerror/)
  and siblings); a new loader should not join it.

OpenClaw is deliberately outside `PLUGIN_HOOK_REGISTRIES`: it reimplements the
deck hooks in TypeScript inside `openclaw-plugin/index.ts` and ships no
`hooks.json`.

Engine placement rather than a repo-local test, for two reasons: the adjacent
invariants (`validate_hook_registration`, `validate_plugin_mirror_parity`) both
already live there and are both already gated on payload presence, so this is a
third case of an established pattern rather than a new mechanism; and splitting
one invariant across `goc validate` and `tests/` is the exact shape the
sync-mechanisms umbrella exists to complain about. The check is inert in
consuming repos, which have no `claude-plugin/` directory — same as
`validate_plugin_mirror_parity`, and pinned by
`test_absent_payload_root_is_inert`.

Generating `hooks.json` from the templates was deliberately **not** the fix.
AGENTS.md already records both files as hand-maintained, and their contents are
not derivable from a template name: Codex carries per-event `statusMessage`
strings and a version-fallback shell wrapper, Claude uses a different root
variable. The registry stays authored; only the parity is now checked.

`tests/test_plugin_hook_json_registration.py` drives both drift directions
against a synthetic tree, the Codex shell-wrapper command shape, eight
malformed-registry shapes, the absent-payload case, and the live payloads.
