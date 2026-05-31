---
title: decide-misparses-fenced-double-hash-line-as-decision-section-terminator
summary: "`DECISION_REQUIRED_RE` terminates the `## Decision required` section at the first line beginning `## ` *anywhere downstream*, including lines inside a fenced code block (a shell `## comment`, a `## Header` shown as markdown example, a makefile target with `##`). `goc decide` then truncates the archived deliberation and rewrites the README with a stray `## ` heading, an orphaned closing fence, and the rest of the deliberation stranded below the resolved `## Decision` block."
status: open
stage: null
contribution: medium
created: "2026-05-30T23:39:22Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero — `goc decide` preserves the full deliberation prose in the log.md archive and leaves no stray `## ` heading or orphaned fence in the rewritten README
  - [ ] TDD: regression test in `tests/` exercises a `## Decision required` body containing a fenced code block whose content has a line starting with `## ` and asserts the chosen behaviour
  - [ ] MECHANICAL: `DECISION_REQUIRED_RE` (or its callers `extract_decision_required_section` / `replace_or_append_decision` in `goc/engine.py:366-393`) is fence-aware — either via a tiny fence-tracking scanner, a real markdown parser, or the chosen alternative
  - [ ] PROCESS: decision recorded inline (which fence-handling approach was picked and why; cf. sibling decide-family rebuttals)
---

# decide-misparses-fenced-double-hash-line-as-decision-section-terminator

## Location

`goc/engine.py:366-393` — `DECISION_REQUIRED_RE`,
`extract_decision_required_section`, and `replace_or_append_decision`.

## What's broken

`DECISION_REQUIRED_RE` is a flat regex with `re.MULTILINE`:

```python
DECISION_REQUIRED_RE = re.compile(
    r"^## Decision required[^\n]*\n(.*?)(?=^## |\Z)",
    re.MULTILINE | re.DOTALL,
)
```

The terminating lookahead `(?=^## |\Z)` matches *any* line that
begins with `## ` (level-2 ATX heading) regardless of surrounding
markdown structure. `re.MULTILINE` has no notion of fenced code
blocks, so a line that *looks like* a level-2 heading inside a
\`\`\`-fenced block — a shell comment such as `## install via brew`,
a literal `## Decision` shown as a markdown example, a makefile
target whose recipe contains `## ` — terminates the match.

Two downstream consumers corrupt the card:

1. **`extract_decision_required_section`** returns only the prefix
   of the deliberation up to (but not including) the misparsed line.
   `_cmd_decide` writes that truncated prefix to `log.md` as the
   archived deliberation, losing the rest.

2. **`replace_or_append_decision`** replaces only the matched span.
   Everything from the misparsed `## ` line onward — including the
   closing \`\`\` fence and any further `## Why it matters` /
   `## Considerations` sections — is left in place *after* the
   resolved `## Decision` block. The new body therefore carries a
   stray `## ` heading, an orphaned closing fence, and parts of the
   original deliberation stranded below the resolved decision. The
   markdown is no longer well-formed.

## Empirical evidence

`reproduce.py` synthesises a README body whose `## Decision required`
section contains a `bash` code fence with a `## install via brew`
comment, then runs both engine helpers:

```
=== ARCHIVED SECTION (what gets written to log.md) ===
'Choose between:\n\n```bash'

=== RESOLVED BODY (what goes to README.md) ===
## Decision

*Resolved 2026-05-30:* Pick brew

*Reasoning:* Simpler

## install via brew
brew install something
```

Both options have tradeoffs.

## Why it matters

Production deploys depend on this.

=== END ===
```

The archived section ends mid-fence at \`\`\`bash with the entire
substantive deliberation ("Both options have tradeoffs.") missing
from log.md. The rewritten README carries `## install via brew` as a
stray level-2 heading, an orphan closing fence, and the
`## Why it matters` section now reads as if it belonged to the
`## install via brew` "heading".

## Why it matters

Decision deliberations on this project routinely embed code
fragments — shell snippets, makefile recipes, alternate markdown
examples, sample card frontmatter — because the whole point of
`## Decision required` is to lay out concrete alternatives the
human is picking between. The reachability path is direct:

- a card author writes `## Decision required` with one or more
  fenced code blocks containing shell-comment lines (`## ` is the
  common comment shape in installation recipes), or a markdown
  example of card body shape, or a makefile target with `##`;
- a human runs `goc decide <title> --decision "..." --because "..."`;
- the engine silently truncates the archive and corrupts the README.

`log.md` is the journal axis the deck depends on for reconstructing
history (cf. closed-card relationship-edge invariants); silent
truncation falsifies that journal. The README corruption then
trips downstream readers — `goc show`, `triage`, future re-decision
attempts — into reasoning over malformed markdown.

This is the **fourth distinct sibling** of the regex-based
`## Decision required` parser family, joining:

- `goc-decide-corrupts-decision-text-via-regex-replacement-template`
  (closed) — `\1` / `\p` in user text crashed or mangled the
  substitution; fix shipped via `lambda _:` guard.
- `goc-decide-leaves-prior-decision-block-when-the-body-already-has-one`
  (open) — flat regex sees only `## Decision required`, not a
  prior `## Decision`.
- `goc-decide-omits-blank-line-before-following-section-heading`
  (closed) — the regex's neighbour-handling contract.

When the fourth instance lands, this is meta-fix territory: a flat
regex is not the right tool to parse a markdown section's body.
A small fence-tracking pre-pass, or a real markdown AST, should be
weighed against staying with regex + a fence-aware lookahead.

## Decision required

Pick the fence-handling approach:

1. **Tiny fence-aware scanner.** Replace the regex with a manual
   line-walk that toggles "inside fenced block" state on `^\`\`\``
   (with the same delimiter the opener used) and only treats `^## `
   as a section boundary when not inside a fence. Cheap to write,
   no new dependency, ~20 lines, regression-tested. Matches the
   project's existing minimalism (the frontmatter parser, the
   `_strip_goc_block` regex, etc. are all bespoke).
2. **Pull in a markdown parser** (e.g. `markdown-it-py`,
   `mistune`). Correct on every markdown edge — code fences,
   indented code, raw HTML, multi-line ATX headings — at the cost
   of a new runtime dependency.
3. **Stay with regex, narrow the lookahead.** Tighten
   `(?=^## )` to `(?=^## [A-Z])` (require an uppercase character
   after the space) so shell comments like `## install`,
   `## comment` no longer terminate. Cheaper than option 1 but
   leaks on `## Header`-style fenced examples and on legitimate
   lowercased section headings (the engine doesn't reject those).
4. **Mandate the rendering escape.** Forbid fenced `## ` lines in
   `## Decision required` and document the workaround (indented
   code blocks, or use a single `#` shell-comment style). Trades a
   product-surface bug for a card-authoring restriction.

Sibling fix consistency: the closed `corrupts-decision-text-via-regex-replacement-template`
card chose the cheap-and-local fix (`lambda _:`) rather than
rewriting the whole substitution. If we want fence awareness *and*
meta-fix coordination, the open sibling
`leaves-prior-decision-block-when-the-body-already-has-one` is a
natural co-fix candidate — both are flat-regex limitations.
