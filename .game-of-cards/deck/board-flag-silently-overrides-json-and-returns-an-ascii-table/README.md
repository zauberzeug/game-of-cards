---
title: board-flag-silently-overrides-json-and-returns-an-ascii-table
summary: "`--board` and `--json` are mutually exclusive renderers, but `_cmd_default` selects between them with a silent `if args.board: ... elif args.as_json:` chain, so `goc --board --json` prints an ASCII table with exit 0 and no diagnostic. Every neighbouring flag conflict in the same function refuses with exit 2 (`pass only one of --done / --status`), so a machine reader that composes both flags gets unparseable output instead of the usage error the CLI gives everywhere else."
status: done
stage: null
contribution: medium
created: "2026-08-18T04:33:11Z"
closed_at: "2026-08-18T04:40:58Z"
human_gate: none
advances:
  - query-flag-validation-is-opt-in-per-flag-and-new-flags-keep-missing-it
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero — `goc --board --json` and `goc --json --board` either emit parseable JSON or refuse with exit 2 and a diagnostic on stderr, and the `--done --status` precedent still exits 2.
  - [x] MECHANICAL: the renderer conflict is refused BEFORE the query runs, alongside the existing `pass only one of --done / --status` guard in `_cmd_default`, so a usage error never costs a full deck load.
  - [x] TDD: a regression test under `tests/` asserts the refusal (exit code 2, message names both flags) for both flag orders, and asserts `--board` alone and `--json` alone are untouched.
  - [x] MECHANICAL: `--board`'s and `--json`'s `--help` text state that the two are mutually exclusive, so the contract is legible without reading the source.
  - [x] MECHANICAL: the OpenClaw tool schema (`openclaw-plugin/index.ts`) documents that `board` and `json` cannot both be set, so an LLM caller is not invited into the refusal. Re-port and re-sync mirrors; `python3 scripts/port_skills_to_openclaw.py --check` clean.
  - [x] PROCESS: `uv run goc validate` clean and `uv run python -m unittest discover -s tests` green.
worker: {who: "claude[bot]", where: main}
---

# `--board` silently overrides `--json` and returns an ASCII table

## Location

- `goc/engine.py:4196-4204` — the renderer-selection chain in `_cmd_default`,
  which pre-fix was the *only* arbiter of the pair:

  ```python
  if args.board:
      board_cards = filtered if (status_filter_explicit or args.worker) else cards
      print(render_board(...))
  elif args.as_json:
      print(render_json(...))
  else:
      ...
  ```

- `goc/engine.py:4093-4095` — the neighbouring conflict that *was* already
  refused, and the precedent this card followed:

  ```python
  if args.done_flag and args.status_flag is not None:
      print("goc: error: pass only one of --done / --status", file=sys.stderr)
      sys.exit(2)
  ```

- `goc/engine.py:3811-3815` (parser block) — `--json` and `--board` are
  registered as independent store-true flags, with no
  `add_mutually_exclusive_group`.
- `openclaw-plugin/index.ts:99-110` / `:136-137` — the OpenClaw tool schema
  and `buildArgs`, which emit both tokens when both booleans are set.

## What's broken

`--board` and `--json` are two *renderers* for the same query, not a
renderer plus a modifier. Passed together they are a usage error, but
`_cmd_default` resolves them with a bare `if / elif`, so `--board` wins,
`--json` never runs, and the caller gets an ASCII grid on stdout with
exit 0 and an empty stderr.

The help text advertises no precedence:

```
  --json                Machine-readable JSON.
  --board               ASCII multi-column kanban board.
```

Contrast the two flags whose scope *is* documented — both say so in the
one place a reader looks:

```
  --slim                With --json: emit only title, status, ...
  --max-rows MAX_ROWS   Cap rows per column in --board.
```

`--json` and `--board` carry no such qualifier, so nothing tells a
reader that one silently voids the other.

The inconsistency is inside a single function. `_cmd_default` already
refuses two other flag combinations before doing any work — `--done`
with `--status` (line 4092) and `--since` without `--done` (line
4117) — each with `sys.exit(2)` and a diagnostic naming the flags.
`_commit_override` does the same for `--commit` with `--no-commit` on
the mutating verbs (see the closed
[mutating-verbs-leave-card-modified-on-conflicting-commit-flags](../mutating-verbs-leave-card-modified-on-conflicting-commit-flags/)).
So the CLI's established contract for "caller passed two flags that
select mutually exclusive behaviour" is *refuse with exit 2*. The
renderer pair is the one place that instead picks a winner in silence.

## Empirical evidence

`uv run python .game-of-cards/deck/board-flag-silently-overrides-json-and-returns-an-ascii-table/reproduce.py`
(exits 1 today):

```
PASS  --json alone emits JSON (exit=0)
FAIL  BUG: --board --json emits JSON or refuses — exit=0, stderr='', stdout[0]='OPEN                 | ACTIVE               | BLOCKED       '
FAIL  BUG: --json --board emits JSON or refuses — exit=0, stderr='', stdout[0]='OPEN                 | ACTIVE               | BLOCKED       '
PASS  precedent: --done --status refuses (exit=2: goc: error: pass only one of --done / --status)

2 failure(s)
```

Flag order does not matter — `argparse` has no ordering, so both
spellings take the `if args.board` branch. The script's fixture is a
one-card temp deck, and it accepts *either* fix shape (parseable JSON,
or exit 2 with a diagnostic) so it does not prejudge the spelling.

## Reachability

The failure is silent at the boundary and loud one hop downstream: a
`goc ... --json | jq` pipeline gets `parse error: Invalid numeric
literal`, with nothing on goc's stderr to explain it.

- **Composing the flags is invited by the docs.** `Skill(scan-deck)`
  lists them as adjacent lines of one recipe block
  (`goc/templates/skills/scan-deck/SKILL.md:150-151`), directly under
  the sentence "Existing flags compose with AND semantics on tags,
  intersect on other fields." Nothing in that block marks the two as
  exclusive, and `--slim`/`--max-rows` on either side of them *do*
  compose with their partner flag.
- **A wrapper that always appends `--json`** for machine parsing, over a
  caller-supplied flag set that includes `--board`, silently degrades to
  a table. This is the ordinary shape of any script or agent harness
  that shells out to `goc`.
- **Latent, on OpenClaw.** The registered `goc` tool declares `board`
  and `json` as independent optional booleans
  (`openclaw-plugin/index.ts:99-100`) and `buildArgs` emits both tokens
  when both are set (`openclaw-plugin/index.ts:126-127`). So
  `goc({board: true, json: true})` — a natural LLM call for "the board,
  machine-readable" — reaches this branch with no schema-level guard.
  That route is currently dead for an unrelated reason (`buildArgs`
  always injects a verb, so the no-subcommand renderer never runs at
  all — [openclaw-plugin-cannot-show-the-deck-queue-through-tool-or-exec](../openclaw-plugin-cannot-show-the-deck-queue-through-tool-or-exec/)),
  and goes live the moment that card lands.

## Scope boundary

**This is instance 2 of a catalogued family, found and fixed without
reaching the root card.**
[query-flag-validation-is-opt-in-per-flag-and-new-flags-keep-missing-it](../query-flag-validation-is-opt-in-per-flag-and-new-flags-keep-missing-it/)
(open, `human_gate: decision`) had already tabulated this exact defect as
its instance 2 — same file:line, same `pass only one of --done / --status`
precedent — and its DoD names "`--json` + `--board` conflict" as one of
four regression tests the meta-fix owes. The dedup pass that filed this
card grepped card *titles* for `board` and `json` and missed it, because
that card's title names the shape rather than either flag.

The edge is wired (`advances` → that card) and its instance table is
re-audited, but this fix does **not** advance its thesis: it is the sixth
hand-written per-pair guard on a surface whose defect is that guards are
per-pair. That card stays open with all five DoD items unticked — two rows
of its table are still unguarded (`--advances`/`--advanced-by` accept
nonexistent titles; `--closed-since` composes with a non-terminal
`--status` or `--waiting` into can-never-match queries), and only its item
5 (a contract that makes *future* query flags fail closed) would have
prevented this card from being needed at all.


Distinct from [board-view-silently-ignores-filters-other-than-status-and-worker](../board-view-silently-ignores-filters-other-than-status-and-worker/)
(open), which shares the same four lines of source. That card is about
**which filters reach `render_board`** — the `board_cards = filtered if
(status_filter_explicit or args.worker) else cards` predicate on line
4182. This card is about **which renderer runs at all** — the `if /
elif` on lines 4181/4189. Its body reads "`filtered` is what the table
renderer and the JSON renderer consume", treating the JSON renderer as
a peer that receives the query; it never notices that `--json` is
unreachable whenever `--board` is set. Fixing either one leaves the
other untouched: a filter-propagation fix still throws away `--json`,
and this refusal still lets `goc --tag bug --board` render the whole
deck.

## Fix (landed)

The pair is refused before the query runs, beside the `--done`/`--status`
guard three lines above it, so a usage error does not first pay for a full
deck load (`goc/engine.py:4096-4107`):

```python
if args.board and args.as_json:
    print(
        "goc: error: pass only one of --board / --json "
        "(alternative renderers)",
        file=sys.stderr,
    )
    sys.exit(2)
```

`load_all_cards()` moved below both guards for the same reason. The
`if args.board: … elif args.as_json:` chain is left as-is — with the guard
in front of it, the two branches can no longer both be live, so the chain
is now an ordering detail rather than a silent policy.

`argparse.add_mutually_exclusive_group` would also exit 2, but the two flags
are registered in the shared global-flag block that the subcommand parsers
inherit, so a manual guard in `_cmd_default` keeps the check on the one code
path where both flags are meaningful and matches how the sibling conflicts
are already spelled.

Two doc surfaces landed with it so the contract is legible without reading
the source:

- `--board` and `--json` each name the other in their `--help` text
  (`goc/engine.py:3811-3815`).
- The OpenClaw tool schema gives both booleans a `description` stating the
  exclusion and the exit-2 consequence, and the enclosing `flags` object
  says "set at most one" (`openclaw-plugin/index.ts:99-115`). This closes
  the latent route described above before it goes live.

A JSON *rendering of the board* (per-column arrays) is a separate feature,
not this defect's fix — file it on its own card if anyone wants it.
