---
title: non-canonical-title-spellings-write-dangling-edges-and-self-references
summary: "resolve_card_dir accepts non-canonical spellings of an in-deck title (trailing slash, ./ prefix) even though its docstring declares titles are bare card-directory names. Every caller then uses the raw argument string as the card's identity, so goc advance / unadvance / status --by write the unnormalized spelling into frontmatter edge fields and goc done --bundle takes it as a distinct member. Result: dangling references, half-edges, a self-edge that bypasses the title == advancer guard, and a doubled bundle attestation — all reported as success (exit 0) and auto-committed."
status: active
stage: null
contribution: high
created: "2026-08-02T05:32:42Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero — every non-canonical spelling of an in-deck title is refused with exit 2 before any read or write
  - [ ] TDD: regression test covers `resolve_card_dir` directly (`alpha/`, `./alpha`, `alpha//` rejected; `alpha` accepted) and at least one write door end-to-end (`goc advance a --by a/` refuses instead of writing a self-edge)
  - [ ] MECHANICAL: `resolve_card_dir` enforces the contract its own docstring states — a title argument is the bare card-directory name, not any path spelling that happens to resolve into the deck
  - [ ] PROCESS: forward pointer added to the closed [path-shaped-title-arguments-let-verbs-read-and-mutate-files-outside-the-deck](../path-shaped-title-arguments-let-verbs-read-and-mutate-files-outside-the-deck/), whose guard this completes
  - [ ] PROCESS: `uv run goc validate` passes and `uv run python -m unittest discover -s tests` is green
worker: {who: "claude[bot]", where: main}
---

# non-canonical-title-spellings-write-dangling-edges-and-self-references

## Location

`goc/engine.py:1020` — `resolve_card_dir`, the shared title-argument
guard every verb routes through:

```python
if (
    len(Path(title).parts) != 1
    or title == ".."
    or (DECK_DIR / title).resolve().parent != DECK_DIR.resolve()
):
    print(
        f"ERROR: invalid card title {title!r} — a title is the bare card "
        f"directory name inside the deck, not a path",
        file=sys.stderr,
    )
    sys.exit(2)
return DECK_DIR / title
```

Consumers of the raw argument string:

- `goc/engine.py:5928` — `_cmd_advance`'s self-edge guard,
  `if title == advancer`.
- `goc/engine.py:5698-5699` — `_mutate_pair` writes `parent_title` /
  `child_title` verbatim into the frontmatter list fields.
- `goc/engine.py:4424-4431` — `_cmd_done_bundle`'s duplicate-member
  guard, `if title in seen`.

## What's broken

`resolve_card_dir` refuses a title that would *leave* the deck, but not
one that merely spells an in-deck card non-canonically. `Path` folds
both offending forms away before the check ever runs:

```
Path("alpha-card/").parts  == ("alpha-card",)   # len 1 → passes
Path("./alpha-card").parts == ("alpha-card",)   # len 1 → passes
```

Both then resolve to `DECK_DIR / "alpha-card"`, so the directory check
passes too. The function returns the right `Path` — and the caller
throws that away and keeps using the raw string as the card's
**identity**. Its own docstring states the contract it fails to
enforce:

> Titles are bare card-directory names; every verb that resolves a
> title argument must come through here.

Two guards are raw string compares, so a second spelling of one card
reads as a second card:

```python
if title == advancer:                      # _cmd_advance
    print("ERROR: cannot advance a card with itself", file=sys.stderr)
```

```python
if title in seen:                          # _cmd_done_bundle
    print(f"goc: error: --bundle: duplicate title {title!r}", ...)
```

And `_mutate_pair` stores the spelling rather than the resolved name:

```python
(child_dir / "README.md").write_text(op(child_text, field_on_child, parent_title))
(parent_dir / "README.md").write_text(op(parent_text, field_on_parent, child_title))
```

When both spellings name the same card, those two lines are also a lost
update: both texts are read before either write, so the second
`write_text` clobbers the first — which is why the self-edge case ends
up with `advances: [alpha-card]` and an *empty* `advanced_by` rather
than both halves.

Every door reports success (exit 0) and, under the default
`auto_commit: true`, commits the damage.

## Empirical evidence

`uv run python .game-of-cards/deck/non-canonical-title-spellings-write-dangling-edges-and-self-references/reproduce.py`:

```
[1] goc advance alpha-card --by alpha-card/   -> exit 0
    advance: alpha-card.advanced_by += alpha-card/; alpha-card/.advances += alpha-card
[2] goc advance beta-card --by ./delta-card   -> exit 0
    advance: beta-card.advanced_by += ./delta-card; ./delta-card.advances += beta-card
[3] goc status delta-card superseded --by beta-card/ -> exit 0
      superseded_by: beta-card/; beta-card/.supersedes += delta-card
[4] goc validate -> exit 1, 6 error(s):
    ERROR: alpha-card: advances: self-reference 'alpha-card'
    ERROR: beta-card: advanced_by: references unknown title './delta-card'
    ERROR: delta-card: superseded_by: references unknown title 'beta-card/'
    ERROR: alpha-card: advances contains 'alpha-card' but alpha-card.advanced_by is missing 'alpha-card' (half-edge)
    ERROR: beta-card: supersedes contains 'delta-card' but delta-card.superseded_by is missing 'beta-card' (half-edge)
    ERROR: delta-card: advances contains 'beta-card' but beta-card.advanced_by is missing 'delta-card' (half-edge)
[5] goc done --bundle solo-card solo-card/   -> exit 0
    ['Bundled close: 2 cards.', 'Next: commit the closures together.']
    log.md attestation blocks: 2
    - **Bundled with**: solo-card/
    - **Bundled with**: solo-card

DEFECT FIRES — 7 finding(s):
```

Three commands leave six `goc validate` errors. The bundle door closes
one card while reporting two, writes the shared attestation block twice
into the same `log.md`, and records the card as bundled with itself
under both spellings.

`goc new --advances ./beta-card` is **not** affected: `_cmd_new` checks
the referenced titles against the loaded title set before writing, so it
already refuses with `referenced card(s) not found: ./beta-card`. That
membership check is the behaviour the other doors lack.

## Why it matters

The reachability path is the CLI argument itself — no file authoring or
hand-edited YAML is needed, only a spelling a reader plausibly types:

- Shell tab-completion appends a trailing slash to directory names, so
  a maintainer completing a title from inside `.game-of-cards/deck/`
  produces `alpha-card/` without noticing.
- This repo's own DoD cross-reference convention is
  `[<title>](../<title>/)` — copying the slug out of a card body brings
  the trailing slash along.
- `ls -p` / `ls --classify` output carries the same suffix.

The damage is silent at the point of use and durable: exit 0, a
success message echoing the bad spelling back as if it were a card
name, and an auto-commit. The next `goc validate` — likely in CI, on
someone else's branch — is where it surfaces, as a half-edge and a
dangling reference in the deck's relationship graph. Because the deck
is scheduler *and* record, a corrupted edge also mis-sorts the value
graph and can hide or surface the wrong cards in `goc --ready`.

This is the residual of
[path-shaped-title-arguments-let-verbs-read-and-mutate-files-outside-the-deck](../path-shaped-title-arguments-let-verbs-read-and-mutate-files-outside-the-deck/),
which introduced `resolve_card_dir` to stop title arguments escaping the
deck. That card fixed escape; it did not make the accepted set
*canonical*, so in-deck aliasing survived.

## Fix

Tighten the single guard so the accepted set is exactly the spellings
that can round-trip as identity — `goc/engine.py:1033`:

```python
if (
    len(Path(title).parts) != 1
    or title != Path(title).name
    or title == ".."
    or (DECK_DIR / title).resolve().parent != DECK_DIR.resolve()
):
```

`Path("alpha-card").name == "alpha-card"` passes; `"alpha-card/"`,
`"./alpha-card"` and `"alpha-card//"` all have `.name == "alpha-card"`
and are refused with the error the function already prints — which
reads correctly for exactly this case ("a title is the bare card
directory name inside the deck, not a path"). The existing empty-string
and `.`/`..` rejections are unaffected (`Path("").parts == ()`).

Rejecting rather than normalizing is what keeps the fix single-site:
normalizing would mean threading a canonical title back to every caller
that uses `args.title` for guards, edge values and messages
independently — a dozen sites — whereas rejection preserves the
invariant those sites already assume, that the typed identity and the
stored identity are the same string.
