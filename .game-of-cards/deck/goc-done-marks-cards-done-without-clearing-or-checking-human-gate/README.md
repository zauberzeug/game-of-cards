---
title: goc-done-marks-cards-done-without-clearing-or-checking-human-gate
summary: "`goc done`, `goc done --bundle`, and `goc status <t> disproved|superseded` flip a card to a terminal state without inspecting or clearing `human_gate`. A parked card carrying `human_gate: decision` and an unresolved `## Decision required` body section can be closed silently, and `goc validate` accepts the contradictory frontmatter."
status: done
stage: null
contribution: high
created: "2026-05-29T14:01:25Z"
closed_at: "2026-05-30T14:16:31Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, meta-fix]
definition_of_done: |
  - [x] PROCESS: decision recorded on this card (refuse vs auto-lower vs validator-only) before any code edit lands
  - [x] TDD: `uv run python .game-of-cards/deck/goc-done-marks-cards-done-without-clearing-or-checking-human-gate/reproduce.py` exits non-zero on a clean checkout (the chosen fix prevents the contradiction)
  - [x] TDD: `validate_card` (goc/engine.py:1160) rejects any card with `status` in `TERMINAL_STATUSES` AND `human_gate` ≠ `none`; regression test covers `done`, `disproved`, `superseded`
  - [x] TDD: focused test covers all four terminal entry points (`goc done <t>`, `goc done --bundle ...`, `goc status <t> disproved`, `goc status <t> superseded`) under the chosen contract
  - [x] MECHANICAL: `goc decide` continues to refuse cards whose gate is already `none` (engine.py:4557); the symmetry between decide ↔ close is documented in `Skill(card-schema)` if not already
worker: {who: "claude[bot]", where: main}
---

# goc-done-marks-cards-done-without-clearing-or-checking-human-gate

## Location

- `goc/engine.py:3215-3258` — `_cmd_done` (single-card close)
- `goc/engine.py:3281-3346` — `_cmd_done_bundle` (bundled close)
- `goc/engine.py:3948-4022` — `_cmd_status` (flip to `disproved` / `superseded`)
- `goc/engine.py:1160-1262` — `validate_card` (no terminal-gate invariant)
- `goc/engine.py:4557` — `_cmd_decide` (refuses when gate already `none` — the symmetric counterpart that is missing on the close side)

## What's broken

`goc decide` and `goc done` are meant to be a complementary pair: a card filed with `--gate decision` carries a `## Decision required` body section until a human runs `goc decide`, which records the resolution and lowers the gate to `none`. Closure should then proceed with `goc done`. But the current code only enforces one half of that contract:

```python
# goc/engine.py:4557 — _cmd_decide
if t.human_gate == "none":
    print(
        f"ERROR: {title}: gate already 'none' (no decision pending)",
        file=sys.stderr,
    )
    sys.exit(2)
```

`_cmd_done` (engine.py:3215) has no symmetric check. It enforces only DoD checkboxes and non-overwriting of terminal status, then writes:

```python
# goc/engine.py:3253-3256
text = (card_dir / "README.md").read_text()
text = mutate_frontmatter_field(text, "status", "done")
text = mutate_frontmatter_field(text, "closed_at", _yaml_inline(now))
(card_dir / "README.md").write_text(text)
```

`_cmd_done_bundle` (engine.py:3340) and `_cmd_status` (engine.py:3998) follow the same shape — neither inspects nor mutates `human_gate` when flipping into a terminal state.

`validate_card` (engine.py:1206-1216) enforces `closed_at` consistency for terminal cards but has no parallel invariant for `human_gate`:

```python
# goc/engine.py:1206-1216
status_value = fm.get("status")
if status_value in TERMINAL_STATUSES:
    if closed_at is None:
        errors.append(f"{t.title}: closed_at: must be set when status={status_value}")
    if status_value == "done" and t.dod_open > 0:
        errors.append(f"{t.title}: definition_of_done: status=done with {t.dod_open} unchecked boxes")
elif closed_at is not None:
    errors.append(
        f"{t.title}: closed_at: must be null when status is non-terminal"
        f" (status={status_value!r}, closed_at={closed_at!r})"
    )
```

Net effect: a card can simultaneously carry `status: done` and `human_gate: decision`, with the unresolved `## Decision required` body section still in place, and `goc validate` (run locally and in CI) emits no error.

## Empirical evidence

`uv run python .game-of-cards/deck/goc-done-marks-cards-done-without-clearing-or-checking-human-gate/reproduce.py`:

```
--- goc done demo-card ---
rc = 0
stdout: demo-card: open → done
Next: goc to see what's open, or ask your agent to "drain the queue" (pull-card).
stderr:

--- post-close frontmatter ---
status: done
human_gate: decision
body still contains '## Decision required' section: True

--- goc validate ---
rc = 0
stdout: OK  demo-card

DEFECT CONFIRMED:
  status: done AND human_gate: decision coexist on the closed card,
  the unresolved `## Decision required` body section survives,
  and `goc validate` exits 0 with no warning.
```

## Why it matters

The `human_gate` field is part of the card's public API for parallel agents: queue-filtering predicates (`goc --ready`, `next-card`, `pull-card`) consult it to decide whether a card is autonomously claimable, and `goc triage` lists parked cards grouped by gate. When `human_gate` survives closure, every downstream reader sees a contradiction:

- A future reader landing on a closed card with `human_gate: decision` cannot tell whether the recorded decision was honored, deferred, or never made — the README still has `## Decision required` advertising an open pick. `Skill(decide-card)` is documented as the resolution path; if `goc done` quietly bypasses it, the deliberation history is lost.
- `goc triage` filters parked cards by `status: open AND human_gate != none` (engine.py:4605), so closed-but-gated cards do not appear there. Whichever surface a reader queries, the contradictory state is invisible until they read the raw frontmatter.
- The asymmetry between `_cmd_decide` (refuses if gate is already `none`) and `_cmd_done` (ignores gate entirely) is a contract gap — the validator is the catalog floor, and its silence on this case turns "fix it locally next time you notice" into "permanent footgun on every deck."

**Reachability path.** Anyone can produce the malformed state with the dogfood deck — file a card with `--gate decision`, tick its DoD, run `goc done`. No hand-edit required. The four engine code paths above are all live in shipping; the reproducer hits one (`goc done`), and the same hole exists across `goc done --bundle` and `goc status <t> {disproved,superseded}`.

## Decision

*Resolved 2026-05-30T13:36:38Z:* Refuse-and-redirect: the four terminal-close paths (goc done, done --bundle, status disproved, status superseded) refuse when human_gate != none and tell the operator to run goc decide first; validator adds the invariant status in TERMINAL_STATUSES implies human_gate == none

*Reasoning:* it preserves the decide-close symmetry the codebase already commits to (decide refuses gate==none; close should refuse gate!=none) and the validator addition makes the invariant a catalog-level fact rather than a per-command convention; the scripted bulk-close objection is hypothetical with no current caller expecting to close a parked card

## Fix sketch (conditional on Option A)

Add to `_cmd_done`, `_cmd_done_bundle`, and the terminal branch of `_cmd_status`:

```python
if t.human_gate != "none":
    print(
        f"ERROR: {title}: human_gate is {t.human_gate!r}; "
        f"run `goc decide {title} --decision <choice> --because <reason>` "
        f"to lower the gate before closing.",
        file=sys.stderr,
    )
    sys.exit(2)
```

Add to `validate_card` (alongside the existing `closed_at` checks at engine.py:1206-1216):

```python
gate_value = fm.get("human_gate")
if status_value in TERMINAL_STATUSES and gate_value not in (None, "none"):
    errors.append(
        f"{t.title}: human_gate: must be 'none' when status={status_value} "
        f"(got {gate_value!r}); run `goc decide` to resolve the gate before closing."
    )
```

Migration: any deck that already carries a closed-but-gated card surfaces as a `goc validate` failure after the upgrade. A one-shot `goc repair-edges`-style helper, or a documented one-liner that mutates `human_gate` to `none` on terminal cards, may be worth shipping alongside the change.
