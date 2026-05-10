---
name: claude-kickoff
description: Claude Code-specific complement to the generic kickoff skill — handle Bash(goc:*) permission grant, /plugin install cadence, and CLAUDE.md / CLAUDE.local.md merge prompts. AUTO-INVOKE after `Skill(kickoff)` completes on a Claude Code repo, or when the user says "finish kickoff for Claude", "set up Claude Code permissions", "/plugin update for goc", or initiates Claude-specific GoC setup that the generic kickoff intentionally skipped.
---

# Finish kickoff on Claude Code

The generic `kickoff` skill is host-agnostic: it introduces GoC, runs
the persona dialog, asks where the briefing should live (`AGENTS.md`,
`CLAUDE.md`, or `CLAUDE.local.md`), and runs `goc install
--briefing-target <choice>` to scaffold `.game-of-cards/`. This
complement handles everything Claude Code-specific that the generic
kickoff intentionally leaves alone:

- the `Bash(goc:*)` permission grant for future sessions,
- the `/plugin install` (and `/plugin marketplace update`) cadence,
- the minimal `CLAUDE.md` `@<chosen-file>` pointer when the briefing
  lives in `AGENTS.md` or `CLAUDE.local.md`,
- writing GoC-managed entries into `.claude/settings.json`.

Run this skill **after** the generic kickoff returns. Re-running is safe:
every stage detects existing on-disk state before asking.

> **Updating the plugin?** Run `/plugin marketplace update zauberzeug/game-of-cards`
> before `/plugin install` — Claude Code reuses its local marketplace clone and does
> not refresh it automatically. Skipping this step silently installs the old bytes.

## Stage 0 — state detection sweep

Read the on-disk signals that determine which stages still have work to do:

```bash
grep -l '<!-- BEGIN GOC' AGENTS.md CLAUDE.md CLAUDE.local.md 2>/dev/null
```

The first matching file (or the only matching file) is the **briefing
target** — the home the generic kickoff chose. Hold that path; Stage 2
needs it.

Read the project's `.claude/settings.json` and `~/.claude/settings.json`
with the Read tool. Note whether `"Bash(goc:*)"` appears in either
`permissions.allow` array. Note whether `.claude/hooks/` already contains
the GoC-managed hook scripts (the plugin path supplies them; if they're
absent the user is on the vendored path).

Hold all of these flags in mind through the rest of the flow. The
generic kickoff has already run, so `.game-of-cards/deck/` exists, `goc`
is on PATH, and the briefing lives in exactly one of the three
candidates — this skill does not re-check those.

---

## Stage 1 — `/plugin install` cadence note

Skip this stage if Claude Code's plugin runtime already exposes the GoC
skill set in this session (the user reached this skill via
`Skill(claude-kickoff)`, which means the plugin is registered).

Otherwise, deliver this note to the user:

> The Game of Cards Claude Code plugin ships skills, runtime hooks, and
> the bundled `goc` CLI. To install (one-time per machine):
>
> ```
> /plugin marketplace add zauberzeug/game-of-cards
> /plugin install game-of-cards@game-of-cards
> ```
>
> When updating later, run `/plugin marketplace update zauberzeug/game-of-cards`
> before `/plugin install` — Claude Code reuses its local marketplace clone
> and does not refresh it automatically.

If the user prefers to vendor skills into source control (CI without
plugin support, repos that fork or template GoC), add:

> Alternatively, install via `pipx install game-of-cards` and run
> `goc install --local-skills` to vendor skills, hooks, and settings into
> `.claude/`. The plugin-bundled `goc` refuses `--local-skills`; the pipx
> CLI is the only path that writes a vendored `.claude/skills/` tree.

---

## Stage 2 — wire CLAUDE.md to the briefing

Claude Code only auto-loads `CLAUDE.md` (and `CLAUDE.local.md` next to
it). When the briefing lives elsewhere, Claude needs a one-line
`@<file>` import in `CLAUDE.md` to transitively load it.

Use the **briefing target** path detected in Stage 0:

- **target = `CLAUDE.md`** — Claude already sees the full briefing
  inline. Skip this stage entirely; do not write a separate import.
- **target = `AGENTS.md`** — write a minimal `CLAUDE.md` containing
  only `@AGENTS.md` inside a marker block.
- **target = `CLAUDE.local.md`** — write a minimal `CLAUDE.md`
  containing only `@CLAUDE.local.md` inside a marker block.

When a write is required, use this snippet (substitute `<target>`):

```bash
python3 - <<'PY' CLAUDE.md AGENTS.md
import re, sys
from pathlib import Path
claude_md, target_file = Path(sys.argv[1]), sys.argv[2]
block = (
    "<!-- BEGIN GOC IMPORT -->\n"
    f"@{target_file}\n"
    "<!-- END GOC IMPORT -->\n"
)
if not claude_md.exists():
    claude_md.write_text("# Claude Code Guidelines\n\n" + block)
    sys.exit(0)
text = claude_md.read_text()
pattern = re.compile(r"<!-- BEGIN GOC IMPORT -->.*?<!-- END GOC IMPORT -->\n?", re.DOTALL)
if pattern.search(text):
    claude_md.write_text(pattern.sub(block, text))
else:
    claude_md.write_text(text.rstrip() + "\n\n" + block)
PY
```

(Replace the `AGENTS.md` argument with `CLAUDE.local.md` when that is
the briefing target.) The snippet uses the `<!-- BEGIN GOC IMPORT -->`
marker — distinct from the briefing's `<!-- BEGIN GOC v… -->` — so
`goc upgrade`'s briefing-detection logic does not mistake the import
for a competing briefing home. The snippet preserves any pre-existing
user content in CLAUDE.md above and below the marker block.

If the briefing target is `CLAUDE.local.md` and the file does not yet
exist (the generic kickoff already created it as the briefing home, so
this is rare), no extra stub is needed — the file holds the briefing.

---

## Stage 3 — persist `Bash(goc:*)` permission

If Stage 0 detected `Bash(goc:*)` already in either settings.json (or an
interactive grant during the generic kickoff's `goc install` already
wrote it), this stage is a no-op.

Otherwise, write the project's `.claude/settings.json` with:

```json
{
  "permissions": {
    "allow": ["Bash(goc:*)"]
  }
}
```

Merge with any existing `.claude/settings.json` content rather than
overwriting it. After the file is written, tell the user:

> `Bash(goc:*)` is now permitted for this project's future Claude Code
> sessions. The current session continues to work without a restart.

This is the LAST mutation `claude-kickoff` makes. Any future enhancement
that needs a context-losing session restart must remain after this point
so a restart never destroys work already done.

---

## Stage 4 — confirm ready

Report to the user:

```
Claude Code-specific kickoff is complete. All GoC skills are live
through the plugin (or the vendored `.claude/skills/` if you opted in).
What should the first card be?
```

The deck is now live. `Skill(create-card)`, `Skill(scan-deck)`, and all
other GoC skills work immediately — no further kickoff needed.

---

## Reference: runtime hooks

When the GoC plugin is installed, three hooks fire automatically:

| Hook event | Script | Purpose |
|---|---|---|
| `SessionStart` | `deck_session_start` | Prints active-card reminder at session start; silent when no cards are in-flight. |
| `UserPromptSubmit` | `deck_prompt_router` | Detects work-initiating prompts; injects a deck-first reminder into Claude's view. |
| `Stop` | `pattern_generalization_check` | After code-mutating turns, asks the agent to self-assess whether the change warrants a generalization card. Opt-out: set `hooks.pattern_generalization_check: false` in `.game-of-cards/config.yaml`. |

The hooks are optional. Repos without the plugin still get full GoC
functionality through the `goc` CLI and AGENTS.md guidance. Other
agent runtimes (Codex, OpenCode, Cursor) use their own hook systems
and do not share this registration.
