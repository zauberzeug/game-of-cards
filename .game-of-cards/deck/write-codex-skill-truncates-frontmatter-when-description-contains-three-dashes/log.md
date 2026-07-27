## 2026-07-27 — Deck hygiene: falsifying recipe run, `unverified` stripped

`Skill(refine-deck)`'s stale-park sweep flagged this card as the only
`unverified` card in the deck that ships a `reproduce.py`. Per the skill's
"retry the falsifying recipe" path the script was run against HEAD:

```
$ uv run python .game-of-cards/deck/write-codex-skill-truncates-frontmatter-when-description-contains-three-dashes/reproduce.py
FAIL — `_write_codex_skill` corrupted the skill:
  expected description: 'Use --- as a section delimiter in your prose'
  observed description: '"Use'
EXIT=1
```

The ported output also carries the two other symptoms the summary predicted:
the tail of the description (` as a section delimiter in your prose"`) is
emitted into the rendered Codex body after the injected bootstrap block, and a
third `---` delimiter is left dangling. Reproduction is clean, so the
`unverified` predicate ("no working `reproduce.py` AND tagged at filing",
`Skill(card-schema)` § Canonical tags) no longer fires and the tag was
stripped.

The body's opening paragraph had set promotion at "once a downstream skill
carries the trigger pattern". That criterion measures *reachability*, not
*verification* — two independent things the tag was conflating. The paragraph
was rewritten in place (README is a dashboard) to state both: the defect is
verified, the trigger is latent. Reachability stays encoded where it belongs,
in `contribution: low`.

No status change and no decision recorded: `human_gate: decision` stands
because `## Decision required` still asks which of three fix shapes to take.
