---
title: goc-decide-corrupts-decision-text-via-regex-replacement-template
summary: "`goc decide` routes the user's --decision/--reasoning text into `replace_or_append_decision`, which hands it to `re.sub` as the replacement template. Python parses backslash escapes there: `\\p` (e.g. a Windows path `C:\\path`) raises `re.error` and crashes the command; `\\1` silently expands to a captured group, mangling the recorded decision. Third sibling of the regex-replacement-template family; fix mirrors the already-shipped `lambda _:` guard at engine.py:336."
status: done
stage: null
contribution: medium
created: "2026-05-27T01:05:42Z"
closed_at: "2026-05-27T01:10:50Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero — both the crash variant (`C:\path`) and the group-reference variant (`go \1 ahead`) preserve the decision text verbatim.
  - [x] MECHANICAL: `replace_or_append_decision` (engine.py:356) replaces the bare-template `.sub(block, ...)` with the opaque `.sub(lambda _: block, ...)` form, mirroring the shipped fix at engine.py:336.
  - [x] EMPIRICAL: a real `goc decide --decision "Use C:\path" --reasoning "go \1 ahead"` against a parked test card records the literal text in the rewritten README (no crash, no group expansion).
  - [x] PROCESS: sibling sweep recorded in log.md — confirm no other `pattern.sub(<dynamic-template>, ...)` site remains unfixed across engine.py / install.py.
worker: {who: "claude[bot]", where: main}
---

# goc decide corrupts decision text via regex replacement template

## Location

`goc/engine.py:356`, inside `replace_or_append_decision`:

```python
def replace_or_append_decision(body: str, decision: str, reasoning: str, today: str) -> str:
    """Replace `## Decision required` with `## Decision`, or append a new section."""
    block = f"## Decision\n\n*Resolved {today}:* {decision}\n\n*Reasoning:* {reasoning}\n"
    if DECISION_REQUIRED_RE.search(body):
        return DECISION_REQUIRED_RE.sub(block, body, count=1)   # ← line 356
    return body.rstrip("\n") + "\n\n" + block
```

Live caller: `_cmd_decide` (engine.py:4091) passes `args.decision` /
`args.reasoning` — raw CLI strings from
`goc decide --decision "..." --reasoning "..."` — straight through.

## What's broken

`block` embeds the user-supplied `decision` and `reasoning`, then is passed
as the **second argument** to `re.sub`, which Python treats as a *replacement
template*. The `re` engine parses backslash sequences in a replacement
template:

- `\1`..`\99` and `\g<name>` → group back-references (silently substituted)
- an unknown escape like `\p` → `re.error: bad escape`

So a perfectly ordinary decision — a Windows path, a regex snippet, a
LaTeX fragment, anything with a backslash — either crashes `goc decide`
or silently rewrites the recorded decision.

This is the **third sibling** of a known family. The two prior siblings
are closed and document the exact same root-cause shape:

- [mutate-frontmatter-field-corrupts-backslashes-via-regex-replacement-template](../mutate-frontmatter-field-corrupts-backslashes-via-regex-replacement-template/)
  (done) — fixed engine.py:336 by switching to `.sub(lambda _: repl, ...)`.
- [append-marker-block-treats-briefing-text-as-regex-replacement-template](../append-marker-block-treats-briefing-text-as-regex-replacement-template/)
  (done) — same fix in install.py.

Neither sweep reached engine.py:356, so this site still uses the bare
template form. The fix at engine.py:336 is right next door and shows
the correct idiom:

```python
fm_text = pattern.sub(lambda _: f"{field_name}: {new_value}", fm_text, count=1)
```

## Empirical evidence

`uv run python .game-of-cards/deck/goc-decide-corrupts-decision-text-via-regex-replacement-template/reproduce.py`:

```
[A] CRASH: decision 'Use C:\path' raised error: bad escape \p at position 42 (line 3, column 30)
[B] CORRUPTED: literal 'go \1 ahead' not found; output was:
    '## Decision\n\n*Resolved 2026-05-27:* go \nPick a path.\n ahead\n\n*Reasoning:* reason\n'

DEFECT CONFIRMED: 2/2 variants mangled the decision text.
```

Variant B is the insidious one: `\1` expanded to captured group 1 — the
prior `## Decision required` body ("Pick a path.") — so the recorded
decision reads `go ` + the old section text + ` ahead`. No error, just a
quietly wrong permanent record.

## Why it matters

`goc decide` is the human's Andon-cord handoff: it records *what was
decided and why* on a parked card and lowers the gate so `pull-card` can
resume. A decision is a permanent record a cold reader trusts. A crash
blocks the handoff entirely; silent corruption is worse — the card looks
decided but the recorded text is wrong, and nothing flags it. Any
decision mentioning a path, a regex, or an escape sequence is exposed.

## Fix (applied)

Mirrored the engine.py:336 sibling — the replacement is now opaque so `re`
does no template parsing:

```python
return DECISION_REQUIRED_RE.sub(lambda _: block, body, count=1)
```

A lambda replacement receives the match object and returns the string
literally; no `\1` / `\p` interpretation. reproduce.py now exits 0, and a
real `goc decide --decision 'Use C:\path' --because 'go \1 ahead'` records
both strings verbatim. Full sibling re-sweep (see log.md) found no other
unfixed dynamic-template `.sub` site: the `_move_text_rewrite` sites
(engine.py:3945/3952) take a slug constrained to `[a-z0-9-]`, so no
backslash escape can reach them.
