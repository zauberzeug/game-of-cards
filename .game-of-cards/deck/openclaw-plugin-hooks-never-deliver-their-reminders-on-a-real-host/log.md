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
