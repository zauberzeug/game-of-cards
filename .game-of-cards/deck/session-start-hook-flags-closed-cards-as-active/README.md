---
title: session-start-hook-flags-closed-cards-as-active
summary: "SessionStart hook (`deck_session_start.py`) flags closed cards as active because it substring-matches `status: active` against the full README body, not just frontmatter. Any card whose body discusses status semantics (code quote, code block, or prose) gets falsely reported. Replace the substring scan with a proper YAML-frontmatter parse."
status: done
stage: null
contribution: medium
created: 2026-05-09
closed_at: 2026-05-09
human_gate: none
advances: []
advanced_by: []
tags: [bug, meta-fix]
definition_of_done: |
  - [x] `deck_session_start.py` no longer flags a card as active unless the YAML frontmatter's `status` field is literally `active`. References to the string `status: active` inside the card body (code quotes, code blocks, prose) MUST NOT trigger the active-card reminder.
  - [x] A regression case is added: a card whose frontmatter says `status: done` but whose body contains a backtick-wrapped or fenced-code reference to `status: active` is correctly excluded from the SessionStart reminder. Demonstrate via a unit test, a script invocation, or — at minimum — a `.game-of-cards/deck/<fixture>/README.md` fixture exercised in CI.
  - [x] All four file copies updated in lockstep: `goc/templates/hooks/deck_session_start.py` (source of truth), `.claude/hooks/deck_session_start.py`, `claude-plugin/hooks/deck_session_start.py`, `claude-plugin/goc/templates/hooks/deck_session_start.py`. The byte-for-byte CI tripwire (introduced in `bf40f68`) will fail the build if the four diverge.
  - [x] The hook's behavior matches `goc --status active` exactly on the current repo's deck (no false positives, no false negatives).
  - [x] `uv run goc validate` passes.
  - [x] Manual verification: `python3 .claude/hooks/deck_session_start.py` prints the same active-card list as `goc --status active` returns titles for.
worker: {who: "claude[bot]", where: main}
---

# session-start-hook-flags-closed-cards-as-active

## Reproduction

In a repo where any card's body contains the substring `status: active`
(in prose, a backtick code quote, a fenced code block, or a docstring),
the SessionStart hook flags that card as active even when its
frontmatter `status` field is something else.

Concrete instance observed on 2026-05-09:

- `.game-of-cards/deck/surface-active-cards-in-board/README.md` had
  `status: done` in its frontmatter (closed 2026-05-04).
- Line 27 of that file's body read: `Parallel GoC sessions rely on
  \`status: active\` as the soft lock. During a...`
- The SessionStart hook reported the card as active in the
  session-start reminder.

## Root cause

`goc/templates/hooks/deck_session_start.py` line 32:

```python
if "status: active" in readme.read_text():
    active_cards.append(card_dir.name)
```

The hook reads the entire README and substring-matches `status: active`
against it. The match is body-blind: prose, code quotes, and fenced
code blocks all count.

The rest of the toolchain (`goc --status active`, the engine's card
loader in `goc/engine.py`) parses the YAML frontmatter properly and
inspects the `status` field. Only this hook re-implements a "fast"
shortcut that drifts from the source of truth.

## Suggested fix (the implementer can pick)

**Option A — Inline frontmatter parse.** Read the file, split on the
first two `---` delimiters, parse the block in between with
`yaml.safe_load` (or the engine's frontmatter helper if exposed), then
check `data.get("status") == "active"`. Standalone, no engine import.

**Option B — Reuse the engine.** Import `goc.engine.iter_cards` (or
the equivalent) and filter on its returned objects. Single source of
truth; depends on the engine being importable from the hook script
(it already is, since the plugin bundles `claude-plugin/goc/`).

**Option C — Shell out to `goc`.** Invoke `goc --status active` (or a
JSON variant if one exists) and parse stdout. Highest fidelity, slowest,
adds a process-spawn cost to every session start.

Option A is the lightest change and avoids coupling the hook to the
engine package layout. Option B is the cleanest if the engine exposes a
stable iterator. Whichever is chosen, the DoD's behavioural assertion
(matches `goc --status active` exactly) is the binding contract.

## Failure modes the fix should also close

The substring heuristic produces both false positives and false
negatives. While fixing this, also handle:

- **False negative — trailing comment.** A frontmatter line like
  `status: active  # claimed by foo` would not match the literal
  substring `status: active` if any tool ever emits a trailing comment.
  A real YAML parser handles this without special-casing.
- **False positive — body match.** Already covered by the primary case.
- **False positive — alternative key.** A line like
  `original_status: active` would substring-match. A real parser
  inspects the `status` key only.

## Why this matters

The SessionStart reminder is the first piece of GoC context an agent
sees in a new session. A false-positive reminder pushes the agent
toward "resume or close before starting new work" against a card that
is already closed — wasting a turn or two clarifying. A false negative
risks the opposite: starting parallel work on a card that is already
claimed by another session.

This is also a teaching case for the project: when a hook implements a
shortcut around the engine's parser, it can drift silently. Worth
noting in the broader hook-development guidance whenever one is added.

## Out of scope

- Changing the hook's *contract* (what it reports, when it runs).
  The current contract — print active cards at session start, silent
  when none — is correct. Only the implementation is wrong.
- Refactoring the other GoC hooks (`deck_prompt_router.py`,
  `pattern_generalization_check.py`). They have their own concerns and
  already use proper parsing where applicable. If a similar audit
  surfaces issues there, file separate cards.
