---
title: goc-wait-clear-silently-discards-reason-and-until-set-in-same-call
summary: "`goc wait <t> --clear --reason X --until Y` clears the impediment overlay and silently discards the requested set; exit 0, no warning. The verb's argparse and handler accept the mode-conflict without rejecting (cf. `goc status --by` rejecting outside `superseded`)."
status: open
stage: null
contribution: medium
created: "2026-05-29T21:12:54Z"
closed_at: null
human_gate: decision
advances:
  - mutation-verbs-accept-invalid-input-and-report-misleading-no-op-success
advanced_by: []
tags: [bug, api-contract, meta-fix]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero — the verb either rejects the mode-conflict (exit 2) or applies a clear-then-set sequence, but never silently drops the requested overlay
  - [ ] TDD: regression test in `tests/` asserts the chosen behavior for `--clear` combined with `--reason` / `--until`
  - [ ] MECHANICAL: `_cmd_wait` in `goc/engine.py` enforces the resolved contract
  - [ ] PROCESS: decision recorded inline (reject vs. clear-then-set) with sibling-verb consistency rationale
  - [ ] MECHANICAL: skill bodies (`finish-card`, `advance-card`) updated if `--clear` semantics change
---

# goc-wait-clear-silently-discards-reason-and-until-set-in-same-call

## Location

`goc/engine.py:4326-4358` (`_cmd_wait`).

## What's broken

`_cmd_wait` checks `args.clear` first and, if set, pops both overlay
fields and falls through to the unconditional write at line 4359 —
without ever inspecting `args.reason` / `args.until`:

```python
def _cmd_wait(args):
    ...
    if args.clear:
        if prior_reason is None and prior_until is None:
            print(f"{title}: no waiting overlay to clear; nothing to do")
            return
        fm.pop("waiting_on", None)
        fm.pop("waiting_until", None)
        new_reason: str | None = None
        new_until: str | None = None
    else:
        if not args.reason and not args.until:
            print(
                "ERROR: pass --reason and/or --until (or --clear to drop the overlay)",
                ...
            )
            sys.exit(2)
        ...
```

The argparse wiring at `goc/engine.py:2650-2666` declares `--clear`,
`--reason`, and `--until` as three independent flags with no
`mutually_exclusive_group`, so all three pass argparse cleanly:

```python
p_wait.add_argument("--reason", choices=["external", "resource", "deferred"], ...)
p_wait.add_argument("--until", default=None, ...)
p_wait.add_argument("--clear", action="store_true", ...)
```

Sibling state-flip verbs do reject mode-conflicts. `_cmd_status` at
`goc/engine.py:3958-3964` rejects `--by` when `new_status != "superseded"`
with exit code 2 and an explicit error. The convention is documented
behavior across the verb family; `wait` is the lone holdout.

## Empirical evidence

From `reproduce.py` (path-isolated sandbox, runs against the in-tree
`goc` engine):

```
=== second invocation ===
exit code: 0
stdout: demo: waiting overlay cleared (was waiting_on='external', waiting_until='2026-12-31')
stderr:

=== frontmatter overlay fields after conflict call ===
(no waiting_* keys present)

=== diagnosis ===
BUG: exit 0 AND requested overlay (waiting_on=resource, waiting_until=2027-06-30) was silently dropped.
```

The conflict invocation was
`goc wait demo --clear --reason resource --until 2027-06-30`; the first
invocation had already set `waiting_on=external, waiting_until=2026-12-31`.
Exit code is 0, no warning, both requested overlay fields absent.

## Why it matters

`goc wait` is part of the autonomous loop's vocabulary — `pull-card`
recipes that need to swap a wait reason (e.g. an `external` block
transitioning to a `deferred` window after a partial unblock) are a
natural use case. An agent that writes `goc wait <t> --clear --reason
deferred --until <date>` reasoning "drop the old overlay, set the
new one" gets the clear-only outcome with no signal — the next
`pull-card` then claims the card as ready, when the human's intent
was the opposite. The bug is silent because exit code is 0 and the
"cleared" message does not echo the discarded flags.

**Reachability path:** any human or agent running `goc wait <t>
--clear --reason X --until Y` from a shell, a skill body, or a
multi-step recipe. The argparse layer admits the combination; the
handler discards two of the three flags.

## Decision required

Two credible fix paths, both internally consistent. Pick one before
implementation.

**Option A — reject the mode-conflict (sibling-verb consistency).**
After parsing args, if `args.clear` is set AND (`args.reason` is not
None OR `args.until` is not None), print
`ERROR: --clear is mutually exclusive with --reason / --until` and
exit 2. Matches `_cmd_status`'s `--by`-guard convention at
`engine.py:3958-3964`. Pros: zero ambiguity, no silent data loss,
recipes that conflate the two modes get loud feedback. Cons: a
recipe that legitimately wants "clear then re-set" must now run two
invocations.

**Option B — treat `--clear` plus a set as a re-set (clear-then-set).**
Pop both fields first, then apply `--reason` / `--until` from the
same args as if they were the only flags. The final frontmatter
matches the explicit set. Pros: single-call recipe works; matches
the principle of least surprise for power users. Cons: diverges from
sibling-verb convention; the `--clear` flag becomes a redundant
modifier whenever a set is also present.

Recommendation: **Option A** for sibling-verb consistency. If a
clear-then-set recipe needs the atomicity, file a follow-up card to
add an explicit `--reset` flag rather than overloading `--clear`.

## Fix sketch (gated by decision above)

```python
# in _cmd_wait, after argparse and before the if args.clear block:
if args.clear and (args.reason is not None or args.until is not None):
    print(
        "ERROR: --clear is mutually exclusive with --reason / --until",
        file=sys.stderr,
    )
    sys.exit(2)
```

Or move the guard into argparse via a `mutually_exclusive_group`:

```python
group = p_wait.add_mutually_exclusive_group()
group.add_argument("--clear", action="store_true", ...)
# (--reason / --until cannot live in the same MEG because they compose
#  with each other; the handler-level guard is the simpler fit.)
```
