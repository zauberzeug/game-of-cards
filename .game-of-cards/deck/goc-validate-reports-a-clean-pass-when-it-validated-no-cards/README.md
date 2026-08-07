---
title: goc-validate-reports-a-clean-pass-when-it-validated-no-cards
summary: "`goc validate` prints nothing and exits 0 when the deck resolves to zero cards — including when no deck directory exists at all. The frontmatter-drift gate that CI and the install-written pre-commit hook depend on therefore reports a clean pass without saying it checked nothing, so a mis-resolved deck (wrong cwd, unscaffolded checkout, nested worktree) reads byte-identically to a green run."
status: done
stage: null
contribution: medium
created: "2026-08-07T05:51:31Z"
closed_at: "2026-08-07T05:59:09Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, infra]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero — a card-less deck and a missing deck each print an outcome line instead of nothing.
  - [x] TDD: regression test pins all three states apart — cards present (per-card `OK` lines), deck present but empty, deck absent — and asserts the notice names the resolved deck path.
  - [x] TDD: the notice survives `--quiet`; the per-card `OK` lines still do not. Exit codes are unchanged in every case (0 when clean, 1 on errors).
  - [x] MECHANICAL: `goc/engine.py:_cmd_validate` states its outcome on the zero-card path; plugin mirrors re-synced byte-for-byte (`scripts/sync_plugin_assets.py --check` clean).
  - [x] PROCESS: `uv run goc validate` clean on this repo's own deck, and the suite carries no new failure — 928 → 935 tests with the same single pre-existing red, `test_canonical_tag_rows.test_live_cards_satisfy_every_state_row`, owned by `regression-suite-red-on-main-over-the-unverified-tag-row` (open, gate `decision`, untouched by this card).
worker: {who: "claude[bot]", where: main}
---

# `goc validate` reports a clean pass when it validated no cards

## Location

- [`goc/engine.py:4034-4093`](../../../goc/engine.py) — `_cmd_validate`. The
  only per-card output is the `OK  <title>` line inside the card loop
  (`engine.py:4055-4056`); the function ends at `if errors: sys.exit(1)`
  (`engine.py:4092-4093`) with no else-branch, so a run that walked zero
  cards falls off the end having printed nothing.
- [`goc/engine.py:966`](../../../goc/engine.py) — `load_all_cards()` returns
  `[]` for both an empty `DECK_DIR` and a `DECK_DIR` that does not exist.
- [`goc/engine.py:121-147`](../../../goc/engine.py) — `_resolve_deck_dir` /
  `DECK_DIR`. Resolution failure is not an error: the module falls back to a
  path that simply has nothing in it.

## What's broken

`_cmd_validate` reports by exception. Every signal it emits is a per-card
`OK`, an `ERROR:`, or a `WARN`:

```python
    for t in cards:
        per = validate_card(t, schema, all_titles)
        errors.extend(per)
        if not per and not args.quiet:
            print(f"OK  {t.title}")
        else:
            for e in per:
                print(f"ERROR: {e}", file=sys.stderr)
    ...
    if errors:
        sys.exit(1)
```

With `cards == []` the loop body never runs, `errors` stays empty, and the
command exits 0 having written zero bytes to either stream. Three distinct
states therefore share one rendering:

| state | stdout | stderr | exit |
|---|---|---|---|
| deck with 708 cards, all clean | 45757 B of `OK` lines | warnings | 0 |
| deck scaffolded but holding no cards | 0 B | 0 B | 0 |
| **no deck directory at all** | **0 B** | **0 B** | **0** |

The third row is the defect. `goc validate` is the only verb whose silence
is *defined* as success, and it is the one verb that cannot tell you it
never found a deck.

This contradicts the convention every other surface now follows. `goc
triage` says so in a sentence (`engine.py:6484-6486`):

> `print("No parked cards (gate ≠ none).")`

`--json` emits `[]`. `--board` emits its column header. And the queue table
was given the same treatment three days ago by
[empty-queue-view-prints-nothing-instead-of-saying-no-cards-match](../empty-queue-view-prints-nothing-instead-of-saying-no-cards-match/),
whose `render_empty_query_line` (`engine.py:3502`) exists precisely because
"the query ran and matched nothing" must be expressible. That card's
reasoning — *"Three states rendered byte-identically at exit 0"* — is
verbatim the situation here, one surface over. It swept the read views and
stopped at the gate.

## Empirical evidence

`uv run python .game-of-cards/deck/goc-validate-reports-a-clean-pass-when-it-validated-no-cards/reproduce.py`,
**at filing** (2 findings, exit 1):

```
--- B. scaffolded but empty deck
    exit code  : 0
    stdout     : 0 bytes
    stderr     : 0 bytes
    first line : (none)

--- C. no deck directory at all
    exit code  : 0
    stdout     : 0 bytes
    stderr     : 0 bytes
    first line : (none)

FINDING: B printed 0 bytes — a deck with no cards is silent.
FINDING: C printed 0 bytes — a MISSING deck is silent too;
         `goc validate` reports success for a deck it never found.

2 finding(s).
```

The same script **after the fix** (0 findings, exit 0) — exit codes unchanged,
the resolved path now named:

```
--- B. scaffolded but empty deck
    exit code  : 0
    stderr     : 123 bytes
    first line : No cards found in /tmp/…/scaffolded-empty/.game-of-cards/deck — validated 0 cards (structural checks still ran).

--- C. no deck directory at all
    exit code  : 0
    stderr     : 121 bytes
    first line : No cards found in /tmp/…/no-deck-at-all/.game-of-cards/deck — validated 0 cards (structural checks still ran).

0 finding(s).
```

## Why it matters

The reachability path is a *caller*, not a malformed card, which is why no
existing validator catches it. Two shipped callers read this exit code as
the frontmatter-drift gate:

1. **The pre-commit hook `goc install` writes** into every consuming repo:

   ```yaml
   - id: goc-validate
     entry: goc validate
     language: system
     pass_filenames: false
     files: ^\.game-of-cards/deck/.*$
   ```

   `pass_filenames: false` means the hook never learns which deck it was
   meant to check; it inherits whatever `DECK_DIR` resolves to from the
   hook's cwd.

2. **CI.** AGENTS.md calls the validation step load-bearing ("the validation
   step gates card-frontmatter drift"). A gate that passes green on zero
   cards can only be caught by someone reading its log closely enough to
   notice the absence of output — which is exactly what did not happen in
   [ci-skips-deck-validation-after-deck-moved-to-game-of-cards-directory](../ci-skips-deck-validation-after-deck-moved-to-game-of-cards-directory/),
   where the gate was dead in CI across the deck's growth to 224 cards.
   That card's root cause is a shell path guard and is a different fix; this
   card is the reason such a failure stays invisible once it happens.

Concrete misresolutions that produce a card-less `DECK_DIR` with no error:
running the hook or the step from a subdirectory that is its own git root, a
checkout where `.game-of-cards/deck/` has not been scaffolded yet, and a
linked worktree whose deck lives in the primary tree. In all three the
operator sees a green `goc validate` and concludes the deck is clean.

## Fix (landed)

`_cmd_validate` states its outcome on the zero-card path, immediately before
the `if errors: sys.exit(1)` that used to be the function's last statement:

```python
    if not cards:
        print(
            f"No cards found in {DECK_DIR} — validated 0 cards "
            f"(structural checks still ran).",
            file=sys.stderr,
        )
```

Three properties, each deliberate:

- **Names the resolved path.** The actionable fact is *which* directory was
  searched — that is what distinguishes "the deck is empty" from "I am
  standing in the wrong tree".
- **stderr, not stdout.** Warnings already go to stderr
  (`engine.py:4062-4073`) and `--quiet` documents its contract as
  suppressing the per-card `OK` lines on stdout. Routing the notice to
  stderr keeps it visible under `--quiet` — where the false green is most
  dangerous, because silence is the *expected* success rendering — without
  touching what stdout consumers parse.
- **No exit-code change.** A freshly scaffolded repo legitimately has an
  empty deck; failing there would break `goc install` → `goc validate`, the
  sequence `Skill(kickoff)` walks a new user through. The defect is the
  missing signal, not the exit code.

Deliberately *not* done: an unconditional "validated N cards" summary on the
non-empty path. The per-card `OK` lines already prove the gate ran, and
adding a trailing line would change output for every existing caller for no
additional signal.
