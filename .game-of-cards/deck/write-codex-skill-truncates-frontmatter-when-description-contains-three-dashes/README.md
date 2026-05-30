---
title: write-codex-skill-truncates-frontmatter-when-description-contains-three-dashes
summary: "`_write_codex_skill` splits the source SKILL.md on the literal substring `---` with maxsplit=2 to extract frontmatter, but the splitter does not look for line-anchored `---` delimiters. A skill whose `description` value contains the substring `---` (e.g., the prose `Use --- as a section delimiter`) gets its frontmatter truncated at the in-prose `---`, the rest of the description leaks into the rendered Codex body, and the resulting `.codex/skills/<name>/SKILL.md` is corrupted with a dangling third `---` delimiter and a wrong description field."
status: open
stage: null
contribution: low
created: "2026-05-30T04:05:06Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract, infra, unverified]
definition_of_done: |
  - [ ] PROCESS: human picks one of the fix options listed in `## Decision required` (line-anchored split / proper frontmatter parser / refuse-on-detection); recorded inline.
  - [ ] TDD: `reproduce.py` exits zero — a SKILL.md whose `description` contains `---` ports to Codex with the description preserved verbatim and the body intact.
  - [ ] TDD: a regression test in `tests/` covers the same shape end-to-end through `_sync_skill_tree` (the entry point that actually fires during `goc install --agents codex`).
  - [ ] TDD: existing skill-port tests still pass (no regression in the common no-`---` case).
  - [ ] MECHANICAL: `goc validate` clean; plugin mirrors re-synced if `install.py` changed.
---

# `_write_codex_skill` truncates frontmatter when `description` contains `---`

UNVERIFIED only in the sense that no currently-shipped GoC skill has
`---` inside a frontmatter value, so the bug has zero CURRENT impact on
the GoC dogfood install. It is reachable as soon as any skill author
(GoC contributors, or — once `goc install` is documented as supporting
project-local skill customization — downstream users) writes a
`description:` that contains the substring `---`. The bug is exercised
by `reproduce.py` in this directory; promote the card to verified once
a downstream skill carries the trigger pattern.

## Location

`goc/install.py:817-842` — `_write_codex_skill`:

```python
def _write_codex_skill(src: Path, dst: Path, *, skill_name: str) -> None:
    """Write a Codex-compatible SKILL.md copy from the shared template."""

    text = src.read_text()
    if not text.startswith("---\n"):
        shutil.copy2(src, dst)
        return

    try:
        _, frontmatter, body = text.split("---", 2)
    except ValueError:
        shutil.copy2(src, dst)
        return

    name = _frontmatter_value(frontmatter, "name") or skill_name
    description = _frontmatter_value(frontmatter, "description")
    codex_frontmatter = "\n".join(
        (
            "---",
            f"name: {name}",
            f"description: {json.dumps(description, ensure_ascii=False)}",
            "---",
        )
    )
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(codex_frontmatter + body)
```

## What's broken

Line 826 — `text.split("---", 2)` — splits on the bare substring `---`,
NOT on line-anchored `---` delimiters. With maxsplit=2 it produces three
parts: everything before the first `---`, the slice between the first
and second `---`, and everything after the second `---`. The function
assumes the first two occurrences are always the frontmatter opener
and the frontmatter closer. That assumption fails the moment any
`---` appears INSIDE a frontmatter value.

The simplest trigger is a quoted description that mentions `---`:

```markdown
---
name: example-skill
description: "Use --- as a section delimiter in your prose"
---

# Body
```

`text.split("---", 2)` returns:

```python
[
    "",
    '\nname: example-skill\ndescription: "Use ',  # ← truncated frontmatter
    ' as a section delimiter in your prose"\n---\nbody\n',  # ← polluted body
]
```

`_frontmatter_value(frontmatter, "description")` parses the truncated
frontmatter line `description: "Use ` and (because the helper strips
matched balanced quotes) returns the string `"Use` — a corrupted value.
The Codex frontmatter emitted is:

```markdown
---
name: example-skill
description: "\"Use"
---
```

The rendered body then starts with the leaked tail:

```markdown
 as a section delimiter in your prose"
---

# Body

Body content here.
```

Three observable failures from one input:

1. **Description field is silently corrupted** to `"Use` — neither
   the original prose nor an empty fallback. Codex skill rendering on
   the consumer side will display this nonsense as the skill's
   description.
2. **Body content is contaminated** with the leaked tail of the
   original description (`" as a section delimiter in your prose"`).
3. **The output file has THREE `---` lines** (codex_frontmatter open,
   codex_frontmatter close, and the leftover original closer dragged
   into the body). Codex's frontmatter parser stops at the second `---`,
   so the third becomes a literal markdown horizontal-rule line —
   visually wrong, but silent.

## Empirical evidence

`uv run python .game-of-cards/deck/write-codex-skill-truncates-frontmatter-when-description-contains-three-dashes/reproduce.py`:

```
FAIL — `_write_codex_skill` corrupted the skill:
  expected description: 'Use --- as a section delimiter in your prose'
  observed description: '"Use'
  full ported output:
    ---
    name: example-skill
    description: "\"Use"
    --- as a section delimiter in your prose"
    ---

    # Body

    Body content here.
```

## Why it matters

The reachability path is `goc install --agents codex` (or any install
that resolves `skill_for_agent(..., "codex")`), specifically
`_sync_skill_tree` (`goc/install.py:881`) which routes
`SKILL.md` files through `_write_codex_skill` when
`codex_frontmatter=True`. Every Codex consumer's `.codex/skills/<name>/`
tree is rebuilt from the GoC templates on every `goc install` /
`goc upgrade`, so a single template edit that introduces the trigger
pattern silently corrupts the next install cycle for every Codex user.

The trigger pattern is plausibly user-facing:

- **GoC's own skill authoring style.** A `description:` is a one-liner
  natural-language sentence; English prose routinely uses `---` as an
  em-dash typography substitute, especially in technical writing.
  Several current GoC skill descriptions use the em-dash character `—`
  precisely because someone enforced that style — the moment that
  policy slips, or a contributor types three hyphens out of habit, the
  Codex port silently breaks.
- **Downstream-extension scenarios.** Anyone who customizes GoC skills
  locally and ships them to a Codex consumer has no way to know the
  porter is going to mangle their description.

Also covered: the body-injection failure mode would survive any
description-only validator added at the install boundary — the leaked
description tail lives in body bytes, not frontmatter bytes. Whatever
fix lands must restore the body verbatim too, not just the description
field.

## Decision required

Three credible fix paths, ordered by invasiveness:

1. **Line-anchored split.** Replace the bare `text.split("---", 2)`
   with a regex that matches `^---$` (or equivalently locates two
   line-start `---` delimiters). Cheap; matches the same line-anchored
   contract that `goc.engine.FRONTMATTER_RE` already enforces for card
   READMEs. Caveat: still fragile if a quoted multi-line description
   ever contains a line that is literally `---` — but that requires a
   block-scalar value (`|`/`>`) which the helper's `_frontmatter_value`
   does not support today anyway, so the fragility is bounded.
2. **Reuse the proper frontmatter parser.** Call
   `goc.engine.parse_frontmatter` (or import-and-share the same
   `FRONTMATTER_RE`) instead of hand-rolling a split. Symmetric with
   `goc.engine` — there is one frontmatter parse, used everywhere.
   Caveat: introduces an engine→install import edge that the current
   layering deliberately avoids (install imports nothing from engine).
3. **Refuse the trigger pattern.** When the source SKILL.md has any
   `---` between its opening and closing frontmatter delimiters, fail
   loudly during `goc install` / `goc upgrade` with a message
   pointing at the offending file. Cheapest fix, but pushes the
   handling burden to skill authors and gives no path for a
   description that legitimately wants `---`.

Recommendation: **option 1**. Symmetric with `engine.FRONTMATTER_RE`'s
line-anchored shape, no new cross-module import, and the bounded
caveat does not bite any current or imagined usage. The DoD's TDD
items are the same shape regardless of which option lands — the
reproducer exits zero either way.
