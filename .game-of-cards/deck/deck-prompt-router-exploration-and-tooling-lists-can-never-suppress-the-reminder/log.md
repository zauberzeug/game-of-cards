# log

## 2026-07-31T06:50:00Z — Filed

- **What**: filed from an `audit-deck` pass run because `goc --ready` was
  empty (176 open cards, 173 gate-parked, the 3 at gate `none` all carrying
  an active `waiting_on` overlay). The finding is that
  `deck_prompt_router.py`'s `EXPLORATION` and `TOOLING` lists cannot change
  the hook's output for any input.

- **How it was confirmed**: three independent ways, all in `reproduce.py`.
  The exhaustive truth table over the boolean triple is the load-bearing
  one — it settles the claim by construction rather than by corpus, so the
  27-prompt ablation is corroboration, not the argument. The third
  demonstration replays a fix option that
  [deck-prompt-router-i-want-to-pattern-fires-on-pure-exploration-prompts](../deck-prompt-router-i-want-to-pattern-fires-on-pure-exploration-prompts/)
  already offers in its own DoD and shows it is a no-op.

- **A claim corrected before publishing**: the first draft of this body
  asserted that Option B (make suppression load-bearing) would close both
  sibling cards because "their example prompts all match an EXPLORATION
  pattern". True for the `work-verb-as-noun` card — all five of its DoD
  prompts match. False for the `i want to` card: none of its four prompts
  (`I want to understand …`, `… know …`, `… learn about …`, `we need to
  investigate …`) matches any EXPLORATION pattern today, which is precisely
  why that card offers "add `understand|investigate|know|learn|see` to
  EXPLORATION" as a third option. Option B alone does not close it; B plus
  that vocabulary does. The body now says so.

- **Gate**: `decision`. The three options are not variants of one fix — they
  answer different questions about what the router is *for* (detect work vs.
  route between work and questions), and they have opposite effects on the
  mixed-request prompts that two closed cards exist to protect. The
  project's `create-card` rubric hook is empty, so there is no project-local
  rule that decides it without a human.

- **Edges**: `advances` both open router cards. Deciding this question
  changes what "coordinated" means in their DoDs, so it is genuinely
  upstream of both. Edges were written at `goc new` time and committed
  together with the card by explicit pathspec rather than via `--commit`,
  because auto-committing a draft's edges ships the counterparts' half-edges
  while withholding the draft endpoint — the known defect
  [auto-commit-publishes-dangling-edges-when-counterpart-endpoint-is-a-draft](../auto-commit-publishes-dangling-edges-when-counterpart-endpoint-is-a-draft/).
  `goc repair-edges` reports no half-edges after the commit.

## 2026-07-31T06:52:00Z — Family sweep for the "populated but unread" shape

Prompted by the `pattern_generalization_check` Stop hook. Deduped first;
the shape already has an open card, so this is a connection, not a new
filing.

- **Peer**:
  [agent-manifest-guidance-block-is-built-but-silently-ignored](../agent-manifest-guidance-block-is-built-but-silently-ignored/).
  Cross-references added in both directions.

- **Sweep run**: every module-level constant in `goc/` and `scripts/`
  (93 names; `goc/_vendor/` excluded as third-party) checked for zero
  readers across `goc/`, `scripts/`, and `tests/`. One hit —
  `SUPERSEDE_REL_FIELDS` (`goc/engine.py:1218`). Its three neighbours are
  all read; the supersession branch that would use it is written longhand as
  `edge.field == "superseded_by"` (`goc/engine.py:5739`). Logged as the
  degenerate case (an unused name, not a misleading contract) and not filed.

- **Sweep gap, stated rather than glossed**: the scan covered module-level
  constants only. Both real instances are unread *dataclass fields* or
  *local variables*, which grep cannot distinguish from live ones — that
  needs call-graph analysis. So this sweep does not license the claim that
  two instances is the whole family; it only says no third one surfaced by
  the cheap method.

- **No umbrella filed.** Two instances, both open, both with a written fix
  path. A third substantive instance is the signal to file the root.
