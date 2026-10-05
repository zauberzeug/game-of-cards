---
title: agents-md-says-goc-validate-checks-hook-entries-in-claude-settings
summary: "UNVERIFIED. AGENTS.md tells contributors to change GoC hook entries in goc/install.py, not in .claude/settings.json, because goc validate enforces the parity, but validate_hook_registration only compares the package's hook templates with GOC_CLAUDE_HOOKS and never reads settings.json. A hand-dropped or renamed registration therefore passes validate, contrary to the doc and to the closed card that wrote the sentence."
status: open
stage: null
contribution: high
created: "2026-10-05T01:32:49Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, documentation, unverified]
definition_of_done: |
  - [ ] TDD: a reproduce.py runs `goc install --agents claude --local-skills` in a scratch repo, drops the `Stop` registration from `.claude/settings.json`, renames the `SessionStart` script in its command, runs `goc validate`, and fails while `AGENTS.md` still credits `goc validate` with enforcing that parity and validate exits 0 — or the run disproves the hypothesis and the card flips to `disproved`
  - [ ] MECHANICAL: `AGENTS.md:248-250` no longer says `goc validate` enforces the parity; it names what does keep the GoC entries in line (the `goc install` / `goc upgrade` merge from `GOC_CLAUDE_HOOKS`), as `tests/test_precommit_hook_reachability.py:74-80` already describes
  - [ ] PROCESS: the closed `agents-md-mislabels-claude-settings-json-as-user-owned-permission-list` gets a post-close pointer to this card; drop the `unverified` tag once reproduce.py lands
---

# AGENTS.md says goc validate checks the hook entries in `.claude/settings.json`

> **UNVERIFIED.** Surfaced by the general-purpose hunter of the 2026-10-05
> audit-deck pass. The filing agent re-read the citations and ran the
> scratch-repo check by hand (below). No `reproduce.py` was written this round;
> the falsification recipe is below.

## Location

- `AGENTS.md:248-250`: "ownership is shared — the `hooks` entries whose command
  matches `GOC_CLAUDE_HOOKS` are goc-owned (change them in `goc/install.py`, not
  in `.claude/settings.json`, and `goc validate` enforces the parity)".
- `goc/engine.py:1484-1520`: `validate_hook_registration`, the check that
  sentence means. It compares `PACKAGE_DIR / "templates" / "hooks"` with
  `GOC_CLAUDE_HOOKS` and nothing else.
- `goc/engine.py:5708-5738`: `validate_plugin_hook_double_fire`, the only
  validate step that opens `.claude/settings.json`. It is advisory and asks one
  question: are GoC hooks vendored there while the plugin is enabled?
- `tests/test_precommit_hook_reachability.py:74-80` already says so: "the
  `hooks` block of `.claude/settings.json` — `validate_hook_registration` checks
  the *package's* templates against `GOC_CLAUDE_HOOKS` and never reads the
  consumer's copies".
- Origin of the sentence: the closed
  [agents-md-mislabels-claude-settings-json-as-user-owned-permission-list](../agents-md-mislabels-claude-settings-json-as-user-owned-permission-list/)
  (`README.md:56-58`, "`goc validate` then enforces registration parity against
  that map", and `:119-122`, "`goc validate` reports a hook-registration
  mismatch against `GOC_CLAUDE_HOOKS` if the edit renamed or dropped one").

## Hypothesis

The sentence reads as a safety net: hand-edit the GoC entries in
`.claude/settings.json` and `goc validate` will catch it. Nothing reads those
entries for parity, so the net is not there.

Run by hand in a scratch repo:

```
$ goc install --agents claude --local-skills && goc validate      # exit 0
# drop the Stop registration; point SessionStart at deck_session_start_RENAMED.py
events before: ['SessionStart', 'Stop', 'UserPromptSubmit']
events after:  ['SessionStart', 'UserPromptSubmit']
$ goc validate
No cards found in /tmp/h3/.game-of-cards/deck — validated 0 cards (structural checks still ran).
                                                                  # exit 0
```

The hunter reports the same in a clone of this repo: `goc validate` and
`scripts/sync_plugin_assets.py --check` both exit 0 after the same edit.

## Why it matters

`AGENTS.md` is read cold by every agent working here, and this sentence answers
"which files may I hand-edit?". A contributor who trusts it believes a broken
registration fails CI. In fact the hook silently stops firing, or fires a
script that does not exist, with every check green. In a vendored repo that is
the whole hook set: session-start reminder, prompt router, pattern check.

This is a doc-accuracy instance — a doc restating what a check does, written
from the doc's own premise rather than from the code. If confirmed, connect it
to
[doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them](../doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them/).

## Falsification recipe

1. In a scratch `git init` repo: `goc install --agents claude --local-skills`;
   `goc validate` (expect exit 0).
2. Edit `.claude/settings.json`: remove the `Stop` entry and rename the
   `SessionStart` command's script.
3. `goc validate`: exit 0 confirms the hypothesis; a hook-registration error
   disproves it.

## Fix sketch

Rewrite the sentence to what the code does. The repo's own test already chose
not to read the consumer's settings (`tests/test_precommit_hook_reachability.py:74-80`),
so the doc should move to the code, not the other way round. A vendored-mode
check that compares `.claude/settings.json` with `GOC_CLAUDE_HOOKS` (ignoring
non-GoC entries, inert in plugin mode) would be a new feature. File it
separately if anyone wants it.
