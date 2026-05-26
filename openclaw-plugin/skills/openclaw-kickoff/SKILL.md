---
name: openclaw-kickoff
description: OpenClaw-specific complement to the generic kickoff skill — note the `openclaw plugins update` cadence, surface the `inspect`/`doctor` sanity-check verbs, and confirm the host needs no permission grant or private-notes file. AUTO-INVOKE after the generic kickoff completes on an OpenClaw host, or when the user says "finish kickoff for OpenClaw", "set up OpenClaw for goc", or initiates OpenClaw-specific GoC setup that the generic kickoff intentionally skipped.
---

# Finish kickoff on OpenClaw

The generic `kickoff` skill is host-agnostic: it introduces GoC, runs the
persona dialog, asks about the AGENTS.md merge, and runs `goc install` to
scaffold `.game-of-cards/`. This complement handles everything OpenClaw-specific
that the generic kickoff intentionally leaves alone:

- the ClawHub / npm install + update cadence,
- the `openclaw plugins inspect` / `openclaw plugins doctor` sanity check,
- explicitly confirming that OpenClaw needs no permission grant and has
  no host-specific private-notes file (so the user does not go looking
  for a `CLAUDE.local.md` analog that does not exist).

Run this skill **after** the generic kickoff returns. Re-running is safe:
every stage detects existing on-disk state before asking.

## Stage 0 — state detection sweep

Confirm the GoC plugin is registered with OpenClaw:

- `openclaw plugins list` should show `game-of-cards` as enabled.
- `openclaw plugins inspect game-of-cards` should list `goc` under
  `contracts.tools` AND under `toolNames` (the latter is the runtime
  registration; if it is empty while `contracts.tools` lists `goc`, the
  plugin's `register()` callback never fired — re-install or run
  `openclaw plugins doctor`).
- `python3 --version` should report 3.10 or newer; the plugin bundles
  the goc engine but expects `python3` on the host PATH.

Hold the detected flags in mind through the rest of the flow. The
generic kickoff has already run, so `.game-of-cards/deck/` exists,
`AGENTS.md` has been handled, and the `goc` tool is callable.

---

## Stage 1 — install / update cadence note

Skip this stage if `openclaw plugins list` already shows `game-of-cards`
in the active session.

Otherwise, deliver this note to the user:

> The Game of Cards OpenClaw plugin ships skills, lifecycle hooks, and
> the bundled `goc` engine. To install (one-time per host):
>
> ```
> openclaw plugins install game-of-cards
> ```
>
> Or via npm directly:
>
> ```
> npm install -g game-of-cards
> openclaw plugins install game-of-cards
> ```
>
> When updating later, run `openclaw plugins update game-of-cards`
> (or `openclaw skills update --all` if only skill payloads changed).
> If the post-update plugin behaves unexpectedly, run
> `openclaw plugins doctor` to surface load errors and
> `openclaw plugins inspect game-of-cards` to confirm the `goc` tool
> registered.

The plugin's only consumer prerequisite is `python3` (3.10+) on PATH.
No `uv`, no `pipx`, no venv materialization.

---

## Stage 2 — confirm what OpenClaw does NOT need

State the two non-instructions explicitly so the user does not go
hunting for a the host-style analog:

> **No permission grant required.** the host gates `Bash(goc:*)`
> behind a per-project allowlist. OpenClaw exposes `goc` as a registered
> tool through the plugin sandbox — once the plugin is installed and
> enabled, the tool is callable with no further opt-in.
>
> **No host-specific private-notes file.** the host conventions
> include `CLAUDE.local.md` for project-local notes the agent reads but
> Git ignores. OpenClaw has no equivalent convention; project-local
> notes can live anywhere the user prefers (or in `AGENTS.md`, which the
> generic kickoff already handled).
>
> **No `CLAUDE.md` either.** Run from the OpenClaw plugin, `goc install`
> recognizes the host and scaffolds a no-harness layout — `.game-of-cards/`
> plus the `AGENTS.md` briefing — and never writes a `CLAUDE.md`. The
> dry-run plan reads `agents: none`; that is correct on OpenClaw, not a
> missed harness.

---

## Stage 3 — confirm ready

Report to the user:

```
OpenClaw-specific kickoff is complete. All GoC skills are live through
the plugin; the `goc` tool is callable from any GoC repo on this host.
What should the first card be?
```

The deck is now live. The agent can invoke any GoC skill (`scan-deck`,
`create-card`, `pull-card`, …) immediately — no further kickoff needed.
