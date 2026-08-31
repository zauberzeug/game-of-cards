---
title: openclaw-porter-arguments-substitution-breaks-single-quoted-python-literals
summary: "The OpenClaw skill porter rewrites `$ARGUMENTS` to the literal phrase `the user's argument`. In `retrospective/SKILL.md` that token sits inside a single-quoted Python string, so the ported snippet becomes `n = int('the user's argument'.strip() or '10')` — an unterminated-string-literal SyntaxError. An OpenClaw agent following Step 1 gets no closure history at all, and the failure is silent because the snippet ends in `2>/dev/null || true`."
status: open
stage: null
contribution: medium
created: "2026-07-26T12:52:39Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [ ] DECISION: fix path picked from `## Decision required` below
  - [ ] TDD: `reproduce.py` exits zero — the port breaks no snippet that compiled in its source template
  - [ ] TDD: a regression test compiles every ported `python3 -c "..."` snippet, so a future substitution landing in a quoted context turns the build red instead of shipping a SyntaxError
  - [ ] MECHANICAL: `openclaw-plugin/skills/retrospective/SKILL.md` re-ported and its Step 1 snippet parses
  - [ ] MECHANICAL: `python3 scripts/port_skills_to_openclaw.py --check` green (the porter is idempotent, so a re-port must leave no drift)
  - [ ] PROCESS: `uv run python -m unittest discover -s tests` green
---

# openclaw-porter-arguments-substitution-breaks-single-quoted-python-literals

## Location

- `scripts/port_skills_to_openclaw.py:72` — the substitution
- `goc/templates/skills/retrospective/SKILL.md:53` — the source snippet
- `openclaw-plugin/skills/retrospective/SKILL.md:49` — the broken output

## What's broken

The porter's substitution table ends with a plain textual replacement:

```python
    # Argument-hint / $ARGUMENTS — Claude-specific slash-command syntax.
    (re.compile(r"^argument-hint:.*$\n", re.MULTILINE), ""),
    (re.compile(r"User argument: \$ARGUMENTS — "), "Optional argument — "),
    (re.compile(r"\$ARGUMENTS"), "the user's argument"),
```

The replacement text contains an apostrophe, and the rule is
context-blind — it rewrites `$ARGUMENTS` wherever it appears, including
inside code. The `retrospective` skill interpolates the placeholder
into a single-quoted Python literal:

```python
n = int('$ARGUMENTS'.strip() or '10')
```

which ports to:

```python
n = int('the user's argument'.strip() or '10')
```

The apostrophe closes the literal early, so the whole `python3 -c`
snippet is an unterminated string. The snippet's own error suppression
hides it: the pipeline ends in `2>/dev/null || true`, so an OpenClaw
agent running Step 1 sees an empty result and a zero exit status, not a
traceback. The retrospective silently reports no closures.

Two other ported sites take the same substitution in prose, where the
apostrophe is harmless (`scan-deck/SKILL.md:22`,
`create-card/SKILL.md:34` — both `User argument: the user's argument`).
Only the `retrospective` site lands inside quoting.

## Empirical evidence

`uv run python .game-of-cards/deck/openclaw-porter-arguments-substitution-breaks-single-quoted-python-literals/reproduce.py`
compiles each source snippet and its ported counterpart and reports
only what the *port* breaks:

```
porter substitution: (re.compile(r"\$ARGUMENTS"), "the user's argument"),

[PORT BREAKS IT] goc/templates/skills/retrospective/SKILL.md:53
                 → openclaw-plugin/skills/retrospective/SKILL.md:50
                 source snippet compiles; ported snippet: SyntaxError: unterminated string literal (detected at line 6)
                 offending line: n = int('the user's argument'.strip() or '10')

snippet pairs compared: 4   broken by the port: 1

[FAIL] the port turns 1 compiling snippet(s) into a SyntaxError. An OpenClaw agent following the step gets nothing back — silently, because the snippet ends in `2>/dev/null || true`.
```

The differential framing matters: a naive "compile every ported
snippet" probe also flags the two `standup` snippets, whose `\"` are
shell escapes inside a double-quoted `python3 -c` word and are present
in the source templates too. Those are not porter damage. Unescaping
`\"` before parsing and comparing against the source removes them,
leaving exactly one regression.

## Why it matters

The porter is the only path by which skill templates reach OpenClaw
consumers, and `--check` (enforced from `tests/test_plugin_mirror_parity.py`)
verifies only that the committed port *matches a fresh port* — not that
the port is valid. A deterministic, byte-stable, wrong output passes
every existing guard. Any future substitution whose replacement text
carries a quote, backslash, or brace has the same failure mode against
any quoted context, so the guard gap is the general problem and this
snippet is the instance that surfaced it.

Same shape as the closed
[openclaw-porter-fetch-hint-lands-outside-quoted-description-breaking-frontmatter-yaml](../openclaw-porter-fetch-hint-lands-outside-quoted-description-breaking-frontmatter-yaml/)
— a porter rewrite that is correct as text and invalid in its
destination's syntax. Sibling in the substitution-quality family:
[openclaw-skill-porter-claude-substitutions-emit-doubled-articles](../openclaw-skill-porter-claude-substitutions-emit-doubled-articles/).

Surfaced while closing
[retrospective-status-done-queries-hide-disproved-and-superseded-closures](../retrospective-status-done-queries-hide-disproved-and-superseded-closures/),
whose re-port put the broken line in the diff. That card deliberately
left this alone: it lives in the porter, not the skill body.

## Decision required

The defect is confirmed; the fix path is a genuine pick, because the
substitution is shared by three call sites with different needs.

**Option A — drop the apostrophe from the replacement.** Change
`"the user's argument"` to `"the user argument"` (or `"the caller's
argument"` → still apostrophised, so: `"the supplied argument"`). One
line in `scripts/port_skills_to_openclaw.py`, fixes every quoted
context at once, no template churn. Cost: the two prose sites read
very slightly stiffer, and the class of bug survives — the next
replacement string with a quote reintroduces it.

**Option B — make the substitution context-aware.** Skip replacement
inside fenced code blocks, or emit a quote-safe form there (e.g.
substitute `$ARGUMENTS` in code with a bare `10`/`N` placeholder while
prose keeps the phrase). Cost: the porter grows a fence-tracking pass,
which is the `dod-fence-mask-reimplements-commonmark-fences-and-keeps-drifting`
hazard in a new place.

**Option C — make the source template quote-safe.** Rewrite
`retrospective/SKILL.md`'s snippet so the placeholder is not inside a
Python literal — e.g. pass N through an environment variable
(`N="$ARGUMENTS" python3 -c "... os.environ.get('N') ..."`). Cost:
fixes only this site; the porter stays able to emit invalid output, and
the Claude-side template gets slightly more indirect for a
Claude-side non-problem.

Whichever is picked, the DoD keeps the compile-every-ported-snippet
regression test — that guard is what makes the failure mode
non-recurring, and it is orthogonal to the choice.
