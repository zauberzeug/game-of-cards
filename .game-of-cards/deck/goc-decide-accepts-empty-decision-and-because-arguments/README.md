---
title: goc-decide-accepts-empty-decision-and-because-arguments
summary: "`goc decide <title> --decision '' --because ''` exits 0, lowers the human gate to `none`, and writes a corrupt `## Decision` block (no decision text, no reasoning text) plus a log entry whose visible content is ` — . Gate decision → none.`. The Andon-cord handoff that `Skill(decide-card)` documents is meant to be a permanent audit trail of what was decided and why; empty values silently break that trail while still releasing the card to autonomous pullers."
status: open
stage: null
contribution: medium
created: "2026-05-29T19:53:19Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract, meta-fix]
definition_of_done: |
  - [ ] TDD: reproduce.py exits non-zero (defect no longer fires — `goc decide` with empty `--decision` or empty `--because` is rejected before any state changes).
  - [ ] PROCESS: decision recorded on whether the failure mode is `exit 2 + ERROR before any mutation` (strict, mirrors the terminal-status guard at engine.py:4556) or `exit 0 + WARNING on stderr + still record` (lenient). Strict is the natural fit since the resulting body and log are not human-readable.
  - [ ] MECHANICAL: `_cmd_decide` (engine.py:4547) validates that `args.decision.strip()` and `args.reasoning.strip()` are both non-empty before reading the README, with a single `ERROR: --decision and --because must be non-empty` message and exit 2 when either is blank.
  - [ ] TDD: a regression test in `tests/` asserts the chosen signal for the empty-string case, separately for empty-`--decision`, empty-`--because`, and both.
  - [ ] PROCESS: `uv run goc validate` passes.
---

# `goc decide` accepts empty `--decision` / `--because` arguments

## Location

- `goc/engine.py:4547-4606` — `_cmd_decide`
- `goc/engine.py:2706-2714` — argparse definition for `p_decide` (`--decision` / `--because` marked `required=True`)
- `goc/engine.py:363-378` — `replace_or_append_decision` (formats the body block; no value-empty guard)

## What's broken

`p_decide`'s argparse declarations mark both options as required:

```python
# goc/engine.py:2708-2711
p_decide.add_argument("--decision", required=True,
                      help="One-line decision text (what was chosen).")
p_decide.add_argument("--because", dest="reasoning", required=True,
                      help="Reasoning behind the decision.")
```

`required=True` only enforces *presence* on the command line — empty
strings satisfy it. The downstream `_cmd_decide` then trusts the values
unconditionally:

```python
# goc/engine.py:4547
def _cmd_decide(args):
    """Record a decision in the body + log; lower the human gate to `none`."""
    title = args.title
    decision = args.decision
    reasoning = args.reasoning
    ...
    if t.status in TERMINAL_STATUSES:
        ... # terminal-card guard exists
    if t.human_gate == "none":
        ... # already-decided guard exists
    ...
    body = replace_or_append_decision(body, decision, reasoning, now)
    text = mutate_frontmatter_field(text, "human_gate", "none")
    (card_dir / "README.md").write_text(text)
    ...
    entries.append(
        f"## {now}: decision recorded\n\n"
        f"{decision} — {reasoning}. Gate {prior_gate} → none.\n"
    )
```

There is no `if not decision.strip() or not reasoning.strip(): ...` check.
Empty strings flow through `replace_or_append_decision`, which emits the
template literally:

```python
# goc/engine.py:375
block = f"## Decision\n\n*Resolved {today}:* {decision}\n\n*Reasoning:* {reasoning}\n\n"
```

…producing a body block of `*Resolved <ts>:* \n\n*Reasoning:* \n\n` and a
log entry of `## <ts>: decision recorded\n\n — . Gate decision → none.`.
The gate is lowered to `none` regardless, exit code is 0, and stdout
prints the same `decision recorded; gate decision → none` line a real
decision produces. The card now looks fully decided to every
downstream reader.

## Empirical evidence

`uv run python .game-of-cards/deck/goc-decide-accepts-empty-decision-and-because-arguments/reproduce.py`
on a clean checkout:

```text
=== Call: goc decide parked-card --decision '' --because '' ===
  exit code: 0
  stdout (first line): 'parked-card: decision recorded; gate decision → none'

=== Resulting README `## Decision` block ===
  | *Resolved 2026-05-29T19:54:29Z:*
  |
  | *Reasoning:*
  |

=== Resulting log.md entry ===
  | ## 2026-05-29T00:00:00Z: decision deliberation archived
  | ...
  | ## 2026-05-29T19:54:29Z: decision recorded
  |
  |  — . Gate decision → none.

=== Verdict ===
  exit 0 + 'decision recorded' on stdout?    True
  frontmatter human_gate lowered to 'none'?  True
  README `## Decision` block has empty body? True
  log.md entry has empty decision/reasoning? True
  DEFECT FIRES (empty-decision-silently-accepted): True
```

The reproducer exits 0 while the defect fires; the DoD flips this so
exit 0 only happens once the fix is in.

## Why it matters

`goc decide` is the Andon-cord lowering handoff documented by
`Skill(decide-card)`: when a parked card is resolved, the verb records
what was chosen and why on the card's permanent dashboard and journal,
then releases the card to the autonomous queue. Both fields are
load-bearing — the decision text becomes the README's `## Decision`
block (the dashboard a future puller reads to understand the resolved
direction) and the reasoning is the log-journal entry's "why" half. An
empty value at either position breaks the contract while still flipping
the gate.

Reachability is direct: every project agent (the `decide-card` skill,
`/loop`-driven autonomous flows, any human typing the bare verb) goes
through the same argparse + `_cmd_decide` path. Two concrete failure
modes:

1. **Tooling under `--commit`**: a script driving
   `goc decide ... --decision "$DECISION" --because "$REASON" --commit`
   where `$DECISION` or `$REASON` is unset / empty (variable expansion
   misfire, jq returning `null`, an LLM tool-call schema where the
   field defaulted to `""`) produces a commit named
   `decide: <title> — ` (the trailing dash is from
   `f"decide: {title} — {decision_short}"` at engine.py:4604-4605).
   The deck history records a decision that has no decision text;
   reviewers can't replay the call from log.md either, because the log
   entry's content boils down to ` — `.
2. **Andon-cord misuse**: an agent reaches the parked card during
   `pull-card`, sees `## Decision required`, and (instead of escalating
   to the human) calls `goc decide` with empty values to "unblock the
   queue." `Skill(decide-card)` is supposed to be the human's
   one-action handoff, and the empty-string path lets an agent forge
   the handoff while looking, on every downstream surface, like a
   completed decision: gate `none`, body has a `## Decision` heading,
   stdout said `decision recorded`. The next puller takes the card.

The fix is local and additive — a single-line guard in `_cmd_decide`
before any disk mutation — so this is a `meta-fix` candidate alongside
the other `goc <verb> accepts unwanted input` family
(`goc-wait-sets-impediment-overlay-on-terminal-status-cards-without-any-guard`,
`goc-quality-pass-mutates-summary-and-dod-on-terminal-status-cards`,
`goc-attest-mutates-log-md-on-already-closed-cards`,
`goc-advance-claims-success-when-adding-an-already-existing-edge`):
each is one CLI verb whose argparse layer accepts the input and whose
command function performs the mutation without a precondition check.

## Decision required

Two credible failure-mode shapes; pick one:

1. **`exit 2 + ERROR before any mutation`** (strict). Mirrors the
   existing terminal-status guard at `engine.py:4556` and the
   already-`none` gate guard at `engine.py:4565`. The natural choice
   because the resulting body and log entry are not human-readable —
   there is no "lenient success" interpretation that produces a useful
   audit trail. Breaks no tooling that wasn't already producing
   corrupt output.
2. **`exit 0 + WARNING on stderr + still record`** (lenient). Keeps
   the option open for tooling that wants to record a "decided but
   undocumented" state for later annotation. Less appealing — the
   README block and log entry are equally corrupt either way, and a
   "WARNING then succeed" path is the harder-to-discover variant of
   the same broken contract.

Strict (option 1) is the natural sibling of the existing guards in
the same function. Adopt strict unless a concrete tooling use case
appears for the lenient form.

## Fix

After the existing `human_gate == "none"` guard at `engine.py:4570`
and before the `prior_gate = t.human_gate` line:

```python
if not decision.strip() or not reasoning.strip():
    print(
        f"ERROR: {title}: --decision and --because must both be non-empty "
        "(empty values produce an unreadable decision block and log entry)",
        file=sys.stderr,
    )
    sys.exit(2)
```

No other surface needs changing — `replace_or_append_decision` and the
log-entry formatter are correct given non-empty inputs.
