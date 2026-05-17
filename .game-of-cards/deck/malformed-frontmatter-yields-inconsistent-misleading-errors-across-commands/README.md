---
title: malformed-frontmatter-yields-inconsistent-misleading-errors-across-commands
summary: |-
  When a card's README.md has the opening `---` but the closing `---` is missing,
  `goc show` succeeds, `goc validate` says "missing frontmatter", and `goc done`
  says "not found at <path>" — three different stories for the same defect.
  Unify the diagnostics by distinguishing "no opening delimiter" from
  "opening present, closing missing/unparseable".
status: done
stage: null
contribution: medium
created: "2026-05-17T06:01:33Z"
closed_at: 2026-05-17T06:08:22Z
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [x] `parse_frontmatter` raises a `FrontmatterError` when the opening `---` is present but the closing is absent/unparseable; still returns `({}, text)` when no opening delimiter exists at line 1.
  - [x] `goc validate` on a card with missing closing `---` reports `frontmatter unterminated: ...` (not "missing frontmatter").
  - [x] `goc done <card>` on the same card reports `frontmatter parse failed at <path>: frontmatter unterminated: ...` (not "not found at <path>").
  - [x] `goc show <card>` still prints the file content, but emits a stderr warning describing the parse failure.
  - [x] Other mutating commands that look up a card by title (`attest`, `advance`, `unadvance`, `move`, `decide`, `quality-pass`) report the same precise error via a shared helper.
  - [x] `reproduce.py` exits zero against the post-fix engine: pre-fix all three commands disagree; post-fix the three errors form a coherent story (show prints + warns; validate and done both name the unterminated frontmatter).
worker: {who: Rodja Trappe, where: main}
---

# malformed-frontmatter-yields-inconsistent-misleading-errors-across-commands

## Reported defect

A tester filed this bug against goc 0.0.17. When a card's `README.md`
has the opening `---` of frontmatter but is **missing the closing
`---` delimiter**, three commands disagree on what's wrong:

| Command | Behavior on a malformed card |
|---|---|
| `goc show my-card` | succeeds; prints the file as-is. No parse, no warning. |
| `goc validate` | `ERROR: my-card: README.md missing frontmatter` (misleading — the opening IS present) |
| `goc done my-card` | `ERROR: my-card: not found at /full/path/.../my-card` (doubly misleading — the dir and file both exist) |

The tester spent ~10 minutes diagnosing and tried `goc move` twice on
a path that wasn't broken, because the `not found at <path>` error
read like a path-resolution problem rather than a parse failure.

Real-world impact: a Write-tool body authored in one shot can silently
elide the closing `---`. The card looks fine via `goc show`
(frontmatter renders), but every mutating command then errors with a
message that points AWAY from the actual problem.

## Root cause

`parse_frontmatter` at `goc/engine.py:132`:

```python
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.DOTALL)

def parse_frontmatter(text: str) -> tuple[dict, str]:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text          # collapses two failure modes into one signal
    data = yaml.safe_load(m.group(1)) or {}
    return data, m.group(2)
```

The non-greedy regex requires BOTH `---` delimiters. On failure it
returns `({}, text)` — collapsing "no frontmatter at all" and
"opening present, closing missing" into the same empty-dict signal.
Each caller then translates that signal into its own misleading error:

- `load_card` (`goc/engine.py:433`) returns `None` when `fm` is empty.
  Every mutating command (`done` at 1943, `attest` at 2439, `advance`
  at 2564, `decide` at 2890, `unadvance`/`move`/`quality-pass`) maps
  `None` to `"not found at <card_dir>"`. The string suggests a path
  problem; the cause is a parse problem.
- `validate_deck_directories` (`goc/engine.py:500`) emits
  `"<title>: README.md missing frontmatter"` when `fm` is empty. The
  phrasing implies the entire frontmatter is absent; the actual state
  is "frontmatter has an opener but no closer".
- `_cmd_show` (`goc/engine.py:2991`) doesn't call `parse_frontmatter`
  at all — it just reads the file with `p.read_text()` and prints it.
  A malformed card prints exactly the same way a well-formed card
  does, so casual inspection misses the defect.

## Empirical evidence (pre-fix)

```
--- goc show ---
---
title: my-card
status: open
...
definition_of_done: |
  - [x] something

## Body starts here without a closing ---

--- goc validate ---
ERROR: my-card: README.md missing frontmatter
--- goc done ---
ERROR: my-card: not found at /private/tmp/goc-bug-repro/.game-of-cards/deck/my-card
```

See `reproduce.py` for an isolated repro that runs against an
ephemeral scratch deck.

## Fix

1. **Add a `FrontmatterError` exception class.** Subclass `ValueError`
   so legacy callers that catch `ValueError` continue to work.

2. **Make `parse_frontmatter` distinguish three cases:**
   - No opening `---` at line 1 → return `({}, text)` as today
     (legitimate non-frontmatter file).
   - Opening present, closing missing or unparseable → raise
     `FrontmatterError("frontmatter unterminated: opening '---' at "
     "line 1 has no matching closing '---' delimiter")`.
   - Both present → parse + return as today.

3. **Add a `load_card_or_exit(card_dir, title)` helper** at the
   engine layer that wraps `load_card` and centralizes the
   exit-with-diagnostic logic. Distinct messages for:
   - card dir missing → `not found at <card_dir>` (today's message,
     correct in this branch)
   - README.md missing → `README.md not found at <readme>`
   - frontmatter unterminated → `frontmatter parse failed at
     <readme>: frontmatter unterminated: ...`
   - opening `---` absent → `README.md at <readme> has no frontmatter
     (missing opening '---' at line 1)`

4. **Switch every mutating command** (`_cmd_done`, `_cmd_attest`,
   `_cmd_advance`, `_cmd_unadvance`, `_cmd_move`, `_cmd_decide`,
   `_cmd_quality_pass`, `_cmd_triage` if it loads cards by title)
   to use the helper. They each currently duplicate the same two-line
   `if t is None: print(...); sys.exit(2)` pattern — the helper
   replaces all of them.

5. **Update `validate_deck_directories`** to catch `FrontmatterError`
   per-card and surface the precise message (instead of collapsing to
   "missing frontmatter").

6. **Keep `_cmd_show` permissive** (still prints raw text), but call
   `parse_frontmatter` after printing and emit a stderr warning if it
   raises. The tester explicitly asked for unified behavior — a
   warning-not-fatal preserves `show`'s "let me look at a broken
   card" use case while removing the "show succeeds, validate fails"
   surprise.

## Why warning-not-fatal in show

`show` is the diagnosis tool a user reaches for when something else
broke. Making it fatal-on-parse-failure would create a chicken-and-egg:
the card you most need to inspect (the broken one) is the one you
can't see. A stderr warning surfaces the diagnostic without blocking
the read.

## Files touched

- `goc/engine.py` — `parse_frontmatter`, new `FrontmatterError`, new
  `load_card_or_exit`, every `_cmd_*` that today calls `load_card`
  directly, `validate_deck_directories`, `_cmd_show`.
- `reproduce.py` — isolated repro that scaffolds a fresh deck in a
  temp dir, writes a card with a missing closing `---`, runs all
  three commands, and asserts the post-fix invariants.
