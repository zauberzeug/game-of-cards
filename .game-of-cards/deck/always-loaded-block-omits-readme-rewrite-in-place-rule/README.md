---
title: always-loaded-block-omits-readme-rewrite-in-place-rule
summary: "Agents repeatedly leave a card self-contradicting — appending a Correction section to README.md while leaving the now-refuted claim standing above it. The dashboard rewrite-in-place discipline exists only on load-on-demand surfaces (card-schema, advance-card, deck skills) plus a decide-path-only tooling catch (goc decide reminder + DECISION_CONTRADICTS_VERDICT validator). Free-form README correction edits load no skill and run no verb, so none of that is in context. Hoist a crisp rewrite-in-place block into the always-loaded AGENTS.md/CLAUDE.md GOC methodology block (goc/templates/AGENTS_GOC.md), the one surface guaranteed present."
status: done
stage: null
contribution: medium
created: "2026-06-20T05:20:18Z"
closed_at: "2026-06-21T04:45:52Z"
human_gate: none
advances: []
advanced_by: []
tags: [story, documentation, meta-fix]
definition_of_done: |
  - [x] PROCESS: `goc/templates/AGENTS_GOC.md` gains a bolded principle block ("The README is a dashboard, not a changelog.") in the house style of the existing blocks, placed immediately before "Closure is not frozenness." It states: the README shows only what is true now; when new evidence corrects/refutes/re-scopes a finding the README already asserts, **rewrite that section in place** rather than appending a Correction/Update/Latest-finding block below the now-false claim; reconcile the `summary:` frontmatter and any body banner in the same pass; record the *why* + the demoted claim in `log.md`. Cross-references `Skill(card-schema)` "What goes where" and notes that `goc decide` / `goc validate` enforce the rule only on the decide path.
  - [x] MECHANICAL: this repo's own `AGENTS.md` marker block (between `<!-- BEGIN GOC vX.Y.Z -->` and `<!-- END GOC -->`) is updated to match the edited template byte-for-byte, so the dogfood copy reflects the same guidance. Guard: `awk '/^<!-- BEGIN GOC v/{f=1;next} /^<!-- END GOC -->/{f=0} f' AGENTS.md | diff - goc/templates/AGENTS_GOC.md` prints nothing.
  - [x] PROCESS: the new block does NOT contradict the adjacent "Closure is not frozenness." block — it scopes the rewrite-in-place rule to living cards and points forward to the post-close amendment as the lone sanctioned append.
  - [x] PROCESS: `log.md` cross-links the two closed family predecessors ([clarify-readme-as-dashboard-and-log-md-as-history](../clarify-readme-as-dashboard-and-log-md-as-history/) and [goc-decide-leaves-stale-verdict-content-when-recording-a-rescope](../goc-decide-leaves-stale-verdict-content-when-recording-a-rescope/)) and records why the fix lands in the always-loaded block rather than another skill body.
  - [x] MECHANICAL: `uv run goc validate` passes and `uv run python -m unittest discover -s tests` stays green (no skill/marker-parity regression).
---

# always-loaded-block-omits-readme-rewrite-in-place-rule

## What's missing

Downstream agents keep landing the same self-contradiction and even
name it themselves: *"I added correction sections but left the original
refuted claims standing in the earlier sections, so the card now
contradicts itself."* The agent appends a `## Correction` / `## Update`
section to a card's `README.md`, but leaves the now-false claim
standing in the section above it, so the README asserts both the old
verdict and the new one. The stale top-framing is exactly what the next
reader (human or agent) reads first.

The discipline that prevents this already exists — but only on surfaces
an agent must *opt into*:

- `goc/templates/skills/card-schema/SKILL.md` "What goes where"
  (README "rewritten in place; outdated content is replaced, not
  amended below") and its explicit antipattern callout: *"A new
  'Latest finding (DATE)' block at the bottom of the README is an
  antipattern — it accumulates contradicting versions of the truth."*
- `goc/templates/skills/advance-card/SKILL.md` disproved flow
  ("Rewrite … body to document the resolved state").
- `goc/templates/skills/deck/SKILL.md` Layout block (the dashboard /
  journal framing, landed there by the closed card
  `clarify-readme-as-dashboard-and-log-md-as-history` precisely so the
  distinction "lands on the first read, not only inside card-schema").

All three are **load-on-demand skills**. Tooling enforcement exists too
— but only for one verb: the closed card
`goc-decide-leaves-stale-verdict-content-when-recording-a-rescope`
added a `goc decide` reminder and a `goc validate` advisory
(`DECISION_CONTRADICTS_VERDICT`). That card's own body states the
limit: *"This is the `goc decide`-specific manifestation of the general
'fix every occurrence when you demote a claim' discipline — but the
tool neither enforces nor reminds it"* in the general case.

## Why it matters

The self-contradiction failure happens during **free-form `README.md`
correction edits** — an agent realizes an earlier finding was wrong and
edits the card directly. That path loads **no skill** and runs **no
verb**, so none of the surfaces above are in context. The one surface
guaranteed to be loaded in every session is the `<!-- BEGIN GOC -->`
methodology block in `AGENTS.md` / `CLAUDE.md`, generated from
`goc/templates/AGENTS_GOC.md`. That block currently says nothing about
the README's edit discipline. The closest block, "Closure is not
frozenness.", covers the *post-close* append exception but never states
the *living-card* rewrite-in-place rule it is the exception to.

GoC explicitly targets AI-agent collaborators, and `summary:` + the
body's top framing are what an agent reads first; a card that
contradicts itself there drives wrong downstream actions (the rescope
card documents a near-miss `goc status … disproved` flip against a
freshly re-scoped mechanism).

## Fix

Add one bolded principle block to `goc/templates/AGENTS_GOC.md`, in the
register of the existing blocks, immediately before "Closure is not
frozenness." (the general rule sits right before its post-close
exception). Landed text (in `goc/templates/AGENTS_GOC.md`, mirrored
byte-for-byte into this repo's `AGENTS.md` marker block):

> **The README is a dashboard, not a changelog.** A card's `README.md`
> shows only what is true *now*; `log.md` is the append-only journal of
> how it got there. When new evidence corrects, refutes, or re-scopes a
> finding the README already asserts, **rewrite the section that stated
> it in place** — do not append a "Correction" / "Update" / "Latest
> finding" block below it and leave the now-false claim standing. A card
> that asserts both the old verdict and the new one contradicts itself,
> and the stale top-framing is exactly what the next agent reads first.
> In the same pass, reconcile the `summary:` frontmatter and any `> ⚠`
> verdict banner, and record the *why* plus the demoted claim in
> `log.md`. `goc decide` reminds you of this for re-scopes and `goc
> validate` flags `DECISION_CONTRADICTS_VERDICT`, but the discipline
> applies to every hand edit, not just the decide path — the lone
> exception is a closed card's post-close amendment (next). See
> `Skill(card-schema)` "What goes where" for the full contract.

Then mirror the same block into this repo's `AGENTS.md` marker block so
the dogfood copy matches (the marker block is byte-for-byte identical to
the template today; `_append_marker_block` would regenerate the same
content on the next `goc upgrade`).

Scope guard: this is a pure always-loaded-guidance edit. No engine code,
no new validator (the general-case tooling catch is deliberately out of
scope — the existing `goc decide` / `validate` enforcement is named as
partial coverage, not extended here).
