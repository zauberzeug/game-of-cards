---
title: support-custom-frontmatter-fields-with-enum-and-required-when-rules
summary: |-
  Sibling to `support-custom-card-workflows-and-statuses`. That card
  scopes per-repo extension to existing-enum widening (more `status` /
  `stage` values). This card scopes the orthogonal axis: per-repo
  *validation logic* — letting consuming projects enforce arbitrary
  checks (custom enum membership for new frontmatter fields,
  required-when predicates, cross-field invariants, body-shape
  assertions) without forking goc. Preferred mechanism: a validation
  extension hook (`.game-of-cards/validators/*.py`) that `goc validate`
  imports and runs alongside built-in checks. This is strictly more
  general than a schema-field extension file — projects can build
  enum/required-when rules on top of the hook, plus anything else
  their domain needs (DOI-cite checks, granularity-match assertions,
  worker-allowlist enforcement, etc.). Motivating real consumer:
  phasor-agents wants a `granularity:` field with enum
  `[per-synapse | per-spine | per-assembly | per-region | per-network |
  mixed]`, required when `contribution: high` AND tags include
  `framework | plasticity | axiom`, after two granularity-drift bugs
  in 48 hours that their `/mindset` audit didn't catch.
status: open
stage: null
contribution: high
created: "2026-05-15T11:39:08Z"
closed_at: null
human_gate: session
advances:
  - support-custom-card-workflows-and-statuses
advanced_by: []
tags: [story, infra, api-contract]
worker: Rodja Trappe
definition_of_done: |
  - [ ] Design: hook discovery and load mechanism documented —
    where the hook lives (`.game-of-cards/validators/*.py` or
    similar), how `goc validate` discovers and imports it, what the
    callback signature is (e.g.,
    `validate(card: Card, schema: Schema) -> list[str]`), and how
    errors surface in `goc validate` output (line-prefixed per card,
    same as built-in errors)
  - [ ] Design: failure semantics — does a hook exception fail
    `goc validate` outright, or get wrapped as an error against the
    offending card? Does an empty validators directory differ from a
    missing one?
  - [ ] Design: trust boundary — `goc validate` runs in CI; importing
    arbitrary repo Python is already implicit (consumers run their own
    `pre-commit`), but document the boundary explicitly so a future
    `goc validate` invocation outside the consuming repo (e.g., from a
    sandboxed reviewer) knows whether to load hooks
  - [ ] Implementation: `goc/engine.py` validator loop loads
    `.game-of-cards/validators/*.py` modules, calls their entry
    function for each card, merges returned errors into the existing
    error list before exit-code computation
  - [ ] Implementation: opaque pass-through for unknown frontmatter
    keys (already de facto today — the validator only enforces
    `required_fields`); document this as the contract so hooks can
    rely on consumers declaring fields like `granularity:` without
    goc rejecting them
  - [ ] Reference example shipped under
    `goc/templates/game_of_cards/validators/example.py.disabled` (or
    similar) — a working `granularity:` enum + required-when checker
    consumers can copy and adapt; the `.disabled` suffix keeps it
    inert until renamed
  - [ ] Documentation: README section + AGENTS.md / CLAUDE.md guidance
    on the new extension surface, sibling to the `canonical-tags.md`
    and `hooks/<name>.md` extension docs
  - [ ] Tests cover: hook loaded and run, hook errors surfaced, hook
    exception caught and reported, no-validators-directory is a no-op,
    multiple validators compose
  - [ ] `uv run goc validate` passes on this repo's deck (no
    validators yet — should be unchanged behaviour)
  - [ ] Decision recorded on whether `support-custom-card-workflows-and-statuses`
    stays orthogonal (enum widening of *built-in* fields) or gets
    absorbed into the hook mechanism (built-in enum checks become
    just another validator implementation goc ships)
---

# support-custom-frontmatter-fields-with-enum-and-required-when-rules

## Why this exists

`support-custom-card-workflows-and-statuses` covers one extension axis:
let consuming projects add more values to existing enums (`status`,
`stage`). That keeps `goc/schema.yaml` as the source of truth for
*what fields exist* but lets the *vocabulary* per field grow.

There is a second, orthogonal axis the existing card does **not**
cover: consuming projects need to add **new frontmatter fields** with
their own enums, and apply **required-when predicates** that depend
on other field values. Today that's structurally impossible — the
schema is read straight from `goc/schema.yaml` with no per-repo merge
beyond `canonical_tags`, and unknown frontmatter keys are silently
tolerated by the validator (`engine.py:758` checks
`required_fields` only).

## The motivating real consumer

Phasor-agents (a separate computational-neuroscience project that
uses goc) just shipped two granularity-drift bugs in 48 hours
(May 13–15, 2026). Both cards passed their `/mindset` audit gate
because the audit asked "is the bio anchor real?" not "is the bio
anchor at the same granularity as the parameter?". The
post-mortem card
(`mindset-audit-checks-granularity-of-bio-anchor` in their deck)
proposes a two-tier fix:

1. Schema-level: add a `granularity:` field with enum
   `[per-synapse | per-spine | per-assembly | per-region |
   per-network | mixed]`, required when `contribution: high` AND
   `tags ∩ {framework, plasticity, axiom} ≠ ∅`.
2. Audit-level: `/mindset` SKILL.md grows an explicit
   granularity-check section.

Tier 2 is a project-local skill edit — they can do that today.
Tier 1 has nowhere clean to land. Adding `granularity:` to their
cards works (validator silently tolerates unknown keys), but with
no enum enforcement, no required-when rule, no surfacing in
`goc status` or `goc --board`. That's "vendored on top of goc," not
"extending goc."

## The proposed mechanism: validation extension hook

Rather than a narrow schema-field extension file, expose a **general
validation hook**. Consuming repos drop Python files under
`.game-of-cards/validators/*.py`; `goc validate` imports each and
invokes a documented callback for every card; returned error
strings are merged into the existing error list.

Sketch (illustrative, not a contract):

```python
# .game-of-cards/validators/granularity.py
GRANULARITIES = {"per-synapse", "per-spine", "per-assembly",
                 "per-region", "per-network", "mixed"}
REQUIRED_TAGS = {"framework", "plasticity", "axiom"}

def validate(card, schema):
    errs = []
    g = card.frontmatter.get("granularity")
    tags = set(card.frontmatter.get("tags") or [])
    contrib = card.frontmatter.get("contribution")
    requires_g = (contrib == "high" and tags & REQUIRED_TAGS)
    if requires_g and not g:
        errs.append(f"{card.title}: granularity required when "
                    f"contribution=high and tags include "
                    f"{sorted(REQUIRED_TAGS & tags)}")
    if g and g not in GRANULARITIES:
        errs.append(f"{card.title}: granularity '{g}' not in "
                    f"{sorted(GRANULARITIES)}")
    return errs
```

This is **strictly more general** than a schema-field extension file:

- A consumer wanting just enum + required-when (the phasor-agents
  case) writes ~15 lines like the sketch above
- A consumer wanting a DOI-format check on a `cite:` field also fits
- A consumer wanting "no two `worker:` claims on same `where:`
  branch" cross-card invariant also fits
- A consumer wanting to ban specific words in card bodies also fits

The hook is a single extension surface that absorbs the long tail of
domain-specific validation. Hackability is the whole point.

## Why a hook beats a declarative schema-extension file

A declarative file (the obvious alternative) would look like:

```yaml
# .game-of-cards/extra-fields.yaml
fields:
  granularity:
    enum: [per-synapse, per-spine, per-assembly, per-region,
           per-network, mixed]
    required_when:
      contribution: high
      tags_any_of: [framework, plasticity, axiom]
```

That covers the phasor-agents case but immediately hits the
"declarative validation always grows a Turing tarpit" problem. The
moment a consumer wants something not pre-modeled (cross-field
constraints, regex patterns, external lookups, custom error
messages), they're stuck. The hook mechanism is YAGNI-positive: ship
the small composable thing, let consumers build the declarative
sugar on top if they want it.

## Relationship to the sibling card

`support-custom-card-workflows-and-statuses` and this card are
**orthogonal**, not duplicates:

| Axis | Sibling card | This card |
|---|---|---|
| Extends *which* fields? | Existing built-ins (`status`, `stage`) | New project-defined fields |
| Extends *how*? | Add values to a known enum | Add arbitrary validation logic |
| Affects pickability / board / DoD enforcement? | Yes — must declare semantics | No — opaque to renderers |
| Required for autonomous safety? | Yes — wrong status semantics break loop | No — validation is advisory at validate-time |

One viable evolution (DoD #9): once the hook lands, the built-in
enum checks for `status_values`, `stage_values`, etc. could be
re-expressed as validators goc ships by default. That collapses the
two cards into one mechanism — but only if the sibling card's
session decisions land first (because terminal-state and
pickability semantics need to be locked before the implementation
shape settles).

## Open session questions

1. Hook discovery — single conventional path
   (`.game-of-cards/validators/*.py`), or configurable in
   `.game-of-cards/config.yaml`?
2. Callback signature — `validate(card, schema) -> list[str]`, or
   a richer `Verdict` object that supports warnings vs errors vs
   info, plus structured location pointers?
3. Hook exceptions — wrap-as-error-on-card, or fail-validate-loudly?
   The first is friendlier; the second prevents silent skips when a
   hook is buggy.
4. Cross-card validators — should the hook also receive the full
   card list (for invariants like "no duplicate `granularity:` per
   tag-cluster"), or only one card at a time? Cross-card adds power
   but complicates the loop.
5. Trust boundary — `goc validate` already runs in consumer CI, so
   importing repo Python is implicit. But what if a tool (say, a
   future `goc validate --remote` for cross-repo dashboards) wants
   to validate without executing repo code? Need an opt-out flag.
6. Plugin-payload installs — when goc is installed via the Claude
   Code plugin (no `pip install` on host), does the validator-load
   path still work? It should — validators live in the *consuming*
   repo, not the plugin payload — but worth confirming
   `_is_plugin_context` doesn't inadvertently disable the hook.

## What this card is NOT

- **Not a fork of `support-custom-card-workflows-and-statuses`.**
  That card stays as-is, scoped to enum widening of built-in
  pickability-affecting fields. This card is the orthogonal axis.
- **Not a schema rewrite.** `schema.yaml` stays the source of truth
  for built-in fields. The hook is additive — built-in validation
  runs first, hooks run after, errors compose.
- **Not a renderer extension.** `goc status`, `goc --board`, value
  sort, etc. don't learn the new fields. Opaque pass-through is
  fine for v1; if a project wants their custom field on the board,
  that's a follow-on card.
- **Not a generalisation of `canonical-tags.md`.** That hook is
  declarative-only (a list of strings); this hook is procedural.
  They coexist — both are valid extension surfaces with different
  power-vs-simplicity tradeoffs.

## Cross-references

### Sibling and predecessor

- [`support-custom-card-workflows-and-statuses`](../support-custom-card-workflows-and-statuses/)
  — sibling, scopes enum widening of built-in fields. Open,
  human_gate: session, parked since 2026-05-04.
- [`refine-deck-skill-missing-consuming-repo-hook-override`](../refine-deck-skill-missing-consuming-repo-hook-override/)
  — closed 2026-05-14; established the pattern that every
  goc-shipped surface needs a per-repo override hook. This card
  applies the same principle to the validator.

### External motivating consumer

- `mindset-audit-checks-granularity-of-bio-anchor` (in
  phasor-agents' deck, not this repo) — the post-mortem card that
  surfaced the gap. Closing this card unblocks the Tier-1 portion
  of theirs (schema-level granularity declaration becomes
  enforceable rather than vendored).
