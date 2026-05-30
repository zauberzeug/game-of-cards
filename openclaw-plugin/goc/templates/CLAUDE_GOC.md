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
