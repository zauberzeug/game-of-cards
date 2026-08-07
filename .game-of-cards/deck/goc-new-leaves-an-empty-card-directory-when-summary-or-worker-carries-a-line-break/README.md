---
title: goc-new-leaves-an-empty-card-directory-when-summary-or-worker-carries-a-line-break
summary: "Every input guard in `_cmd_new` (engine.py:5678-5704) runs before `card_dir.mkdir`, but `--summary` and `--worker` are only checked for blankness — a value carrying a line break the inline emitter refuses (any non-LF break for summary; any break at all for worker) gets past them and blows up at the README write on line 5728, after the directory exists. The result is an uncaught `FrontmatterError` traceback instead of the CLI's clean `ERROR:` + exit 2, plus an empty card directory that leaves `goc validate` red until a human finds and deletes it."
status: active
stage: null
contribution: medium
created: "2026-08-07T05:07:14Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero — all three doors (summary+CR, worker+CR, worker+LF) exit 2 with a clean `ERROR:` line, no traceback, and no directory left behind.
  - [ ] TDD: a regression test under `tests/` covers the refusal for both `--summary` and `--worker`, and asserts the deck directory is absent afterwards (not merely that the command failed).
  - [ ] MECHANICAL: the line-break check derives its dangerous-character set from the existing `_contains_line_break` helper rather than a fresh hand-copied list, so it cannot drift from the parser (same constraint the emitter card this one follows already imposed).
  - [ ] PROCESS: `uv run goc validate` clean, and `uv run python -m unittest discover -s tests` shows no failure other than the pre-existing one tracked by [regression-suite-red-on-main-over-the-unverified-tag-row](../regression-suite-red-on-main-over-the-unverified-tag-row/).
worker: {who: "claude[bot]", where: main}
---

# goc new leaves an empty card directory when --summary or --worker carries a line break

## Location

- `goc/engine.py:5665-5668` — `_cmd_new`'s only `--summary` check (blankness).
- `goc/engine.py:5670` — `worker = args.worker`, with no check at all.
- `goc/engine.py:5705` — `card_dir.mkdir(parents=True)`.
- `goc/engine.py:5728` — `(card_dir / "README.md").write_text(emit_frontmatter(...))`, where the refusal fires.
- `goc/engine.py:298` — `_yaml_inline`'s `raise FrontmatterError(...)`.
- `goc/engine.py:363` — `_emit_worker`, which routes every `worker` scalar through `_yaml_inline`.

## What's broken

`_cmd_new` validates its inputs in a deliberate order: every guard rejects and
exits **before** any filesystem write. Reading down from line 5678 —
antipattern guard, `title_pattern` regex, `card_dir.exists()`, unknown-tag
loop, `_validate_new_edge_flags` — and only then, at line 5705:

```python
    _validate_new_edge_flags(title, card_dir, advances, advanced_by)
    card_dir.mkdir(parents=True)
```

Two inputs are missing from that pre-mkdir set. `--summary` is checked only
for blankness (engine.py:5665-5668):

```python
    summary = args.summary
    if summary is not None and not summary.strip():
        print("ERROR: --summary must not be empty or whitespace-only", file=sys.stderr)
        sys.exit(2)
```

and `--worker` is not checked at all (engine.py:5670):

```python
    worker = args.worker
```

Both are emitted as YAML scalars 23 lines later, at line 5728. The emitter
refuses a scalar carrying a line break the vendored parser would split on —
correctly, and by design. That guard was installed by the closed card
[inline-emitter-writes-non-newline-line-breaks-bare-dropping-subsequent-frontmatter](../inline-emitter-writes-non-newline-line-breaks-bare-dropping-subsequent-frontmatter/),
whose DoD reads:

> - [x] TDD: a regression test asserts the emitter's behaviour for a scalar
>   containing a non-LF line break (CR/VT/FF/FS/GS/RS/NEL/LS/PS) — either it
>   raises a `FrontmatterError` like the existing `\n` case, or it round-trips
>   faithfully; it must NOT emit the value bare and silently drop trailing
>   fields.

Raising is the right behaviour. But nothing taught `_cmd_new`'s call site
about it, so the refusal arrives **after** `mkdir`, and two contracts break at
once:

1. **The CLI's error contract.** Every neighbouring rejection in `_cmd_new`
   prints `ERROR: ...` to stderr and exits 2. This one emits an uncaught
   Python traceback ending in `goc.engine.FrontmatterError` and exits 1.
2. **The deck's integrity.** The card directory has already been created and
   now holds neither `README.md` nor `log.md`. Nothing removes it, and the
   traceback never mentions that a directory was created — so the user has no
   idea cleanup is owed.

Which breaks are reachable differs per field, because the emitter treats them
differently. `emit_frontmatter` routes a `summary` containing LF into a
block scalar (that round-trips fine), so only the *non-LF* breaks reach
`_yaml_inline`. `worker` has no block-scalar path — `_emit_worker` sends every
scalar through `_yaml_inline` — so **any** break, LF included, refuses.

## Empirical evidence

`uv run python .game-of-cards/deck/goc-new-leaves-an-empty-card-directory-when-summary-or-worker-carries-a-line-break/reproduce.py`:

```
--- summary-with-CR ---
  argv          : goc new probe-summary-with-cr '--summary' 'first\rsecond'
  exit code     : 1   (contract: 2)
  traceback     : True   (contract: False)
  clean ERROR:  : False   (contract: True)
  orphan dir    : True   (contract: False)
  no README.md  : True   (contract: False)
  validate red  : True   (contract: False)
  last stderr   : goc.engine.FrontmatterError: frontmatter scalar contains a line-break character the vendored parser splits on (str.split

--- worker-with-CR ---
  argv          : goc new probe-worker-with-cr '--summary' 'fine' '--worker' 'alice\r'
  exit code     : 1   (contract: 2)
  traceback     : True   (contract: False)
  ... (identical verdict)

--- worker-with-LF ---
  argv          : goc new probe-worker-with-lf '--summary' 'fine' '--worker' 'alice\nbob'
  exit code     : 1   (contract: 2)
  traceback     : True   (contract: False)
  ... (identical verdict)

FAIL: `goc new` breaks its refusal contract and corrupts the deck:
  - summary-with-CR: refusal is not the CLI's clean `ERROR:` contract
  - summary-with-CR: exit 1, expected 2
  - summary-with-CR: left an orphan card directory behind
  - summary-with-CR: goc validate is red because of the orphan
  ... (same four for worker-with-CR and worker-with-LF)
```

The resulting deck state, verified live in a scratch install:

```
$ ls -a .game-of-cards/deck/cr-summary-card/
.  ..
$ goc validate
ERROR: cr-summary-card: card directory missing README.md
```

## Why it matters

**Reachability.** The offending scalar does not have to be typed. Command
substitution strips a trailing LF but *not* a trailing CR, so any value read
from a CRLF-terminated source arrives with `\r` still attached:

```bash
goc new my-card --summary "fine" --worker "$(cat .assignee)"   # CRLF file → 'alice\r'
```

That is an ordinary way to feed a worker slug, a summary pulled from an issue
export, or a value piped out of a Windows-authored file. The user sees a
Python traceback about `str.splitlines()` internals, which names neither the
flag at fault nor the directory just created.

**The failure is sticky.** `goc validate` runs as a pre-commit hook in
consuming repos, so the orphan directory turns every subsequent commit red —
not just the card the user was filing. Recovery requires knowing to
`rm -rf .game-of-cards/deck/<title>/`, which nothing in the output suggests.

**It is distinct from the two known `goc new` input defects**, and worse than
both. [goc-new-crashes-with-oserror-traceback-on-overlong-title](../goc-new-crashes-with-oserror-traceback-on-overlong-title/)
is the same contract violation but explicitly disclaims data corruption — its
body records that "the crash fires at `card_dir.exists()`, so no partial state
is created". [trailing-newline-title-passes-guards-and-scaffolds-unaddressable-card-dir](../trailing-newline-title-passes-guards-and-scaffolds-unaddressable-card-dir/)
is the inverse shape: a value that is wrongly *accepted*. This card is the only
one of the three where a correct refusal leaves the deck broken, and the only
one reached through the value flags rather than the title.

## Fix

Move the check to where every sibling guard already lives — before
`card_dir.mkdir(parents=True)` at engine.py:5705. Extend the existing
`--summary` blankness guard (engine.py:5665-5668) and add the matching
`--worker` guard, both rejecting with the CLI's clean `ERROR:` + `sys.exit(2)`
and naming the flag at fault.

The dangerous-character set must come from the existing `_contains_line_break`
helper (engine.py:225), not a fresh literal list — that single-source
constraint is what the predecessor emitter card's third DoD item bought, and
re-copying the set here would spend it. Note the asymmetry when writing the
predicate: `summary` legitimately supports LF (block scalar), so it must reject
only non-LF breaks (`_contains_line_break(value.replace("\n", ""))`, the same
expression `emit_frontmatter` uses at engine.py:423), while `worker` has no
block path and must reject any break.

Validating before `mkdir` is preferred over a try/except-and-unlink unwind:
it matches the ordering the rest of `_cmd_new` already establishes and leaves
no window in which a partially-created card exists at all.
