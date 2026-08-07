

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
