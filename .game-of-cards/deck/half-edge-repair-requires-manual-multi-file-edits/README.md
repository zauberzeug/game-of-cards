---
title: half-edge-repair-requires-manual-multi-file-edits
summary: "When `goc validate` reports half-edge errors (typically from cloud agents that bypass the pre-commit hook), the only fix today is a hand-edit of every offending pair. Add `goc repair-edges` so the validator's complaint maps to a one-command cleanup."
status: done
stage: null
contribution: medium
created: "2026-05-17T09:34:17Z"
closed_at: 2026-05-18T04:10:52Z
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, meta-fix]
definition_of_done: |
  - [x] `goc repair-edges` exists as a subcommand; with no args it scans every card and reports the half-edges that would be fixed (preview / dry-run by default)
  - [x] `goc repair-edges --apply` writes the missing reverse edge for every half-edge found, using the same atomic writers as `_mutate_pair`
  - [x] `--apply` is idempotent — re-running on a clean deck is a no-op and exits 0
  - [x] Repair refuses to "fix" anything that would create an `advances` cycle; that pair is reported separately as a structural problem requiring human review
  - [x] After `goc repair-edges --apply` on a half-edge-dirty deck, `goc validate` reports zero half-edge errors
  - [x] CI's `goc validate` failure message points at `goc repair-edges --apply` as the suggested remediation
  - [x] `goc/templates/skills/refine-deck/SKILL.md` updated to use `goc repair-edges` instead of describing manual repair
worker: {who: Rodja Trappe, where: main}
---

# half-edge-repair-requires-manual-multi-file-edits

## What's broken

When `validate_bidirectional_edges` (`goc/engine.py:913`) reports a
half-edge, today's remediation is:

1. Read the error line, parse out the two card slugs and the missing
   field name.
2. Open `deck/<offender>/README.md` to confirm the asymmetric edge.
3. Open `deck/<target>/README.md` and hand-edit the missing
   `advances:` or `advanced_by:` entry into the correct block-style
   YAML list, preserving emitter conventions.
4. `git add` both files and commit a "backfill" entry.

Every "backfill" / "repair half-edges" commit in the log
(`e8e6cb7`, `b4b004f`, and the partial fix inside
`release-yml-smoke-job-fails-on-tag-push-events`) executed exactly
this multi-file ritual by hand. The information needed to perform
the fix — which card is missing which reverse entry — is *already in
the validator's error string*. The CLI just doesn't act on it.

## Empirical evidence

The validator emits, per offence:

```
<src>: <field> contains '<ref>' but <ref>.<inverse> is missing '<src>' (half-edge)
```

This string contains every datum needed to compute the fix
(`<ref>` is missing `<src>` in `<inverse>`; add it). The fix is
mechanical: append `<src>` to `<ref>`'s `<inverse>` list via
`_add_to_list_field` (`goc/engine.py:2746`), the same primitive
`_mutate_pair` already uses.

Recent half-edge backfill diff (commit `e8e6cb7`) shows the shape of
what `goc repair-edges --apply` would produce automatically:

```diff
-advanced_by: []
+advanced_by:
+  - publish-npm-package-under-zauberzeug-org-not-personal
```

Three such two-line diffs across three files; the rest of the
commit's bulk was the manual editor session and the explanatory
commit message.

## Why it matters

The sibling card
[half-edge-errors-recur-because-goc-new-cannot-wire-edges](../half-edge-errors-recur-because-goc-new-cannot-wire-edges/)
closes the local-author path (most-frequent source). Half-edges
can still arrive via:

- Cloud agents that push commits via the GitHub API and bypass the
  pre-commit `goc validate` hook.
- Future writers (custom scripts, external tools) that touch
  frontmatter without going through `_mutate_pair`.

For those residual cases, the validator catches them in CI but the
fix is still a manual ritual. `goc repair-edges --apply` turns
"CI red → engineer reads error → hand-edits two files → commits"
into "CI red → run one command → commit". It also means the
validator's complaint becomes self-resolving in autonomous loops,
not a human-decision gate.

## Fix

Add `goc repair-edges` as a new subcommand:

- **Default behavior**: dry-run preview. Print each half-edge the
  command *would* fix, formatted as the diff the writer would apply.
  Exit 0 even if half-edges exist (preview is informational).
- **`--apply`**: perform the fixes using `_add_to_list_field` on the
  reverse-edge side. Idempotent. Atomic per pair (either both halves
  of the pair are consistent at the end, or neither is touched and
  the pair is reported as a structural error).
- **Cycle guard**: if applying a reverse edge would close an
  `advances` cycle, refuse that one pair (report it separately) and
  continue with the rest. Cycles are a structural error that needs
  human judgment about *which* edge is wrong.
- **CI integration**: when `goc validate` fails with half-edge
  errors, the final line of its output should suggest
  `Run 'goc repair-edges --apply' to fix.`

This is a thin tool — the validator already builds the graph and
identifies every defect; `repair-edges` is the symmetric writer
hooked up to the existing diagnostic.

## Cross-references

- Sibling card:
  `half-edge-errors-recur-because-goc-new-cannot-wire-edges`
  (the preventive half — closes the dominant source so this command
  handles only the residual cloud-agent leak)
- Validator that produces the input: `goc/engine.py:913`
- Symmetric writer to reuse: `goc/engine.py:2746`
  (`_add_to_list_field`) and `goc/engine.py:2768` (`_mutate_pair`)
- Cycle guard to reuse: `goc/engine.py:960`
  (`_would_create_advance_cycle`)
