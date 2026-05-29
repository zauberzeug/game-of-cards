---
title: bundled-closure-skips-configured-attestation-checks
summary: "`goc done --bundle` writes a `## Closure verification (TIMESTAMP) — bundled` block but never runs the layer-2 / layer-3 checks configured in `.game-of-cards/config.yaml`. A bundle can close a card whose `advanced_by` points at a still-open prereq — the same closure that `goc attest` (the documented two-step partner) would refuse. The bundle's hard-coded `DoD enforcement: PASS — per-card unchecked-box count was 0 for every member` is the entire attestation; layer-2 and layer-3 are silently skipped."
status: open
stage: null
contribution: medium
created: "2026-05-29T11:45:02Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [ ] PROCESS: decision recorded in `## Decision required` (which of the three paths below the bundle takes).
  - [ ] TDD: `reproduce.py` exits zero after the fix (defect no longer fires under the chosen path).
  - [ ] MECHANICAL: implementation matches the recorded decision — either bundle runs the configured layer-2/layer-3 checks before flipping status, or it refuses to close cards with non-trivial attestation, or the skill docs are amended to say the bundle skips attestation by design.
  - [ ] MECHANICAL: `Skill(finish-card)` Step 5 + the `--bundle` paragraph in `goc/templates/skills/finish-card/SKILL.md` reflect the chosen behavior (and the plugin mirrors are regenerated).
  - [ ] TDD: `tests/` covers the chosen behavior (bundle attestation runs / bundle refuses / docs match).
---

# `goc done --bundle` records a Closure-verification block without running the configured checks

## Location

- `goc/engine.py:3261-3269` — `_format_bundle_attestation_block` (the
  hard-coded "PASS" block).
- `goc/engine.py:3281-3345` — `_cmd_done_bundle` (writes the block,
  flips status, never calls `_run_derived_check` /
  `_run_automated_check`).
- `goc/templates/skills/finish-card/SKILL.md:228-242` — the
  `--bundle` paragraph that documents the current behavior.

## What's broken

`goc attest <title>` reads `.game-of-cards/config.yaml`, runs each
layer-2 + layer-3 check, and writes a result-based Closure
verification block (`goc/engine.py:3829-3899`). The non-bundle
closure flow is documented as two steps: `goc attest` (records
attestation) → `goc done` (flips status).

`goc done --bundle` is documented in `finish-card`'s Step 6 as the
*single-step equivalent* of that two-step flow:

> `--bundle` enforces the unchecked-DoD refusal on every member
> before mutating disk (any failure aborts the bundle), then writes
> one shared `## Closure verification (TIMESTAMP) — bundled` block
> plus a `## TIMESTAMP — Closure (bundled)` entry with
> `Bundled with:` cross-references into every member's `log.md`,
> and flips each card to `done` with the same `closed_at`. **Use
> this in place of running `goc attest` + `goc done` once per card
> when the closures genuinely share an attestation.**
> — `goc/templates/skills/finish-card/SKILL.md:234-242`

The implementation does NOT run any of the configured checks. The
attestation block is literally the following hard-coded f-string —
no layer-2 section, no layer-3 section, no check results:

```python
def _format_bundle_attestation_block(timestamp: str, titles: list[str]) -> str:
    members = "\n".join(f"  - {t}" for t in titles)
    return (
        f"## Closure verification ({timestamp}) — bundled\n"
        f"\n"
        f"- Bundle members:\n{members}\n"
        f"- DoD enforcement: PASS — per-card unchecked-box count was 0 for every member.\n"
        f"- Closed via: `goc done --bundle`\n"
    )
```
— `goc/engine.py:3261-3269`

Compare the non-bundle equivalent, which loops through every
configured check, runs it, and records the per-check result:

```python
def _format_attestation_block(today: str, results: list[dict]) -> str:
    lines = [f"## Closure verification ({today})", ""]
    for layer_num, label in [(2, "Layer-2 (project DoD)"), (3, "Layer-3 (GoC DoD)")]:
        layer_results = [r for r in results if r["layer"] == layer_num]
        if not layer_results:
            continue
        ...
```
— `goc/engine.py:3813-3826`

## Empirical evidence

A minimal in-process reproducer (see `reproduce.py`) builds three
cards in a temp deck:

- `card-c-prereq` — `status: open`, no DoD ticked.
- `card-a-bundle` — `advanced_by: [card-c-prereq]`, DoD 1/1 ticked.
- `card-b-bundle` — no prereqs, DoD 1/1 ticked.

With a `.game-of-cards/config.yaml` that enables the three derived
checks (`advanced-by-closed`, `dod-100-percent`,
`log-md-closure-entry`) it produces:

```
=== goc attest card-a-bundle ===
exit: 2

Layer-3 (GoC) checks:
  [ ] advanced-by-closed — 1 not done: card-c-prereq — wait for them
      to close, or if an edge is false, retract it: `goc unadvance
      card-a-bundle --by <upstream>` (prefer over `--skip`)
  [x] dod-100-percent — 1/1 ticked
  [ ] log-md-closure-entry — no '## 2026-05-29 — Closure' section

ERROR: attestation has failures; finish-card will block closure.

=== goc done --bundle card-a-bundle card-b-bundle ===
exit: 0
card-a-bundle: open → done
card-b-bundle: open → done

Bundled close: 2 cards.

=== card-a-bundle/log.md after bundle close ===
## Closure verification (2026-05-29T11:44:18Z) — bundled

- Bundle members:
  - card-a-bundle
  - card-b-bundle
- DoD enforcement: PASS — per-card unchecked-box count was 0 for every member.
- Closed via: `goc done --bundle`
```

The bundle closes `card-a-bundle` cleanly even though
`advanced-by-closed` would have FAILed and `log-md-closure-entry`
would have FAILed under `goc attest`. The Closure verification
block records neither failure — there is no record that the checks
even existed.

## Why it matters

The Closure verification block is the **audit trail** the 6-month-old
reader uses to tell whether attestation actually ran. The non-bundle
block records `[ ] advanced-by-closed FAIL` / `[x] dod-100-percent`
/ etc. — a per-check verdict the reader can re-derive. The bundle
block records `DoD enforcement: PASS` and nothing else, so a
bundled card with a still-open prereq looks identical on disk to a
bundled card that genuinely had no upstream waits.

Reachability is direct: every call to `goc done --bundle` produces
the offending block. A bundle of two unrelated cards (the
documented use case — "one fix resolves multiple cards") is the
most common shape, and it's exactly the shape where attestation
divergence between members would matter most.

The bug is independent of the
[closed-at-format-drifts-between-closure-verbs-and-frontmatter-emitter](../closed-at-format-drifts-between-closure-verbs-and-frontmatter-emitter/)
fix (which also touched `_cmd_done_bundle` for `closed_at` quoting,
but did not address the attestation gap).

## Decision required

Three credible paths exist; pick one before implementation.

### Path A — `--bundle` runs the configured checks (most faithful to the docs)

Refactor `_cmd_done_bundle` to call the same loop `_cmd_attest`
uses: iterate `config["layer_2_project_dod"]` /
`config["layer_3_goc_dod"]`, dispatch by `kind` (`automated` /
`derived` / `manual` / `agent`), collect results per card, and emit
`_format_attestation_block` once per member alongside the existing
bundled-closure entry.

- **Pros:** matches the documented promise ("Use this in place of
  running `goc attest` + `goc done`"). Audit trail is honest.
- **Cons:** the bundle is no longer a fast mechanical close — manual
  / agent checks now prompt interactively per member, undermining
  the "share one attestation" framing for bundles that genuinely
  share verification. Needs a `--non-interactive` story.
- **`advanced-by-closed` for in-bundle members:** the check should
  count a bundle-mate as terminal-for-this-attestation (members
  flip to `done` atomically), so the derived check needs a
  `pending_terminal: set[str]` overlay supplied by the bundle path.

### Path B — `--bundle` refuses to close cards with non-trivial attestation

Inspect the configured checks at bundle entry. If any
layer-2/layer-3 check is configured (or any check beyond
`dod-100-percent`), refuse the bundle with a redirect:

```
ERROR: --bundle: attestation skip not allowed when layer-2/layer-3
checks are configured. Run `goc attest <title>` per member, then
`goc done` per member.
```

- **Pros:** small change, preserves the "fast bundle" use case for
  projects that opt out of layer-2/layer-3.
- **Cons:** breaks existing bundle workflows in this repo — the
  shipped config enables three layer-3 checks. Closes the gap by
  removing the bundle shortcut where it matters most.

### Path C — Document that `--bundle` skips attestation by design

Amend `finish-card/SKILL.md` Step 6 to state explicitly:

> `--bundle` records a closure-verification marker but does **not**
> run the layer-2 / layer-3 checks. Run `goc attest <title>` per
> member first, then bundle-close.

- **Pros:** zero code change; honesty alignment with current
  implementation.
- **Cons:** the bundle's "shared attestation" framing becomes a lie
  — a per-member `goc attest` *isn't* shared, it's a duplicate.
  Future readers still find the misleading PASS string in log.md.
  Leaves a footgun in place.

### Recommended

Path A. The bundle's value is atomic closure with one Closure
verification artifact; replacing the hard-coded PASS with the real
loop preserves that value without misleading audit trails. The
`pending_terminal` overlay on `advanced-by-closed` is a localized
ten-line change; manual/agent prompts in non-interactive contexts
already have a precedent in `_cmd_attest` (the
`--non-interactive` flag).

## Fix sketch (Path A — illustrative, NOT pre-applied)

In `goc/engine.py`:

1. Factor `_cmd_attest`'s per-check dispatch out of `_cmd_attest`
   into a `_run_attestation_checks(card, all_cards, today, *,
   skips, non_interactive, pending_terminal) → results` helper.
2. `_cmd_done_bundle` calls the helper per member with
   `pending_terminal=set(bundle_titles) - {title}` so
   `advanced-by-closed` treats in-bundle siblings as terminal.
3. `_cmd_done_bundle` replaces `_format_bundle_attestation_block`
   with the existing per-member `_format_attestation_block`, plus
   one shared `## Closure (bundled) ...` cross-reference entry.
4. On any failure: abort the bundle before any disk mutation, just
   like the existing per-member DoD-count check.

The skill docs and `tests/` follow whichever path is chosen.

## Cross-references

- `Skill(finish-card)` — Step 5 (`goc attest`) and Step 6
  (`goc done` + `--bundle`).
- [closed-at-format-drifts-between-closure-verbs-and-frontmatter-emitter](../closed-at-format-drifts-between-closure-verbs-and-frontmatter-emitter/)
  — the prior fix that touched `_cmd_done_bundle` for `closed_at`
  quoting but left this attestation gap untouched.
- [finish-card-records-implicit-dod-attestation](../finish-card-records-implicit-dod-attestation/)
  — the predecessor that added layer-2/layer-3 attestation to the
  closure flow; `_cmd_done_bundle` was not part of that wiring.
- [default-config-omits-goc-closure-checks](../default-config-omits-goc-closure-checks/)
  — the change that put `advanced-by-closed` /
  `log-md-closure-entry` / `dod-100-percent` into the shipped
  default config.
