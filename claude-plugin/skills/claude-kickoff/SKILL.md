---
name: claude-kickoff
description: Claude Code-specific complement to the generic kickoff skill — handle Bash(goc:*) permission grant, /plugin install cadence, and CLAUDE.md / CLAUDE.local.md merge prompts. AUTO-INVOKE after `Skill(kickoff)` completes on a Claude Code repo, or when the user says "finish kickoff for Claude", "set up Claude Code permissions", "/plugin update for goc", or initiates Claude-specific GoC setup that the generic kickoff intentionally skipped.
---

# Finish kickoff on Claude Code

The generic `kickoff` skill is host-agnostic: it introduces GoC, runs the
persona dialog, asks about the AGENTS.md merge, and runs `goc install` to
scaffold `.game-of-cards/`. This complement handles everything Claude
Code-specific that the generic kickoff intentionally leaves alone:

- the `Bash(goc:*)` permission grant for future sessions,
- the `/plugin install` (and `/plugin marketplace update`) cadence,
- the per-file `CLAUDE.md` / `CLAUDE.local.md` merge prompts,
- writing GoC-managed entries into `.claude/settings.json`.

Run this skill **after** the generic kickoff returns. Re-running is safe:
every stage detects existing on-disk state before asking.

> **Updating the plugin?** Run `/plugin marketplace update zauberzeug/game-of-cards`
> before `/plugin install` — Claude Code reuses its local marketplace clone and does
> not refresh it automatically. Skipping this step silently installs the old bytes.

## Stage 0 — state detection sweep

Read the on-disk signals that determine which stages still have work to do:

```bash
grep -l '<!-- BEGIN GOC' CLAUDE.md 2>/dev/null && echo "CLAUDE_MD_MERGED" || true
test -f CLAUDE.local.md && echo "CLAUDE_LOCAL_MD_EXISTS" || true
```

Read the project's `.claude/settings.json` and `~/.claude/settings.json`
with the Read tool. Note whether `"Bash(goc:*)"` appears in either
`permissions.allow` array. Note whether `.claude/hooks/` already contains
the GoC-managed hook scripts (the plugin path supplies them; if they're
absent the user is on the vendored path).

Hold all of these flags in mind through the rest of the flow. The
generic kickoff has already run, so `.game-of-cards/deck/` exists, `goc`
is on PATH, and AGENTS.md has been handled — this skill does not re-check
those.

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

## Stage 2 — per-file merge opt-in (CLAUDE.md / CLAUDE.local.md)

For each file, skip the question if Stage 0 detected its final state on
disk.

**Question A — CLAUDE.md** (skip if `CLAUDE_MD_MERGED` was detected)

> Merge GoC guidance into `CLAUDE.md`? This adds a `<!-- BEGIN GOC -->` block
> with Claude Code-specific instructions (skill surface, hook descriptions,
> first-use setup). The block is marker-bounded and survives future `goc upgrade`
> runs. Your existing content above and below the markers is untouched.
>
> Add to CLAUDE.md? [yes/no]

If the user said **No**, strip the block back out — `goc install` from
the generic kickoff already wrote it. Use the strip snippet from the
generic kickoff (Stage 4 of `kickoff`):

```bash
python3 - <<'PY' CLAUDE.md
import re, sys
from pathlib import Path
path = Path(sys.argv[1])
if not path.exists():
    sys.exit(0)
text = path.read_text()
pattern = re.compile(r"\n*<!-- BEGIN GOC v[\d.]+ -->.*?<!-- END GOC -->\n*", re.DOTALL)
new = pattern.sub("\n", text).strip()
header_only = re.fullmatch(r"# (Agent Guidelines|Claude Code Guidelines)\s*", new)
if not new or header_only:
    path.unlink()
else:
    path.write_text(new + "\n")
PY
```

**Question B — CLAUDE.local.md** (skip if `CLAUDE_LOCAL_MD_EXISTS` was
detected)

> Add a minimal `CLAUDE.local.md` stub? This gives Claude Code a private,
> untracked file to record project-local notes without touching checked-in
> docs.
>
> Create CLAUDE.local.md stub? [yes/no]

If yes:

```bash
test -f CLAUDE.local.md || cat > CLAUDE.local.md <<'EOF'
# Local notes for Claude Code (not checked in)
EOF
```

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
