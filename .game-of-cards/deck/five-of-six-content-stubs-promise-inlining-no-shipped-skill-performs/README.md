---
title: five-of-six-content-stubs-promise-inlining-no-shipped-skill-performs
summary: "goc install scaffolds six user-owned content stubs under .game-of-cards/, and every one carries a header stating it is \"injected into goc-shipped skill bodies via `!`cat ...`` at documented insertion points\" — but only canonical-tags.md has an injection point in any shipped skill. The deck README catalogue compounds the drift: it marks four stubs \"(reserved for project use)\", contradicting their own headers, and claims tooling-conventions.md is inlined into the audit-deck skill Phase 2 brief when audit-deck only names the file in prose. A consumer who authors a model-tier mandate or a glossary into those files gets nothing delivered to the agent."
status: active
stage: null
contribution: medium
created: "2026-08-01T05:56:33Z"
closed_at: null
human_gate: none
advances:
  - doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them
advanced_by: []
tags: [bug, documentation, api-contract]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero — every stub whose header claims injection has one, and every catalogue row naming a skill is backed by a real `!`cat`` line.
  - [ ] MECHANICAL: `goc/templates/skills/audit-deck/SKILL.md` Phase 2 injects `.game-of-cards/tooling-conventions.md` at the point the catalogue documents, replacing the prose pointer.
  - [ ] MECHANICAL: the four reserved stubs (`domain-vocabulary.md`, `domain-examples.md`, `file-path-map.md`, `documentation-conventions.md`) carry a header that states they are reserved and names no injection point; `canonical-tags.md` and `tooling-conventions.md` keep the injected-stub header.
  - [ ] MECHANICAL: the dogfood copies under `.game-of-cards/` are updated to match the corrected templates (user-owned, not auto-synced).
  - [ ] TDD: a regression test derives the verdict from the tree — for every shipped `goc/templates/game_of_cards/*.md` stub, the header's injection claim and the README row's "Inlined into" cell must both agree with whether a shipped skill `!cat`-injects it. Fails before the fix, passes after.
  - [ ] TDD: `uv run goc validate` is clean and `uv run python -m unittest discover -s tests` is green.
worker: {who: "claude[bot]", where: main}
---

# Five of the six content stubs promise an inlining no shipped skill performs

## Summary

`goc install` scaffolds six user-owned content stubs under
`.game-of-cards/`. Each one's header comment tells the consumer it is
"injected into goc-shipped skill bodies via `!`cat
.game-of-cards/<name>.md`` at documented insertion points" and that
"if this file is empty, the skills proceed with their generic flow" —
i.e. authoring content into it changes agent behavior. For five of the
six, no shipped skill injects it, so authoring content into them
changes nothing.

## Location

- Stub headers (all six, identical boilerplate):
  `goc/templates/game_of_cards/{canonical-tags,domain-vocabulary,domain-examples,file-path-map,tooling-conventions,documentation-conventions}.md:1-7`
- Catalogue: `goc/templates/game_of_cards/README.md` § "Content stubs
  (root)" (byte-identical dogfood copy at `.game-of-cards/README.md`).
- The one skill that names a non-injected stub in prose instead:
  `goc/templates/skills/audit-deck/SKILL.md:133-134`.

## What's broken

Every stub ships this header (`domain-vocabulary.md`, verbatim; the
other five differ only in the filename):

```
<!-- .game-of-cards/domain-vocabulary.md
     Project-local content stub injected into goc-shipped skill bodies via
     `!\`cat .game-of-cards/domain-vocabulary.md\`` at documented insertion points.

     Author the content the skills should see. If this file is empty, the
     skills proceed with their generic flow. See the goc README for the
     hook-point catalogue. -->
```

The catalogue that header points at defines the mechanism precisely
(`goc/templates/game_of_cards/README.md:11-18`):

> Markdown files inlined verbatim into skill bodies at documented
> injection points. The skill loads them via:
> `` !`cat .game-of-cards/<filename>.md 2>/dev/null || true` ``

Grepping the shipped skill tree for that line finds seven injections —
the six workflow hooks plus `canonical-tags.md`. None of the other five
content stubs appears.

The catalogue then contradicts the headers it just authorized. Four
rows read:

```
| `domain-vocabulary.md` | (reserved for project use) | Glossary of project-specific terms |
| `domain-examples.md` | (reserved for project use) | Concrete example card bodies for project-specific bug classes |
| `documentation-conventions.md` | (reserved for project use) | Doc-style rules — STATUS.md vs SPEC.md split, per-doc consistency invariants |
| `file-path-map.md` | (reserved for project use) | Project filesystem map — where scripts/tests/docs live, what's gitignored |
```

So for those four the catalogue is honest and the stub header is the
lie. The fifth row is the reverse — the catalogue makes a claim the
skill does not honor:

```
| `tooling-conventions.md` | `audit-deck` skill (Phase 2 brief, model-tier guidance) | Project tooling rules (e.g., `uv run` discipline, `model: "opus"` mandate, parallelization rules) |
```

`audit-deck` Phase 2 does not inject it. It names it in prose
(`goc/templates/skills/audit-deck/SKILL.md:133-134`):

```
For model-tier guidance (e.g. mandating `model: "opus"`), see
`.game-of-cards/tooling-conventions.md`.
```

A prose pointer and an `!`cat`` injection are not the same delivery.
The injection is unconditional — the host evaluates it while assembling
the skill body, so the content is in the agent's context before the
first decision. A prose pointer is a suggestion the agent may or may
not act on, and an `audit-deck` orchestrator that fans hunters out
never forwards a file it did not read.

## Empirical evidence

`uv run python .game-of-cards/deck/five-of-six-content-stubs-promise-inlining-no-shipped-skill-performs/reproduce.py`:

```
shipped content stubs:            6
`!cat` injections in skill tree:  7

stub                             header claims  injected  catalogue 'Inlined into'
----------------------------------------------------------------------------------
canonical-tags.md                True           True      `card-schema` skill (end of predicate table) AND parsed by `goc validate` to extend the canonical-tag enum
documentation-conventions.md     True           False     (reserved for project use)
domain-examples.md               True           False     (reserved for project use)
domain-vocabulary.md             True           False     (reserved for project use)
file-path-map.md                 True           False     (reserved for project use)
tooling-conventions.md           True           False     `audit-deck` skill (Phase 2 brief, model-tier guidance)

[FAIL] stub headers promising an injection that does not exist: 5/6
          documentation-conventions.md
          domain-examples.md
          domain-vocabulary.md
          file-path-map.md
          tooling-conventions.md
[FAIL] catalogue rows naming a skill that does not inject: 1
          tooling-conventions.md -> '`audit-deck` skill (Phase 2 brief, model-tier guidance)'

audit-deck/SKILL.md:134: `.game-of-cards/tooling-conventions.md`.
          ^ a prose pointer, not the `!`cat`` injection the catalogue documents
```

Confirmed against a real consumer install rather than the templates
alone — `goc install --agents claude --local-skills` into an empty git
repo scaffolds all six stubs into `.game-of-cards/`, and grepping the
installed `.claude/skills/` tree yields the same seven injections
(`canonical-tags.md` plus the six hooks). The same seven hold across
all five skill copies in this repo (`goc/templates/skills`,
`.claude/skills`, `.codex/skills`, `claude-plugin/skills`,
`codex-plugin/skills`).

## Why it matters

The stubs are the documented extension surface for making
domain-agnostic skills project-aware, and they are the *only* surface:
skill bodies are goc-owned and regenerated on upgrade, so a consumer
cannot add their own injection line. When five of the six are inert, a
consumer who follows the header's instruction — "Author the content the
skills should see" — writes a glossary or a filesystem map that no
agent ever reads, and gets no signal that it went nowhere.

`tooling-conventions.md` carries the concrete cost. The catalogue
advertises it for the `model: "opus"` mandate and `uv run` discipline,
and `audit-deck` Phase 2 is exactly where a hunter roster needs both.
In this repo the file is an unauthored stub, so nothing is lost today —
but a consumer who authors a model-tier mandate into it is relying on a
delivery mechanism that the skill does not implement.

Thirteenth instance of
[doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them](../doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them/),
and the mirror image of the one guard that already exists here:
[deck-readme-hook-catalogue-omits-refine-deck-hook](../deck-readme-hook-catalogue-omits-refine-deck-hook/)
added `tests/test_readme_hook_catalogue_parity.py`, which pins the
*hook* table against `goc/templates/game_of_cards/hooks/*.md`. That
guard proves only that a shipped hook has a table row; nothing checks
the content-stub table, and nothing checks that a catalogued injection
point exists in the skill it names. Both gaps are why this rotted
silently.

## Fix

Each half is settled by the same tie-break: the per-stub catalogue row
is the specific statement of intent, the stub header is boilerplate
copied across all six.

1. **`tooling-conventions.md` — the code drifted.** The catalogue names
   the injection point, so add it at
   `goc/templates/skills/audit-deck/SKILL.md:133-134`, replacing the
   prose pointer:

   ```
   Project tooling rules and model-tier guidance (e.g. mandating
   `model: "opus"`), as authored by the consuming repo:

   !`cat .game-of-cards/tooling-conventions.md 2>/dev/null || true`
   ```

   This matches how `canonical-tags.md` and the six hooks already
   behave, including the empty-stub case: an unauthored stub inlines
   its own header comment, exactly as `hooks/audit-deck.md` does today.

2. **The four reserved stubs — the header drifted.** Give them a header
   that says what the catalogue says, and names no injection point:

   ```
   <!-- .game-of-cards/domain-vocabulary.md
        Reserved for project use. No goc-shipped skill inlines this file
        today, so content authored here does not reach an agent on its own.
        See `.game-of-cards/README.md` § "Content stubs" for the stubs that
        do have an injection point. -->
   ```

   These are user-owned files: changing the template changes what a
   fresh `goc install` scaffolds, while `goc upgrade` preserves any
   existing copy, so no authored content is at risk.

3. **Guard it from the tree.** Add
   `tests/test_readme_content_stub_catalogue_parity.py` (sibling to the
   hook-table guard) asserting, for every
   `goc/templates/game_of_cards/*.md` stub, that the header's injection
   claim and the README row's "Inlined into" cell both agree with
   whether any shipped skill `!cat`-injects it — in both the template
   and the dogfood copy. That is the derive-from-tree shape the
   doc-accuracy root card asks for, and it closes the direction the
   hook-table guard leaves open.
