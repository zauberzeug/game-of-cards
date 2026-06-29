---
title: session-start-hook-shows-gated-active-cards-as-resumable
summary: "SessionStart hook (`deck_session_start.py`) lists every `status: active` card with the same `resume or close before starting new work` framing — even cards parked behind `human_gate: session` or `human_gate: decision`, which the agent cannot resume (only the human can lower the gate). The hook ignores `human_gate` entirely, conflating agent-resumable work with human-blocked parked work."
status: done
stage: null
contribution: medium
created: "2026-05-29T08:06:58Z"
closed_at: "2026-05-29T09:18:43Z"
human_gate: none
advances:
  - active-state-conflates-being-worked-on-with-parked-at-human-gate
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [x] MECHANICAL: `deck_session_start.py` distinguishes agent-resumable active cards (`human_gate: none`) from human-parked active cards (`human_gate: decision` or `session`). Either filter the parked ones out of the reminder, or label them separately so the agent does not read `resume or close` advice for cards it cannot resume.
  - [x] TDD: a unit/regression test exercises the hook on a fixture deck containing (a) one `status: active`, `human_gate: none` card, (b) one `status: active`, `human_gate: decision` card, (c) one `status: active`, `human_gate: session` card. The test asserts the hook's output matches the chosen framing — at minimum the `gate: none` card is the only one labeled as resumable.
  - [x] MECHANICAL: all four file copies updated in lockstep (source-of-truth + auto-synced mirrors): `goc/templates/hooks/deck_session_start.py`, `.claude/hooks/deck_session_start.py`, `claude-plugin/hooks/deck_session_start.py`, `codex-plugin/hooks/deck_session_start.py`. The byte-for-byte mirror tripwire in CI catches drift if any are missed.
  - [x] MECHANICAL: the OpenClaw TypeScript port of this hook in `openclaw-plugin/index.ts` is updated to match — same `human_gate` filtering semantics. (The OpenClaw hook is hand-ported, not auto-synced; verify by re-reading `index.ts` after the change.)
  - [x] PROCESS: `uv run goc validate` passes.
worker: {who: "claude[bot]", where: main}
---

# SessionStart hook flags gated active cards with the same "resume" framing as truly resumable ones

## Location

`goc/templates/hooks/deck_session_start.py:48-71` (and three mirrored copies — see DoD).

## What's broken

The SessionStart hook scans the deck, collects every card whose YAML
frontmatter `status` is `active`, and prints:

```text
[GoC] Active card(s): <titles> — resume or close before starting new work.
```

The hook never inspects `human_gate`. So an `active` card that has been
parked behind `human_gate: decision` or `human_gate: session` — i.e. the
agent who claimed the card raised a gate during its session and stopped
working pending human input — is reported with the exact same
`resume or close` framing as an `active` card with `human_gate: none`
that another agent could legitimately pick up and finish.

Quoted code (the entire collection loop):

```python
# goc/templates/hooks/deck_session_start.py:58-71
active_cards = []
for card_dir in sorted(deck_dir.iterdir()):
    if not card_dir.is_dir():
        continue
    readme = card_dir / "README.md"
    if not readme.is_file():
        continue
    if _card_status(readme) == "active":
        active_cards.append(card_dir.name)

if active_cards:
    cards_str = ", ".join(active_cards)
    print(f"[GoC] Active card(s): {cards_str} — resume or close before starting new work.")
return 0
```

`_card_status` only reads the `status:` line; the hook never parses
`human_gate:` at all.

## Reachability path

Both surfaces this hook drives are user-visible every session:

- Claude Code's `SessionStart` event runs the hook on every fresh
  session (registered in `claude-plugin/hooks/hooks.json` and in the
  consumer's `.claude/settings.json` via `GOC_CLAUDE_HOOKS`).
- The OpenClaw plugin's `index.ts` reimplements the same logic and
  registers it via `api.on('session_start', ...)`.

So **every** session in **every** repo that uses GoC sees this message
when any card is `status: active`. The current dogfood deck has two
parked active cards at filing time:

| title | `status` | `human_gate` |
|---|---|---|
| `support-external-game-of-cards-state-location` | active | **session** |
| `list-game-of-cards-on-anthropic-community-marketplace` | active | **decision** |

Running the hook (verbatim, 2026-05-29):

```text
$ echo '{}' | uv run python .claude/hooks/deck_session_start.py
[GoC] Active card(s): list-game-of-cards-on-anthropic-community-marketplace, support-external-game-of-cards-state-location — resume or close before starting new work.
```

The agent reading that line cannot resume either card — both are awaiting
the human. The hook is functionally telling the agent to attempt work it
is structurally barred from doing.

## Why it matters

The hook is one of two surfaces (along with the prompt router) where GoC
asserts its presence in the agent's context window. Its job is to keep
in-flight work visible across session boundaries. When it labels gated
parked work as "resume or close", three failure modes follow:

1. **Misframing.** The autonomous `pull-card` flow explicitly treats
   listed active cards as a soft lock and skips them, so the loop does
   not regress. But an interactive agent that obeys the literal text
   ("resume or close before starting new work") will try to resume a
   card it cannot progress, burn tokens reading the body, and surface
   the gate to the human a second time.
2. **Lost signal.** Conflating the two cases means the human reading
   the line cannot tell at a glance which active cards still need their
   own attention (gate ≠ none) vs which an agent could finish. The
   distinction is exactly what `goc triage` exists to surface — but the
   session-start primer should not require a follow-up query to be
   interpretable.
3. **Drift from the lifecycle model.** AGENTS.md describes a
   three-axis "stuck" model (progress status / derived dependency
   readiness / stored impediment overlay) and a fourth axis
   (`human_gate`) for decision-waits. The hook hard-codes the progress
   axis only, which made sense when the project shipped a single
   `blocked` status. Now that the impediment overlay and human-gate
   axes are first-class, a hook still keyed solely on `status:` is
   silently behind the model.

## Fix

Two clean shapes; either is fine, but pick one before opening the
patch.

**Option A — filter parked cards out of the reminder.** Change the
loop to skip cards with `human_gate != "none"`:

```python
# pseudo-diff against deck_session_start.py
   if _card_status(readme) == "active":
+      if _card_human_gate(readme) != "none":
+          continue
       active_cards.append(card_dir.name)
```

Pros: simplest. The `goc triage` view already surfaces parked cards
separately, so the session-start hook becomes a clean
"agent-resumable work" signal.

Cons: a human reading their own SessionStart loses visibility of
parked cards entirely — they have to remember to run `goc triage`.

**Option B — split the line into two groups.**

```text
[GoC] Active card(s):
  - <title> (gate: none) — resume or close
  - <title> (gate: session) — awaiting human; agent cannot resume
```

Pros: preserves the "what's in flight" signal while telling the agent
what is actually actionable.

Cons: two-line output is louder; some hosts may truncate.

The implementer picks. The DoD insists only that gated cards are no
longer presented with the agent-actionable framing.

The hook should reuse the engine's frontmatter parser rather than
hand-rolling a second `human_gate` line scan — the closed predecessor
`session-start-hook-flags-closed-cards-as-active` already converted the
body-substring match to a proper frontmatter parse for `status`. The
fix here is a small extension of that parser, not a third hand-rolled
shortcut.

## Notes

- Two existing closed cards establish the editing pattern:
  `session-start-hook-flags-closed-cards-as-active` (corrected
  body-blind matching) and `derive-claude-hook-manifest-from-templates`
  (parity / sync discipline). Reuse their layout for the regression
  fixture.
- The OpenClaw plugin reimplements this hook in TypeScript inside
  `openclaw-plugin/index.ts`; the fix must update that copy by hand
  since it is not auto-synced (the porter only covers skills, not the
  TS entrypoint).
