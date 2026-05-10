## Game of Cards — Claude Code specifics

@AGENTS.md

The shared briefing is in AGENTS.md (imported above). On Claude Code,
GoC ships as a plugin bundling skills, hooks, and the `goc` CLI:

```
/plugin marketplace add zauberzeug/game-of-cards
/plugin install game-of-cards@game-of-cards
```

In a fresh repo, invoke `Skill(kickoff)` — it scaffolds `.game-of-cards/`
then hands off to `Skill(claude-kickoff)` for the permission grant and
CLAUDE.md / CLAUDE.local.md merge prompts.
