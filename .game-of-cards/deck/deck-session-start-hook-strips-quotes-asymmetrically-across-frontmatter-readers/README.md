---
title: deck-session-start-hook-strips-quotes-asymmetrically-across-frontmatter-readers
summary: "`goc/templates/hooks/deck_session_start.py` re-implements YAML-lite frontmatter parsing for four fields (`status`, `human_gate`, `waiting_on`, `waiting_until`). Two of the four readers strip outer quotes from the parsed value (`_card_waiting_on` line 65 and `_card_waiting_until` line 81 both call `.strip().strip('\"').strip(\"'\")`), the other two do not (`_card_status` line 33 and `_card_human_gate` line 49 call only `.strip()`). The asymmetry is latent today because `_yaml_inline` in `goc/engine.py:229-239` only quotes scalars containing colons, hashes, brackets, etc. — none of the enum values for `status` or `human_gate` trigger that path. If a future migration or schema change ever emits a quoted form (e.g. `status: \"active\"`), the SessionStart hook would silently classify every active card as non-active, suppressing the reminder that the recently-closed `session-start-hook-shows-gated-active-cards-as-resumable` and `session-start-hook-frames-waiting-on-active-cards-as-resumable` cards just restored. Unverified because the defect does not fire on current emitter output."
status: done
stage: null
contribution: low
created: "2026-05-29T21:51:11Z"
closed_at: "2026-05-29T21:56:15Z"
human_gate: none
advances:
  - session-start-hook-reimplements-engine-waiting-and-frontmatter-logic-and-keeps-drifting
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [x] EMPIRICAL: `deck/<title>/reproduce.py` constructs a temp deck with one card whose frontmatter uses quoted-form `status: "active"` and `human_gate: "decision"`, invokes the SessionStart hook on it, and prints whether the card was classified as resumable / parked / impeded vs. silently dropped. Promotion to a confirmed defect requires the reproduce.py to demonstrate misclassification.
  - [x] MECHANICAL: align the four readers — either all four strip outer quotes (symmetric defensive coding, matches `waiting_on` / `waiting_until`) or none do (symmetric trust in the engine's bare-form contract). Update `goc/templates/hooks/deck_session_start.py:33` and `:49` to match the chosen convention.
  - [x] PROCESS: re-sync plugin mirrors (`python scripts/sync_plugin_assets.py`) and re-run the OpenClaw TypeScript port if the hook's behavior changed (the TS reimpl lives in `openclaw-plugin/index.ts`).
  - [x] PROCESS: `uv run python -m unittest discover -s tests` and `uv run goc validate` both pass.
worker: {who: "claude[bot]", where: main}
---

# `deck_session_start.py` strips quotes asymmetrically across frontmatter readers

## Location

`goc/templates/hooks/deck_session_start.py:23-83` — four frontmatter readers.

## What's broken (latent)

The SessionStart hook re-implements YAML-lite frontmatter parsing
"so it has no package dependency and runs from any working tree
shape" (per `_parse_waiting_until` docstring at line 92-96). Four
readers each scan the frontmatter block for a single key:

```python
# line 33 — _card_status
return line.split(":", 1)[1].strip()

# line 49 — _card_human_gate
val = line.split(":", 1)[1].strip()
return val or "none"

# line 65 — _card_waiting_on
val = line.split(":", 1)[1].strip().strip('"').strip("'")
return val or None

# line 81 — _card_waiting_until
val = line.split(":", 1)[1].strip().strip('"').strip("'")
return val or None
```

Two readers (`_card_waiting_on`, `_card_waiting_until`) defensively
strip outer double-quote then single-quote characters. The other
two (`_card_status`, `_card_human_gate`) do not. If a card's
frontmatter ever contains `status: "active"` instead of bare
`status: active`, the hook's `_card_status` returns the literal
string `'"active"'` (with quotes), and the equality check at line
178 (`if _card_status(readme) != "active": continue`) treats the
card as not-active and silently skips it. The same misclassification
applies to `_card_human_gate` at line 183.

## Why it matters (and why it's unverified)

The engine's `_yaml_inline` in `goc/engine.py:229-239` only quotes
scalars matching `_YAML_NEEDS_QUOTE = re.compile(r"[:#'\"\\\[\]\{\}\,`@]")`
or hitting other quoting conditions. None of the canonical enum
values for `status` (`open`, `active`, `blocked`, `done`,
`disproved`, `superseded`) or `human_gate` (`none`, `decision`,
`session`) contain those characters, so today the engine always
writes them bare. The asymmetry between the four hook readers does
not produce visible misclassification on any current card.

It WILL fire if:

- A future migration or schema change adopts quoted-form status
  values (e.g. to harmonize with `closed_at` / `created` which are
  already quoted as ISO strings).
- A hand-authored card uses quoted form by accident or by a
  third-party tool emitting the more conservative YAML shape.
- A new status or gate enum value contains a character in
  `_YAML_NEEDS_QUOTE` (any future enum extension would need to be
  carefully chosen — this constraint is currently undocumented).

If the hook ever misclassifies the active-card status, the
SessionStart reminder fails silently — the same failure mode the
recently-closed `session-start-hook-shows-gated-active-cards-as-resumable`
and `session-start-hook-frames-waiting-on-active-cards-as-resumable`
cards (both closed 2026-05-29) explicitly restored.

Reachability path: the engine emitter writes status/human_gate
values via `mutate_frontmatter_field(text, "status", new_status)`
(`engine.py:4000`) which delegates to a regex-based line-rewrite
that does NOT pass through `_yaml_inline` — so a quoted form would
not be emitted by the current `_cmd_status` path. But `goc move`,
`goc migrate-list-style`, and any code that re-emits frontmatter
via `emit_frontmatter(fm, body=body)` (e.g. `_cmd_wait` at line
4359, `_cmd_decide` at line 4579) routes through `_yaml_inline`,
which preserves the round-tripped form. If a hand-authored
`status: "active"` slipped in, `emit_frontmatter` would normalize
it back to bare `active` — but only if the rewriting verb fires
first. Until then, the hook sees the quoted form.

## Fix proposal

Align the four readers. Two options:

- **Option A (defensive, symmetric strip):** add `.strip('"').strip("'")`
  to `_card_status` and `_card_human_gate`. Mirrors the existing
  defensive treatment of `waiting_on` / `waiting_until`.
- **Option B (trust the contract, symmetric bare):** remove the
  defensive strip from `_card_waiting_on` and `_card_waiting_until`.
  Smaller, but exposes the same latent risk for those fields.

Recommend **Option A**: the hook explicitly cannot import the engine
(line 92-96 docstring), so it must tolerate whatever YAML-lite shape
the engine emits. The defensive strip is the cheap insurance that
matches the hook's stated design.

After picking the convention, the TypeScript reimplementation in
`openclaw-plugin/index.ts` must be updated symmetrically (the hook
is hand-ported to TS for the OpenClaw plugin) — otherwise the two
hook implementations drift.

## Promotion path

Unverified → confirmed defect when:

1. `reproduce.py` writes a card with `status: "active"` (quoted),
   invokes `_card_status` / the full hook `main()`, and prints
   "MISCLASSIFIED" if the card was silently dropped.
2. The MECHANICAL fix lands and the reproduce.py exits zero
   (classification matches expected).
