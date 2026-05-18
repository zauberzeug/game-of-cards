## Game of Cards — Claude Code specifics

GoC ships as a Claude Code plugin bundling skills, hooks, and the
`goc` CLI:

```
/plugin marketplace add zauberzeug/game-of-cards
/plugin install game-of-cards@game-of-cards
```

In a fresh repo, invoke `Skill(kickoff)` — it scaffolds `.game-of-cards/`
then hands off to `Skill(claude-kickoff)` for the permission grant and
the briefing-target prompt.

**Closure is not frozenness.** When new evidence surfaces after a card
closes, file a new card for the new work and amend the closed card
with a forward pointer (dated `log.md` append; optional `> Later
evidence:` line atop the README). See `Skill(finish-card)` "After
closure" for the format.
