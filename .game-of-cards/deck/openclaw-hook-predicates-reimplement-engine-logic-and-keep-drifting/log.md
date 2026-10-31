## 2026-08-04 — fifth drift instance recorded (frontmatterTail quote-awareness)

Surfaced by an `audit-deck` sweep of the TypeScript hook ports. Deduped
first: `frontmatterTail` is already named in this card's ported-predicate
list, so the instance is recorded here rather than filed as a duplicate
umbrella.

`frontmatterTail` in `openclaw-plugin/index.ts` strips a whitespace-preceded
`#` anywhere on the scalar tail; the Python `_comment_free_tail` it claims to
mirror only does so *outside* a quoted scalar. Verified by extracting the TS
functions with Node (`--experimental-strip-types`) and running both readers on
the same four frontmatter lines — all four disagree, and two flip a decision:

- `human_gate: "none # revisit"` — Python reports the active card **parked**
  (gate reads `none # revisit`); TS reports it **resumable** (gate reads
  `none`).
- `waiting_until: "<past date> # comment"` with no `waiting_on` — Python hits
  the unparseable backstop and impedes; TS parses the truncated date, sees it
  elapsed, and announces the card resumable.

Notable for this card's argument: instance #5 is the first found *after* the
guard was filed, and it is a predicate the existing `isImpeded` matrix does
not cover at all. That supports mechanism 1's stated weakness (it pins
agreement on enumerated cells of enumerated predicates) and is an argument for
scoping the chosen guard to all ported predicates, not just the waiting pair.
No fix applied — this card is gated on the mechanism decision.

Separately filed this sweep:
[openclaw-pattern-check-never-fires-on-plain-file-edits](../openclaw-pattern-check-never-fires-on-plain-file-edits/),
which `advances` this card. That one is a *different* shape — the port is
faithful to its Python source, and the faithfulness is the bug, because the
copied value is Claude Code's host-specific tool vocabulary.

## 2026-10-31T05:24:49Z — Instance #6: hasDeck accepts a file named deck

Found while closing
[openclaw-prompt-hook-fires-in-workspaces-without-a-deck](../openclaw-prompt-hook-fires-in-workspaces-without-a-deck/),
whose new opt-in guard calls `hasDeck`. The TS helper tests that the path
exists (`access()`), while `deck_prompt_router._has_deck` and the engine
test `is_dir()`. Both were run on two workspaces, one holding a regular
file `deck` and one holding a file `.game-of-cards/deck`. TS said true for
both, Python said False for both. Added to the instance list and to the
ported-predicate list. No fix applied: this card is gated on the mechanism
decision, and the sibling-sweep rule keeps a fifth-plus instance off the
fix-through path. On a real host nothing reaches the guard today anyway
([openclaw-plugin-hooks-never-deliver-their-reminders-on-a-real-host](../openclaw-plugin-hooks-never-deliver-their-reminders-on-a-real-host/)).
