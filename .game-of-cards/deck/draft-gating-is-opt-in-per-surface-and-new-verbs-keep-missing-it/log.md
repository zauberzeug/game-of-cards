

## 2026-07-13 — Deck hygiene pass

Wired the meta-fix family roster surfaced by the orphaned-dependency sub-check (zero edges despite the body linking three closed instances): `advanced_by += goc-triage-lists-unauthored-draft-scaffolds-as-parked-cards, waiting-filter-surfaces-draft-scaffolds-as-active-impediments, ready-leverage-line-names-draft-scaffolds-as-the-highest-gated-card`.

## 2026-08-07 — instance six recorded (connect, not duplicate)

An audit pass with an empty ready queue found a sixth surface that skips
`card_is_draft`: `validate_dod_method_tags` (`engine.py:2268-2294`) exempts
terminal cards but not drafts, so `goc validate` emits `UNTAGGED_DOD_ITEM`
against `SCAFFOLD_DOD_PLACEHOLDER` (`engine.py:2424`) — the untagged DoD stub
`goc new` itself writes — on every freshly scaffolded card.

Reproduced on a scratch deck with two commands (`goc new fresh-scaffold-card
--summary "a fresh scaffold"`, then `goc validate`):

```
WARN UNTAGGED_DOD_ITEM fresh-scaffold-card: 1 DoD item(s) lack a method tag
(TDD:/EMPIRICAL:/MECHANICAL:/PROCESS:): [- [ ] (replace with real criteria)]
OK  fresh-scaffold-card
```

Recorded here rather than filed as a new card, deliberately. This card is the
open umbrella for exactly this root cause, it is parked at `human_gate:
decision` pending a mechanism pick (inverted default vs validate-time lint vs
per-site fixes), and a per-site patch would pre-empt that decision. Filing a
seventh sibling would also be the redundant-umbrella move that
`Skill(create-card)`'s dedup step and the Stop hook's dedup-then-connect
branch both warn against. The body's instance list and summary were updated
in place; no status, gate or edge changed.

Note for whoever picks the mechanism: this instance discriminates between the
options more sharply than the other five. It is not a surface *listing* an
unauthored card — it is goc criticising its own generated text, which no
per-site `if card_is_draft(c): continue` reads as a principled fix so much as
a sixth patch.

## 2026-08-11 — evidence added: un-gating is per-site too

Connected from
[zero-match-line-claims-hidden-drafts-that-publishing-would-not-surface](../zero-match-line-claims-hidden-drafts-that-publishing-would-not-surface/),
closed today. Not a seventh instance of "a surface forgot to exclude drafts" —
the mirror image, and it bears on the mechanism choice.

Producing the zero-match line's hidden-draft count means asking "would this
card appear if its draft flag were cleared?". Because `card_is_draft` is
inlined per call site, that counterfactual had to be threaded through each site
separately as an opt-in `include_drafts` keyword: `filter_cards` and
`card_is_ready` (predecessor card), then `live_impeded` (this one, found when
`goc --waiting --status open` claimed a draft was hidden that publishing would
not have revealed). Three keywords, three cards, one predicate.

Consequence for the decision below: an inverted default that only makes
"exclude drafts" implicit would still leave the counterfactual scattered. The
mechanism should be judged on both directions — one place to apply the gate AND
one place to ask what it removed. No DoD item ticked and no gate change; this
is evidence for whoever picks.
