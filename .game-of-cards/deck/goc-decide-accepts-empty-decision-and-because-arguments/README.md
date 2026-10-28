---
title: goc-decide-accepts-empty-decision-and-because-arguments
summary: "`goc decide <title> --decision '' --because ''` exited 0, lowered the human gate to `none` and wrote a `## Decision` block and log entry with nothing in them (` — . Gate decision → none.`), forging the Andon-cord handoff `Skill(decide-card)` documents as the permanent record of what was decided and why — argparse's `required=True` enforces presence only. It now refuses a blank (empty or whitespace-only) `--decision`, `--because` or both — exit 2, `ERROR: <title>: --decision and --because must be non-empty (blank: …)`, nothing written — through the parent epic's shared `_refuse_invalid_input` helper, before the card is read."
status: done
stage: null
contribution: medium
created: "2026-05-29T19:53:19Z"
closed_at: "2026-10-28T04:57:17Z"
human_gate: none
advances:
  - mutation-verbs-accept-invalid-input-and-report-misleading-no-op-success
advanced_by: []
tags: [bug, api-contract, meta-fix]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero (defect no longer fires — `goc decide` with empty `--decision` or empty `--because` is rejected before any state changes). — a blank `--decision`, a blank `--because` and both each get exit 2, `ERROR:` on stderr, no success line and README + log.md untouched, while the filled-in control is still recorded; the same script exits 1 against the pre-fix engine. Reworded from `exits non-zero`, which matched the inverted original script.
  - [x] PROCESS: decision recorded on whether the failure mode is `exit 2 + ERROR before any mutation` (strict, mirrors the terminal-status guard at engine.py:4909) or `exit 0 + WARNING on stderr + still record` (lenient). Strict is the natural fit since the resulting body and log are not human-readable. — decided 2026-10-22 via the parent epic: strict-refuse (exit 2).
  - [x] MECHANICAL: `_cmd_decide` (engine.py:6844) validates that `args.decision.strip()` and `args.reasoning.strip()` are both non-empty before reading the README, with a single `ERROR: --decision and --because must be non-empty` message and exit 2 when either is blank. — checked right after the `--commit`/`--no-commit` conflict check, before the card is resolved or read; the one message goes through the parent epic's `_refuse_invalid_input`, prefixed with the title and naming the blank option(s): `ERROR: <title>: --decision and --because must be non-empty (blank: --because)`.
  - [x] TDD: a regression test in `tests/` asserts the chosen signal for the empty-string case, separately for empty-`--decision`, empty-`--because`, and both. — `DecideCliTest` in `tests/test_mutation_verbs_refuse_invalid_input.py` covers those three plus whitespace-only values beside a filled-in control; its 4 refusal tests fail against the pre-fix engine.
  - [x] PROCESS: `uv run goc validate` passes.
worker: {who: "claude[bot]", where: main}
---

# `goc decide` accepts empty `--decision` / `--because` arguments

## Location

- `goc/engine.py` `_cmd_decide` — trusted `--decision` and `--because`
  unconditionally; it now refuses a blank value before it reads the card.
- `goc/engine.py` `p_decide` (the `decide` subparser) — marks both options
  `required=True`, which enforces presence only (unchanged).
- `goc/engine.py` `replace_or_append_decision` — formats the `## Decision`
  block; correct given non-empty values (unchanged).

## What was broken

`p_decide`'s argparse declarations mark both options as required, but
`required=True` only enforces *presence* on the command line — empty
strings satisfy it. The excerpts and line numbers below are the code as
filed; the terminal-card guard they show has since become the gate-repair
path, but the values went unchecked throughout.

```python
# goc/engine.py:4146-4149
p_decide.add_argument("--decision", required=True,
                      help="One-line decision text (what was chosen).")
p_decide.add_argument("--because", dest="reasoning", required=True,
                      help="Reasoning behind the decision.")
```

`_cmd_decide` then trusted the values unconditionally:

```python
# goc/engine.py:6844
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

There was no `if not decision.strip() or not reasoning.strip(): ...` check.
Empty strings flowed through `replace_or_append_decision`, which emits the
template literally:

```python
# goc/engine.py:678
block = f"## Decision\n\n*Resolved {today}:* {decision}\n\n*Reasoning:* {reasoning}\n\n"
```

…producing a body block of `*Resolved <ts>:* \n\n*Reasoning:* \n\n` and a
log entry of `## <ts>: decision recorded\n\n — . Gate decision → none.`.
The gate was lowered to `none` regardless, the exit code was 0, and stdout
printed the same `decision recorded; gate decision → none` line a real
decision produces. The card then looked fully decided to every downstream
reader.

## Empirical evidence

As filed, the original reproducer showed the forged handoff:

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

That reproducer exited 0 while the defect fired. It now follows the
reproducer contract (0 = defect no longer fires, 1 = fires, 2 = harness
broken) and drives the real CLI over a blank `--decision`, a blank
`--because` and both, each on its own parked card, with a filled-in
decision as the control. After the fix,
`uv run python .game-of-cards/deck/goc-decide-accepts-empty-decision-and-because-arguments/reproduce.py`
exits 0:

```text
$ goc decide control --decision 'Option A.' --because 'Option A is simpler.'
  exit 0
  stdout: control: decision recorded; gate decision → none
  stderr: (empty)

$ goc decide blank-decision --decision '' --because 'Option A is simpler.'
  exit 2
  stdout: (empty)
  stderr: ERROR: blank-decision: --decision and --because must be non-empty (blank: --decision)

$ goc decide blank-because --decision 'Option A.' --because ''
  exit 2
  stdout: (empty)
  stderr: ERROR: blank-because: --decision and --because must be non-empty (blank: --because)

$ goc decide both-blank --decision '' --because ''
  exit 2
  stdout: (empty)
  stderr: ERROR: both-blank: --decision and --because must be non-empty (blank: --decision, --because)

FIXED: a blank --decision, --because or both is refused with nothing written; a filled-in decision is still recorded.
```

Against the pre-fix engine the same script exits 1 (`DEFECT FIRES: blank
input accepted for blank-decision, blank-because, both-blank`).

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
   field defaulted to `""`) produced a commit named
   `decide: <title> — ` (the trailing dash is from the auto-commit's
   `f"decide: {title} — {decision_short}"`). The deck history recorded a
   decision that had no decision text; reviewers could not replay the
   call from log.md either, because the log entry's content boiled down
   to ` — `.
2. **Andon-cord misuse**: an agent reaches the parked card during
   `pull-card`, sees `## Decision required`, and (instead of escalating
   to the human) calls `goc decide` with empty values to "unblock the
   queue." `Skill(decide-card)` is supposed to be the human's
   one-action handoff, and the empty-string path let an agent forge
   the handoff while looking, on every downstream surface, like a
   completed decision: gate `none`, body has a `## Decision` heading,
   stdout said `decision recorded`. The next puller takes the card.

The fix is local and additive — a guard in `_cmd_decide` ahead of any
disk mutation. The card is one of the input-validation family the parent
epic
[mutation-verbs-accept-invalid-input-and-report-misleading-no-op-success](../mutation-verbs-accept-invalid-input-and-report-misleading-no-op-success/)
coordinates: each is one CLI verb whose argparse layer accepts the input
and whose command function performs the mutation without a precondition
check. As filed, this section also grouped three missing terminal-status
guards with it (`goc-wait-sets-impediment-overlay-on-terminal-status-cards-without-any-guard`,
`goc-quality-pass-mutates-summary-and-dod-on-terminal-status-cards`,
`goc-attest-mutates-log-md-on-already-closed-cards`); those check the
target card's status, not the arguments, and belong to the separate
[terminal-status-guard-missing-across-mutation-verbs](../terminal-status-guard-missing-across-mutation-verbs/)
epic.

## Decision

*Resolved 2026-10-22T05:20:22Z:* Decided via parent mutation-verbs-accept-invalid-input-and-report-misleading-no-op-success: option 1, exit 2 + ERROR before any mutation for an empty --decision or --because

*Reasoning:* The maintainer decided the parent's shared validation-failure shape (1. Strict-refuse) in a human session on 2026-10-22, which answers exactly this card's question

## Fix

`_cmd_decide` checks both values right after the `--commit` /
`--no-commit` conflict check, before it resolves or reads the card. A
value that is empty or whitespace-only after `.strip()` is blank, and a
blank one is refused through the parent epic's shared
`_refuse_invalid_input`:
`ERROR: <title>: --decision and --because must be non-empty (blank: --because)`,
naming whichever is blank (both, comma-separated), exit 2, nothing
written. Whitespace counts as blank because it renders as nothing in the
`## Decision` block and the log entry.

The fix sketch filed with this card placed the check after the
gate-already-`none` guard; DoD item 3 asked for it before the README is
read, which is where it landed. A pure argument check needs no card
state — the same reason `_cmd_advance` refuses a self-edge before it
loads either card — so a blank value is refused the same way whatever
state the card is in.

`replace_or_append_decision` and the log-entry formatter are unchanged;
they are correct given non-empty inputs. `Skill(decide-card)`'s list of
refusals now names the blank case. The regression cases sit beside the
redundant-edge pair's in `tests/test_mutation_verbs_refuse_invalid_input.py`
(`DecideCliTest`).
