## 2026-10-31 — Filed

Surfaced while closing
[openclaw-prompt-hook-fires-in-workspaces-without-a-deck](../openclaw-prompt-hook-fires-in-workspaces-without-a-deck/).
`npm ci` in `openclaw-plugin/` (needed for that card's `dist/` rebuild)
installed the pinned `openclaw@2026.5.7`. Its hook types and runner show that
the host calls `handler(event, ctx)` and merges only the return value, and no
handler in `index.ts` uses that shape. Checked two ways: `reproduce.py` calls
each handler as the host does, and the compiled plugin was also registered
into the SDK's own hook runner, where `runBeforePromptBuild` returned
`undefined` for a work prompt in a workspace with a deck.

Not fixed through. Two of the three hooks are void, so their messages need a
channel someone has to choose. Making the hooks work also switches on
reminders that live deployments have never seen. Parked at
`human_gate: decision`.

## 2026-11-09T02:10:03Z — Cites written against ffc0f4bc's tree, not the filing commit's

A refine-deck citation pass anchored this card's `openclaw-plugin/index.ts`
cites at its filing commit `66678c34` (05:16:46Z) and proposed moving
`:763` → `:769` and `:797` → `:804`. Both proposals were wrong: the card's
numbers were computed against the tree `ffc0f4bc` committed six minutes
later (05:23:26Z), which added six comment lines and a `hasDeck` guard above
them. At HEAD every `index.ts` number in § Location names exactly what the
prose says — `:763` the `before_prompt_build` registration, `:797` the
`agent_end` registration, and the bare `:764`, `:773`, `:798`, `:808`,
`:819`, `:821` the reads and deliveries listed.

`:763` was held; `:797` had been applied and is restored here. Until the
recipe can tell which tree a cite was written against, a pass should leave
`:763` alone: its anchor at `66678c34` is `if ((hasExploration ||
hasTooling) && !hasWork) return;`, which HEAD holds uniquely at `:769`.
