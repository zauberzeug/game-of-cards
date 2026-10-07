---
title: goc-validate-crashes-in-a-repo-that-has-its-own-plugin-folder
summary: "goc validate's plugin-mirror and hook-registration checks treated any project root holding a claude-plugin/ or codex-plugin/ folder as the goc source tree. A consuming repo that keeps its own plugin under one of those names got an uncaught FileNotFoundError on <root>/goc/templates/skills, so the installed pre-commit hook failed every commit, and its own hooks.json drew two false hook-registration errors. Fixed: both checks now gate on goc/templates/ at the project root, the tree the payloads are built from."
status: done
stage: null
contribution: high
created: "2026-10-05T01:32:49Z"
closed_at: "2026-10-07T05:06:36Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: a reproduce.py runs `goc install --agents claude` in a scratch git repo, adds `claude-plugin/.claude-plugin/plugin.json` (then, separately, only `codex-plugin/skills/<x>/SKILL.md`), and asserts `goc validate` exits 0 with no traceback — or the run disproves the hypothesis and the card flips to `disproved`
  - [x] TDD: a regression test pins that `validate_plugin_mirror_parity` and `validate_plugin_hook_registration` stay silent in a consuming repo that has a payload-named folder but no goc source tree, beside the existing absent-folder case in `tests/test_plugin_hook_json_registration.py`
  - [x] MECHANICAL: both checks tell the goc source tree from a consuming repo by something other than a folder name, so the "inert in consuming repos" sentences in `AGENTS.md` and `goc/engine.py` hold; drop the `unverified` tag once reproduce.py lands
worker: {who: "claude[bot]", where: main}
---

# goc validate crashes in a repo that has its own plugin folder

> **Confirmed and fixed 2026-10-07.** Filed UNVERIFIED by the 2026-10-05
> audit-deck pass. `reproduce.py` exited 1 before the fix: a traceback for both
> payload folders, and two false errors from the hook check. It exits 0 after
> the fix. The hunter's claim about the hook check held too (see
> "What the run showed").

## Location

Line numbers are from before the fix. All in `goc/engine.py` unless noted:

- `:1754-1762`: the gate. `validate_plugin_mirror_parity` returned `[]` only
  when none of `REPO_ROOT / "claude-plugin"`, `"codex-plugin"`,
  `"openclaw-plugin"` existed.
- `:1800`: `templates_root = REPO_ROOT / "goc" / "templates"`, the goc source
  tree the rest of the function assumes.
- `:1822-1827`: Claude branch, `for p in skills_src.iterdir()` on
  `templates_root / "skills"`.
- `:1890`: Codex branch, `p.name for p in src.iterdir() if p.is_dir() and skill_for_agent(p.name, "codex")`.
- The contract it breaks: `:1727-1729` ("Only the pairs whose plugin root
  actually exists at REPO_ROOT are checked, so this works in both the goc
  source repo and downstream consumers.") and `AGENTS.md:221-222` ("The plugin
  check is gated on the payload root existing at the repo root, so it is inert
  in consuming repos.").
- Sibling: `validate_plugin_hook_registration` carried the same sentence
  (`:1631-1632`). It reads the *package's* templates, so it does not crash,
  but it walked a consumer's own `claude-plugin/hooks/hooks.json` against
  GoC's hook layout.
- The only consumer-side test: `tests/test_plugin_hook_json_registration.py:223-226`,
  `test_absent_payload_root_is_inert` — "Consuming repos have no `claude-plugin/`".
  That premise is what this card disproves.

## Hypothesis

The gate tests a folder name, not whether the project is the goc source tree.
A consuming repo that keeps its own Claude Code or Codex plugin in a folder with
the conventional name — the layout this repo documents for its own payloads —
passes the gate, and the walk then reads `<repo>/goc/templates/skills`, which
only the goc source tree has.

Run by hand (scratch `git init` repo, `goc` from this checkout):

```
$ goc install --agents claude && goc validate         # exit 0
$ mkdir -p claude-plugin/.claude-plugin
$ echo '{"name":"my-plugin","version":"1.0.0"}' > claude-plugin/.claude-plugin/plugin.json
$ goc validate
  ...
FileNotFoundError: [Errno 2] No such file or directory: '/tmp/h1/goc/templates/skills'
                                                        # exit 1
$ rm -rf claude-plugin && mkdir -p codex-plugin/skills/foo && echo x > codex-plugin/skills/foo/SKILL.md
$ goc validate
FileNotFoundError: [Errno 2] No such file or directory: '/tmp/h1/goc/templates/skills'
                                                        # exit 1
$ rm -rf codex-plugin && mkdir openclaw-plugin && echo '{}' > openclaw-plugin/openclaw.plugin.json
$ goc validate                                          # exit 0 — the OpenClaw-only case does not crash
```

## Why it matters

`goc install` writes a pre-commit stanza that runs `goc validate` with
`always_run: true` (`goc/install.py:82-87`). In an affected repo every commit
then fails with a traceback until the user disables the hook, and the error
names a path (`goc/templates/skills`) the user never had, with nothing pointing
at the folder that triggered it. Anyone building a Claude Code or Codex plugin
inside a GoC-managed repo under the folder names this project uses for its own
payloads hits it.

## Falsification recipe

1. In a scratch `git init` repo: `goc install --agents claude`, then
   `goc validate` (expect exit 0).
2. Add `claude-plugin/.claude-plugin/plugin.json` and run `goc validate`. A
   traceback and exit 1 confirm the hypothesis; exit 0 disproves it.
3. Repeat with only `codex-plugin/skills/<x>/SKILL.md`.
4. If confirmed, add a `claude-plugin/hooks/hooks.json` that registers the
   consumer's own script and call `validate_plugin_hook_registration()`, to
   settle the hunter's misreport claim.

`reproduce.py` runs these steps, with the engine from this checkout. It exits 0
only when every scenario leaves `goc validate` at exit 0, with no traceback and
no plugin-mirror or hook-registration error.

## What the run showed

Before the fix:

| Scenario | `goc validate` |
|---|---|
| fresh `goc install --agents claude` | exit 0 |
| only `claude-plugin/.claude-plugin/plugin.json` | exit 1, `FileNotFoundError: <repo>/goc/templates/skills` |
| only `codex-plugin/skills/foo/SKILL.md` | exit 1, same traceback |
| only `openclaw-plugin/openclaw.plugin.json` (control) | exit 0 |
| `claude-plugin/` with its own `hooks.json` | exit 1, the mirror crash comes first |

Hypothesis confirmed. Step 4 settles the hunter's claim about the hook check.
The consumer's plugin has one hook that imports a helper module beside it, and
a `SessionStart` command that runs a script kept in `scripts/`. Called on its
own, `validate_plugin_hook_registration()` reported both as defects:

```
hook registration: claude-plugin/hooks/_util.py is shipped in the plugin payload but no command in claude-plugin/hooks/hooks.json names it — the file would be installed and never invoked. Add an event entry.
hook registration: claude-plugin/hooks/hooks.json registers warm_cache.py, which claude-plugin/hooks/ does not ship — the hook would fail with 'no such file' on every fire. Drop the entry or restore the script.
```

Both rules belong to GoC's payload layout, where every `.py` under `hooks/` is
a registered hook. Neither holds for a consumer's plugin. So once the crash was
gone, `goc validate` would still have exited 1 in that repo. Both checks needed
the new gate.

After the fix every scenario exits 0. `validate_plugin_hook_registration()` on
its own returns `[]`.

## Fix (applied)

- `goc/engine.py`: a new `_is_goc_source_tree()` returns true when
  `REPO_ROOT / "goc" / "templates"` is a directory, the tree every payload is
  generated from. `validate_plugin_hook_registration` and
  `validate_plugin_mirror_parity` both return `[]` when it is false, before
  reading any payload folder. Nothing changes inside the source tree: the mirror
  check still compares only the payload roots that exist. Both docstrings now
  name the gate.
- Why `goc/templates/`: every comparison the two checks make reads its source
  side from there, so without it there is nothing to compare against. The
  package's own install also reads its templates from there, so the directory
  cannot quietly vanish from the source tree. Rejected alternatives:
  - Comparing `REPO_ROOT / "goc"` with the running engine's `PACKAGE_DIR`. A
    pipx-installed goc run in this repo would switch the tripwire off, and the
    mirror tests patch only `REPO_ROOT`.
  - The `pyproject.toml` project name. A fork under another name would lose
    the check, and reading TOML on Python 3.10 needs a hand-written parser.
  - The payload manifests. The checks exist to catch an incomplete payload,
    such as a fresh clone before the first sync.
- `AGENTS.md`, hook-registration paragraph under "Templates ship as package
  data": the gate sentence now names the source tree and says
  `validate_plugin_mirror_parity` shares the gate.
- `tests/test_plugin_hook_json_registration.py`:
  - New `test_consuming_repo_with_its_own_plugin_folder_is_inert`. It points
    `REPO_ROOT` at a consumer tree while the engine keeps its hook templates,
    and asserts both checks return `[]` for three layouts: a Claude manifest
    only, a Codex skill only, and a Claude plugin with its own `hooks.json`.
  - New `test_the_same_plugin_folder_is_checked_in_the_goc_source_tree`, the
    control. The same plugin draws errors from both checks once the tree has
    `goc/templates/`.
  - `test_absent_payload_root_is_inert` keeps its assertion. Its docstring no
    longer says consuming repos have no `claude-plugin/`.
  - The real-tree test now asserts the gate holds for this repo.
- `tests/test_plugin_mirror_parity.py`:
  - New `test_real_repo_is_the_goc_source_tree`, so `test_real_repo_passes`
    cannot pass by checking nothing.
  - The two OpenClaw fixtures used to build a `goc/` with no `templates/`. They
    now build one through `_engine_pair`, since a real source tree always has it.
- Mutation check. With the gate forced open, the consumer test fails on all
  three layouts with the original `FileNotFoundError`. With it open for the
  hook check only, the `hooks.json` layout fails with the two false errors. Each
  half of the test catches its own defect.

## Residual

A consuming repo that keeps its own `goc/templates/` directory at the root
still counts as the source tree. That could be an unrelated project folder or a
hand-copied goc package. No such repo is known, and a plugin author has no
reason to use that path.
