---
title: backfill-script-reintroduces-bare-closed-at-the-migration-removed
summary: "`scripts/backfill_terminal_closed_at.py:85` writes `closed_at` by handing the raw `%Y-%m-%dT%H:%M:%SZ` string to `mutate_frontmatter_field`, bypassing `_yaml_inline`, so it emits the bare `closed_at: 2026-…Z` form that `emit_frontmatter` re-emits quoted. It is the one surviving call site missed by the sweep in the closed card `closed-at-format-drifts-between-closure-verbs-and-frontmatter-emitter`, whose DoD claimed every colon-bearing `mutate_frontmatter_field` site was routed through `_yaml_inline` or documented as intentionally bare. Live reach is currently nil (no terminal non-done card carries a null `closed_at`), but any future run re-introduces the drift that card's migration removed."
status: done
stage: null
contribution: low
created: "2026-07-26T22:00:52Z"
closed_at: "2026-07-26T22:10:08Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, infra]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits 1 before the fix (both probes FAIL) and 0 after — the script's emitted line becomes byte-identical to `emit_frontmatter`'s for the same value.
  - [x] TDD: a regression test asserts the *property* for every `mutate_frontmatter_field(..., "closed_at", X)` call site under `goc/` and `scripts/` — `X` must route through `_yaml_inline` — so a newly added writer fails closed instead of relying on a one-time manual sweep.
  - [x] MECHANICAL: `scripts/backfill_terminal_closed_at.py` routes the timestamp through `_yaml_inline` (import extended at line 33); the value it writes is unchanged.
  - [x] MECHANICAL: the parent card [closed-at-format-drifts-between-closure-verbs-and-frontmatter-emitter](../closed-at-format-drifts-between-closure-verbs-and-frontmatter-emitter/) gets a forward pointer to this card (post-close evidence amends the closed card; its ticked "any other call site" box was not true).
  - [x] PROCESS: `uv run goc validate` clean and `uv run python -m unittest discover -s tests` green; no deck-wide `closed_at` re-quote diff is produced by the fix.
worker: {who: "claude[bot]", where: main}
---

# The backfill script re-introduces the bare `closed_at` form the migration removed

## Location

- [`scripts/backfill_terminal_closed_at.py:85`](../../../scripts/backfill_terminal_closed_at.py)
  — the write:

  ```python
  ts = latest_readme_commit_iso(readme)          # "%Y-%m-%dT%H:%M:%SZ"
  ...
  text = mutate_frontmatter_field(text, "closed_at", ts)
  ```

- [`scripts/backfill_terminal_closed_at.py:38-56`](../../../scripts/backfill_terminal_closed_at.py)
  — `latest_readme_commit_iso`, which produces the colon-bearing shape:
  `dt.strftime("%Y-%m-%dT%H:%M:%SZ")`.

- The four engine `closed_at` writers, all routed:
  [`goc/engine.py:4296`](../../../goc/engine.py) (`_cmd_done`),
  [`goc/engine.py:4393`](../../../goc/engine.py) (`_cmd_done_bundle`),
  [`goc/engine.py:5336`](../../../goc/engine.py) (`do_status`
  disproved/superseded) — each `mutate_frontmatter_field(text,
  "closed_at", _yaml_inline(...))`.

- The quote contract:
  [`goc/engine.py:208`](../../../goc/engine.py)
  (`_YAML_NEEDS_QUOTE = re.compile(r"[:#'\"\\\[\]\{\}\,`@]")`) — the `:`
  in a full timestamp matches, so `_yaml_inline` returns the quoted form.

## What's broken

`mutate_frontmatter_field` is a line-anchored regex substitution that
inserts the value string verbatim, with no YAML quoting. Every engine
closure path therefore wraps a colon-bearing value in `_yaml_inline`
first. The backfill script does not — it passes `ts` raw, so it writes:

```yaml
closed_at: 2026-05-29T09:58:40Z
```

where the emitter, reached through `emit_frontmatter`, writes:

```yaml
closed_at: "2026-05-29T09:58:40Z"
```

This is a **sweep gap, not a new defect shape**. The closed card
[closed-at-format-drifts-between-closure-verbs-and-frontmatter-emitter](../closed-at-format-drifts-between-closure-verbs-and-frontmatter-emitter/)
fixed the drift in May 2026 and migrated 251 cards. Its DoD carried a
ticked box that explicitly claimed this site:

> - [x] MECHANICAL: the closure-verb paths (`_cmd_done`,
>   `_cmd_done_bundle`, the `disproved` / `superseded` write in
>   `do_status`) **and any other call site of `mutate_frontmatter_field`
>   for a colon-bearing value** either route the value through
>   `_yaml_inline` first or document the intentional bare form.

`scripts/backfill_terminal_closed_at.py:85` is such a call site. It
neither routes through `_yaml_inline` nor documents an intentional bare
form — the module docstring says only that it "writes that timestamp
into the frontmatter". The parent card's own Location section scoped its
search to `goc/engine.py` ("search for `mutate_frontmatter_field(text,
"closed_at"` for all sites"), and `scripts/` was never walked.

## Empirical evidence

`reproduce.py` derives both probes from the repo — it re-scans the real
call sites, and Probe 2 evaluates the value expression it finds at the
script's own call site, so neither probe can pass while the code is
wrong or fail once it is right. `GOC_BACKFILL_SRC=<path>` points the
scan at an alternate copy of the script, which keeps the pre-fix
behaviour checkable after the fix lands.

Before the fix (`GOC_BACKFILL_SRC` pointed at the pre-fix source), exit 1:

```
== Probe 1: does every `closed_at` writer route through `_yaml_inline`? ==

site                                                  value expression                    routed
----------------------------------------------------  ----------------------------------  ------
goc/engine.py:4296                                    _yaml_inline(now)                   yes
goc/engine.py:4393                                    _yaml_inline(now)                   yes
goc/engine.py:5336                                    _yaml_inline(_utc_now_iso())        yes
/tmp/backfill_before.py:85                            ts                                  NO

[FAIL] 1 closed_at writer(s) bypass the emitter quote contract:
        /tmp/backfill_before.py:85 passes ts without _yaml_inline

== Probe 2: does the written line survive a full-frontmatter rewrite? ==

  backfill script writes : closed_at: 2026-05-29T09:58:40Z
  engine closure writes  : closed_at: "2026-05-29T09:58:40Z"
  emit_frontmatter emits : closed_at: "2026-05-29T09:58:40Z"

[FAIL] the script's line differs from the emitter's line for the same value —
       the next `goc decide` / `migrate-list-style` / `repair-edges` rewrite
       re-quotes this card with no authored change.

  value round-trips unchanged either way: '2026-05-29T09:58:40Z'

DEFECT REPRODUCED (2 failing check(s))
```

After the fix, exit 0:

```
scripts/backfill_terminal_closed_at.py:96             _yaml_inline(ts)                    yes

[OK]   every closed_at writer routes through _yaml_inline

  backfill script writes : closed_at: "2026-05-29T09:58:40Z"
  engine closure writes  : closed_at: "2026-05-29T09:58:40Z"
  emit_frontmatter emits : closed_at: "2026-05-29T09:58:40Z"

[OK]   the script's line is byte-identical to the emitter's line

DEFECT FIXED (0 failing check(s))
```

The value itself round-trips correctly through the vendored parser in
either form — this is a **format** defect, not a data-loss defect
(contrast the sibling
[backfill-terminal-closed-at-stamps-latest-edit-date-as-closure-date](../backfill-terminal-closed-at-stamps-latest-edit-date-as-closure-date/),
which is about the *value* the same script computes being wrong).

Deck state confirming the parent's migration held, and that this script
is the only remaining regression vector:

```
$ grep -rhc '^closed_at: "' .game-of-cards/deck/*/README.md | ...
  quoted full timestamps : 378
  bare date-only         : 125   (correct — no colon, emitter leaves these bare)
  bare full timestamps   : 1     (a fenced code sample inside the parent card's own README)
  null                   : 173
```

## Why it matters

The reachability path is the script's only purpose: it walks every
`disproved`/`superseded` card whose `closed_at` is null and stamps a
timestamp. Any such card is enough to re-introduce the drift.

Consequence, as the parent card documented it: a bare `closed_at` traps
the next *full-frontmatter* rewrite in a spurious diff.
`emit_frontmatter` is reached by `goc decide`, `goc migrate-list-style`,
and `goc repair-edges` — so a card nobody edited gets its `closed_at`
line re-quoted, and that noise lands in a commit about something else.
That is exactly the 251-card diff the parent card's migration pass
existed to prevent.

Two facts bound the severity to `contribution: low`:

1. **Live reach is currently nil.** `goc --status all --json` reports
   zero `disproved`/`superseded` cards with a null `closed_at`, because
   `do_status` (`goc/engine.py:5336`) now stamps closure dates itself.
   The script has no targets today.
2. **Not shipped.** `pyproject.toml` sets `packages = ["goc"]`, so
   `scripts/` is absent from the wheel. The blast radius is this repo's
   own maintenance path.

It is still worth closing rather than deleting: the script remains the
documented recovery path for hand-authored terminal cards, and leaving
one unswept writer behind makes the parent card's ticked
"any other call site" box false.

## Fix (landed)

The value now routes through `_yaml_inline`, matching the three engine
precedents — `scripts/backfill_terminal_closed_at.py:96`:

```python
text = mutate_frontmatter_field(text, "closed_at", _yaml_inline(ts))
```

with `_yaml_inline` added to the `from goc.engine import ...` block. The
written *value* is unchanged; only its on-disk quoting is.

`tests/test_closed_at_canonical_form.py` — the parent card's own
regression suite — gains a `ClosedAtWriterContractTest` that asserts the
**property** instead of enumerating verbs: every
`mutate_frontmatter_field(..., "closed_at", X)` call site under `goc/`
and `scripts/` must have `_yaml_inline` in `X`. A second test pins the
scan to the two files that definitionally write `closed_at`, so the
contract test cannot start passing vacuously if the matcher ever stops
matching — which is precisely how the parent card's one-time manual
sweep rotted.

The test is deliberately scoped to `closed_at` rather than "any
colon-bearing value": the general rule is not statically decidable
(`mutate_frontmatter_field(text, "status", new_status)` is safe only
because argparse `choices` bounds it; `"worker", worker_yaml` was
already run through `_yaml_inline` a frame up), and widening it would
require a per-callsite allowlist that drifts the same way the sweep did.
`closed_at` is the one field whose value is always a colon-bearing
timestamp, so for it the rule is exact.

`goc/templates/`, `claude-plugin/`, `codex-plugin/`, and
`openclaw-plugin/` need no change: `scripts/` is not mirrored into any
plugin payload, and the engine sites were already correct. The plugin
`goc/` mirrors are excluded from the scan for the same reason —
`tests/test_plugin_mirror_parity.py` already guarantees they are
byte-identical to `goc/`, so scanning them would re-report each engine
site under four names.
