---
title: title-guard-shows-regex-error-instead-of-helpful-suggestion
summary: "The TITLE_ANTIPATTERNS guard at engine.py:1662 carries two patterns (_md_|_py_ and camelCase) that the schema's title regex strips first, so anyone typing `fix_md_thing` or `fixThing` sees a cryptic regex-pattern error instead of the helpful 'source-file infix; describe the *concept*, not the file' suggestion the maintainer authored. The dead branches also misalign with the LLM quality-pass prompt, which still tells Sonnet those antipatterns are catchable."
status: open
stage: null
contribution: medium
created: 2026-05-05
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] reproduce.py exits zero (defect no longer fires)
  - [ ] `goc new fix_md_thing` (and similarly `goc new fixThing`) prints the antipattern reason ("source-file infix..." / "camelCase token...") instead of (or alongside) the bare regex-mismatch error
  - [ ] TITLE_ANTIPATTERNS and the `_QUALITY_PROMPT_TEMPLATE` antipattern enumeration agree about which antipatterns are catchable at filing time
  - [ ] No regression in the existing rN / path-N / phase-N / bug-N branches (still reachable, still rejected with their authored reasons)
---

# title-guard-shows-regex-error-instead-of-helpful-suggestion

## Location

- `goc/engine.py:1662-1669` (TITLE_ANTIPATTERNS table)
- `goc/engine.py:1687-1700` (`new` command: schema regex check at 1688 runs *before* antipattern guard at 1692)
- `goc/schema.yaml:16` (`title_pattern: "^[a-z0-9][a-z0-9-]*[a-z0-9]$"`)
- `goc/engine.py:1029-1031` (LLM quality-pass prompt enumerates `_md_/_py_` and camelCase as antipatterns)

## What's broken

The maintainer wrote a six-row antipattern table with deliberately gentle, instructive error messages:

```python
TITLE_ANTIPATTERNS = [
    (re.compile(r"\br\d+\b"), "internal investigation-round reference (rN); describe the *observable problem* instead"),
    (re.compile(r"\bpath-\d+\b"), "sub-investigation step number; promote to a noun-phrase deliverable"),
    (re.compile(r"\bphase-\d+\b"), "internal sequence reference; name the deliverable instead"),
    (re.compile(r"\bbug-\d+\b"), "bug-tracker numbering; use the defect-shape clause"),
    (re.compile(r"_md_|_py_"), "source-file infix; describe the *concept*, not the file"),
    (re.compile(r"[a-z][A-Z]"), "camelCase token; lower-kebab the intent"),
]
```

But `new` enforces the schema title-regex first, and only on success runs the antipattern guard:

```python
schema = load_schema()
if not re.match(schema.title_pattern, title):
    click.echo(f"ERROR: title {title!r} does not match {schema.title_pattern!r}", err=True)
    sys.exit(2)
if not allow_jargon:
    antipatterns_hit = _check_title_antipatterns(title)
```

The schema regex (`^[a-z0-9][a-z0-9-]*[a-z0-9]$`) accepts only lowercase letters, digits, and hyphens. Therefore:

- Underscore titles like `fix_md_thing` — rejected by the schema regex, never reach the antipattern guard. The user sees `ERROR: title 'fix_md_thing' does not match '^[a-z0-9][a-z0-9-]*[a-z0-9]$'` and must reverse-engineer what kebab-case is.
- camelCase titles like `fixThing` — same fate. The "camelCase token; lower-kebab the intent" message is never shown.

The two branches `_md_|_py_` and `[a-z][A-Z]` are unreachable code — the patterns can never match a string that survives the regex above them.

The drift is also visible in the LLM quality-pass prompt at `engine.py:1029-1031`, which tells Sonnet:

```text
- Bad: "pong-late-hr-stuck-below-50-after-bug-140-path-2"
  (engineer's-jargon: rN refs, path-N, bug-N, math symbols, _md_/_py_,
  camelCase tokens — same antipattern set as deck.py `new` rejects)
```

The "same antipattern set as deck.py `new` rejects" claim is no longer true: `_md_/_py_` and camelCase are gated out at `new`, not by the antipattern set.

## Empirical evidence

`uv run python .game-of-cards/deck/title-guard-shows-regex-error-instead-of-helpful-suggestion/reproduce.py`:

```
schema title_pattern = ^[a-z0-9][a-z0-9-]*[a-z0-9]$

  [REACHABLE] '\\br\\d+\\b'  →  'internal investigation-round reference (rN); describe the *observable problem* instead'
  [REACHABLE] '\\bpath-\\d+\\b'  →  'sub-investigation step number; promote to a noun-phrase deliverable'
  [REACHABLE] '\\bphase-\\d+\\b'  →  'internal sequence reference; name the deliverable instead'
  [REACHABLE] '\\bbug-\\d+\\b'  →  'bug-tracker numbering; use the defect-shape clause'
  [UNREACHABLE] '_md_|_py_'  →  'source-file infix; describe the *concept*, not the file'
  [UNREACHABLE] '[a-z][A-Z]'  →  'camelCase token; lower-kebab the intent'

unreachable branches: 2 / 6

--- `goc new fix_md_thing` stderr ---
ERROR: title 'fix_md_thing' does not match '^[a-z0-9][a-z0-9-]*[a-z0-9]$'
--- end ---

BUG: the user sees only a regex-mismatch error; the authored teaching message is buried.
```

Exit code: 1 (will flip to 0 once the helpful antipattern reason is shown for `fix_md_thing` or similar).

## Why it matters

The antipattern guard exists precisely so a contributor (human or agent) doesn't bounce off a regex error. A new agent invoking `goc new my_first_card` to scaffold work today gets a regex-pattern error message, not the kind teaching message the maintainer wrote. That's the opposite of the guard's stated intent ("Titles are kanban labels; a non-engineer must understand the card from the title alone.").

It's also a one-card hygiene fix that surfaces cleanly: either reorder the checks (run antipatterns first, then regex), or move underscore/uppercase rejection into the antipattern table and drop them from the schema's regex (or augment the schema-regex error path to consult the antipattern explanations).

## Fix (for the implementer — do NOT apply now)

Two viable shapes:

1. **Reorder + extend antipatterns** — run `_check_title_antipatterns` before the schema-regex check; expand the antipattern table to cover underscores explicitly (e.g. `(re.compile(r"_"), "underscore in title; use a hyphen instead")`); keep the schema regex as the final correctness check for anything the antipatterns missed.
2. **Compose error messages** — when the schema regex fails, also run the antipattern set against the same string and concatenate any antipattern reasons into the error output. This keeps the regex as the single source of truth for legality but recovers the teaching messages.

Option 1 is cleaner; option 2 is smaller. Either way the LLM prompt at lines 1029-1031 should be re-aligned with whichever invariant survives.
