---
title: goc-validate-crashes-in-a-repo-that-has-its-own-plugin-folder
summary: "UNVERIFIED. goc validate's plugin-mirror check treats any project root holding a claude-plugin/ or codex-plugin/ folder as the goc source tree and iterates <root>/goc/templates/skills, which no consuming repo has, so a repo that keeps its own plugin under one of those names gets an uncaught FileNotFoundError and exit 1. The installed pre-commit hook runs goc validate on every commit, while AGENTS.md and the check's docstring both say it is inert in consuming repos."
status: open
stage: null
contribution: high
created: "2026-10-05T01:32:49Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, unverified]
definition_of_done: |
  - [ ] TDD: a reproduce.py runs `goc install --agents claude` in a scratch git repo, adds `claude-plugin/.claude-plugin/plugin.json` (then, separately, only `codex-plugin/skills/<x>/SKILL.md`), and asserts `goc validate` exits 0 with no traceback — or the run disproves the hypothesis and the card flips to `disproved`
  - [ ] TDD: a regression test pins that `validate_plugin_mirror_parity` and `validate_plugin_hook_registration` stay silent in a consuming repo that has a payload-named folder but no goc source tree, beside the existing absent-folder case in `tests/test_plugin_hook_json_registration.py`
  - [ ] MECHANICAL: both checks tell the goc source tree from a consuming repo by something other than a folder name, so the "inert in consuming repos" sentences in `AGENTS.md` and `goc/engine.py` hold; drop the `unverified` tag once reproduce.py lands
---

# goc validate crashes in a repo that has its own plugin folder

> **UNVERIFIED.** Surfaced by the general-purpose hunter of the 2026-10-05
> audit-deck pass. The filing agent re-read the citations and reproduced the
> crash by hand in a scratch repo (output below). No `reproduce.py` was written
> this round; the falsification recipe is below.

## Location

All in `goc/engine.py` unless noted:

- `:1754-1762`: the gate. `validate_plugin_mirror_parity` returns `[]` only
  when none of `REPO_ROOT / "claude-plugin"`, `"codex-plugin"`,
  `"openclaw-plugin"` exists.
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
- Sibling: `validate_plugin_hook_registration` carries the same sentence
  (`:1631-1632`). It reads the *package's* templates, so it does not crash,
  but it walks a consumer's own `claude-plugin/hooks/hooks.json` against GoC's
  hook set. The hunter reports it then flags the consumer's own helper module
  as an unregistered GoC hook; not re-run by the filing agent.
- The only consumer-side test: `tests/test_plugin_hook_json_registration.py:223-226`,
  `test_absent_payload_root_is_inert` — "Consuming repos have no `claude-plugin/`".

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

## Fix sketch

Gate both plugin checks on the goc source tree, not on a payload-named folder —
for example, require `REPO_ROOT / "goc" / "templates"` before comparing
anything. Keep `test_absent_payload_root_is_inert` and add the
present-folder, absent-source case beside it.
