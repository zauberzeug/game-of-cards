---
title: closure-on-integration-check-only-runs-for-done-not-disproved-or-superseded
summary: When `workflow.closure_on_integration: true`, `goc done` refuses to close unless HEAD is reachable from origin/main, but `goc status <title> disproved` and `goc status <title> superseded --by <other>` skip the check entirely. The same terminal-state semantics (others must see the closure to avoid duplicate effort) apply to all three transitions, so the asymmetry creates a loophole: a worker can close locally by disproving instead of done. Decision-class because the scope of the policy is taste — was the done-only framing deliberate, or should the check extend to every terminal flip.
status: open
stage: null
contribution: medium
created: "2026-05-31T03:36:20Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract, documentation]
definition_of_done: |
  - [ ] PROCESS: decision recorded — does the policy extend to all terminal transitions, or stay scoped to `done`?
  - [ ] TDD: reproduce.py exits zero (the chosen behaviour fires consistently on the three terminal transitions per the decision)
  - [ ] MECHANICAL: the relevant call site(s) in `goc/engine.py` updated (extend → call `_enforce_closure_on_integration_or_exit` from the `_cmd_status` terminal branch; keep → rename / re-doc the helper so its scope is unambiguous)
  - [ ] MECHANICAL: docstring at `goc/engine.py:3766` and kickoff doc at `goc/templates/skills/kickoff/SKILL.md:287` updated to match the chosen scope
  - [ ] TDD: regression test in `tests/` covering the chosen behaviour for `done`, `disproved`, and `superseded` flips under `closure_on_integration: true`
---

# closure-on-integration-check-only-runs-for-done-not-disproved-or-superseded

## Location

- `goc/engine.py:3518` — `_cmd_done` calls `_enforce_closure_on_integration_or_exit(title)`.
- `goc/engine.py:3603` — `_cmd_done_bundle` calls the same helper inside its bundle loop.
- `goc/engine.py:4302-4303` — `_cmd_status` enters the terminal-status branch (`if new_status in TERMINAL_STATUSES`) and calls *only* `_enforce_no_inbound_superseded_by_or_exit(title, new_status)`. The integration check is not invoked here.
- `goc/engine.py:3766-3772` — helper docstring framing.
- `goc/templates/skills/kickoff/SKILL.md:287` — user-facing description of the workflow knob.

## What's broken

`_cmd_done` enforces the integration policy:

```python
# goc/engine.py:3515-3518
def _cmd_done(args: argparse.Namespace) -> None:
    title = _resolve_title_or_exit(args.title)
    _enforce_no_inbound_superseded_by_or_exit(title, "done")
    _enforce_closure_on_integration_or_exit(title)
```

`_cmd_done_bundle` enforces it per plan member:

```python
# goc/engine.py:3601-3603
for title in plan_titles:
    _enforce_no_inbound_superseded_by_or_exit(title, "done")
    _enforce_closure_on_integration_or_exit(title)
```

`_cmd_status`, which handles transitions to `disproved` and `superseded` (the other two terminal statuses), only enforces the supersede-graph guard:

```python
# goc/engine.py:4302-4303
if new_status in TERMINAL_STATUSES:
    _enforce_no_inbound_superseded_by_or_exit(title, new_status)
```

The helper's own docstring scopes itself to `done`:

> Multi-team policy: a card cannot transition to `done` until its work is integrated to the canonical branch — `done` must mean "visible to every participant", not just "locally DoD-complete". Opt-in; default off.

So does the kickoff doc that ships with `goc install`:

> `workflow.closure_on_integration: true` — `goc done` refuses to close unless HEAD is reachable from `origin/main`, so `done` means visible to every participant rather than locally DoD-complete.

## Empirical evidence

Static AST reproducer (`reproduce.py`) walks `goc/engine.py` and checks
which command handlers reach `_enforce_closure_on_integration_or_exit`:

```
_cmd_done:        integration check = True
_cmd_done_bundle: integration check = True
_cmd_status:      integration check = False  <-- DEFECT
```

Exit 1 while the asymmetry exists; will exit 0 once all three (or none
of the three) call the helper, per whichever direction the decision
chooses.

## Why it matters

`TERMINAL_STATUSES = {"done", "disproved", "superseded"}` are all closure
states — once entered, the card is no longer in the pull queue, no longer
in `goc --ready`, no longer a candidate for further work by any
participant. The stated principle ("visible to every participant, not
just locally DoD-complete") applies symmetrically to every terminal flip:

- A locally-disproved card not pushed to `origin/main` lets another
  participant pick it back up and waste effort re-disproving it (or
  worse, attempting the work assuming the rebuttal hasn't been
  attempted).
- A locally-superseded card with an unpushed `superseded_by` edge
  leaves other participants pointing at the old card without seeing
  the forward pointer to its successor.

Reachability path: any consumer with `workflow.closure_on_integration: true`
in `.game-of-cards/config.yaml` running `goc status <card> disproved`
or `goc status <card> superseded --by <other>` from a branch whose
HEAD is not reachable from `origin/main` (e.g. a local feature branch,
a detached HEAD, an agent worktree that hasn't pushed yet). The policy
fires on `goc done <card>` from the same branch; the two other
terminal transitions silently skip it. A worker who wants to close a
card without integrating just has to pick `disproved` over `done`.

## Decision required

Two credible paths; pick one.

**A. Extend the check to every terminal flip.** Add
`_enforce_closure_on_integration_or_exit(title)` to the `_cmd_status`
terminal branch alongside the existing supersede-graph guard. Update
the helper docstring and the kickoff doc to say "any terminal
transition" instead of "done". Closes the loophole; treats all three
closure flavours uniformly. Cost: a worker disproving in the middle
of a long-running spike now has to push before flipping the status
— marginally more friction in legitimate local exploration.

**B. Keep the policy scoped to `done`.** Rename the helper (or its
exposed config key) so the scope is explicit:
`workflow.done_on_integration` instead of `closure_on_integration`,
and a corresponding helper rename. Update the kickoff doc to make the
scope contrast explicit ("only `goc done`; disproved and superseded
flip without integration"). Cost: doesn't close the loophole; leaves
a sharp edge a multi-team setup may trip over later.

Tie-breaker if both options feel even: the helper's existing name
(`closure_on_integration`, not `done_on_integration`) and the
"visible to every participant" framing of its docstring both suggest
the design intent was option A and option B is the documented-scope
patch over a bug. But the documented contract today is option B, so
flipping to A is a behaviour change consumers may not expect.

## Fix (per chosen path)

**If A:**

```python
# goc/engine.py:4302
if new_status in TERMINAL_STATUSES:
    _enforce_no_inbound_superseded_by_or_exit(title, new_status)
    _enforce_closure_on_integration_or_exit(title)
```

Plus docstring + kickoff doc rewrites at the two cited line ranges.

**If B:**

Rename `_enforce_closure_on_integration_or_exit` →
`_enforce_done_on_integration_or_exit`, rename the config key
`workflow.closure_on_integration` →  `workflow.done_on_integration`,
add a migration warning for the old key, update the kickoff doc to
state the scope explicitly.

A regression test must cover both `done` and `status … disproved` /
`status … superseded --by …` under the policy so the chosen scope
stays honest.
