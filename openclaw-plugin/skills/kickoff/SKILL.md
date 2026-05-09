---
name: kickoff
description: Kick off GoC in a fresh repo — introduce GoC, ask which persona fits, confirm AGENTS.md merge, scaffold project state via `goc install`. AUTO-INVOKE when the user says "kickoff", "use GoC here", "set up game of cards", "initialize GoC", or when any GoC skill is first used in a repo with no `.game-of-cards/deck/` directory. Host-agnostic: per-host complements (`claude-kickoff`, future `openclaw-kickoff`) handle host-specific UX.
---

# Kick off GoC in this repo

This skill is the **host-agnostic onboarding dialog**: it introduces GoC,
asks a few focused questions, then runs `goc install` to scaffold project
state. It runs **idempotently** — every stage detects on-disk state before
asking, so a re-run on a partially set-up repo only asks for the answers
it cannot already derive.

The body covers what every host needs. Host-specific UX (permission
prompts, plugin install cadence, private-notes file) lives in a
complementary per-host skill that runs after this one — for example,
`claude-kickoff` on the host.

## Stage 0 — state detection sweep

Read all of the on-disk signals at once. Each subsequent stage will skip
its question(s) when the corresponding signal is already present.

```bash
ls .game-of-cards/deck/ 2>/dev/null && echo "DECK_EXISTS" || echo "deck_missing"
which goc 2>/dev/null && echo "GOC_ON_PATH" || echo "goc_missing"
grep -l '<!-- BEGIN GOC' AGENTS.md 2>/dev/null && echo "AGENTS_MD_MERGED" || true
```

Route on the results:

- **`DECK_EXISTS`** → report "GoC is already initialized in this repo —
  deck is live." and **stop**. Do not continue. This is the silent-exit
  branch the skill description promises.
- **`goc_missing`** → halt at this stage. Tell the user: "`goc` CLI is
  not installed. Install it (e.g. `pipx install game-of-cards`, or use
  whatever plugin/runtime ships goc for your host) and re-run kickoff."
  Do not proceed without `goc`.
- **Otherwise** → continue. Hold the detected flags in mind through the
  rest of the flow.

---

## Stage 1 — introduce GoC

Skip this stage if `AGENTS_MD_MERGED` was detected in Stage 0 — it means
the user has engaged with kickoff before, and replaying the intro is
noise.

Otherwise, deliver this paragraph verbatim (no edits, no summarising):

> **Game of Cards (GoC)** is a lightweight, file-based methodology layer
> for software projects. It keeps a deck of cards — each card is a plain
> Markdown file with YAML frontmatter — that records every piece of
> persistent work: features, bugs, decisions, and experiments. The deck
> tracks status, value, and dependency edges between cards, so AI agents
> and human contributors share one authoritative view of what's in flight
> and what's next. GoC borrows from XP (user stories, spike experiments),
> Kanban (pull-based intake, explicit WIP limits), and Scrum (definition
> of done, backlog refinement). The CLI (`goc`) validates cards, renders
> board views, and gates closure on a per-card definition of done.

Then pause — do not continue to Stage 2 until the user acknowledges or
responds.

---

## Stage 2 — persona question

Skip this stage if `AGENTS_MD_MERGED` was already detected (Stage 3 has
nothing left to ask, so persona is moot).

Otherwise, ask the user **one question**:

> Which description best fits how you'll use GoC here?
>
> 1. **Solo / vibe-coder** — I'm the only contributor; I want a lightweight
>    personal task tracker with AI-agent help.
> 2. **Classical team** — We have a shared repo, multiple humans, and want
>    the deck as a shared source of truth alongside PRs and reviews.
> 3. **OSS / library evaluator** — I'm exploring GoC before deciding whether
>    to adopt it; I'd prefer not to merge anything into AGENTS.md yet.
> 4. **Agent-runtime / CI** — This repo is driven primarily by AI agents;
>    I want the CLI but minimal checked-in documentation overhead.

Record the user's answer. It drives the AGENTS.md default in Stage 3.

| Persona | AGENTS.md default |
|---|---|
| Solo / vibe-coder | Offer (yes default) |
| Classical team | Offer (yes default) — surface the external-deck-location guidance |
| OSS / library evaluator | Default **No** — user must opt in explicitly |
| Agent-runtime / CI | Default **No** |

---

## Stage 3 — AGENTS.md merge opt-in

Skip this question if Stage 0 detected `AGENTS_MD_MERGED`. Otherwise use
the persona default from Stage 2.

> Merge GoC guidance into `AGENTS.md`? This adds a `<!-- BEGIN GOC -->` block
> with agent-neutral instructions (deck philosophy, CLI verb table, operating
> modes). Suitable for any agent runtime that reads AGENTS.md. The block is
> marker-bounded and survives future `goc upgrade` runs; your existing content
> above and below the markers is untouched.
>
> Add to AGENTS.md? [yes/no]

If the persona is **Classical team**, add after the question:

> **Team tip:** For teams that keep the deck outside the repo (e.g., a shared
> network drive or separate Git repo), see the card
> `support-external-game-of-cards-state-location` — it tracks the design work
> for configurable deck paths.

Record the answer (or, if the question was skipped, record the detected
state). Pass it to Stage 4.

---

## Stage 4 — scaffold project state

Summarise the AGENTS.md answer collected in Stage 3, then ask:

> Ready to scaffold? This will create `.game-of-cards/` and (if you said
> yes) merge GoC guidance into `AGENTS.md`. Confirm? [yes/no]

On confirmation, run plain `goc install` (no per-file flags — the install
primitive always writes the AGENTS.md guidance block; the per-file opt-out
is applied below by stripping the block back out).

> **Note for this repo (game-of-cards source tree):** Translate bare `goc`
> commands to `uv run goc` when working in the goc package source tree itself.

`goc install` writes project state and merges the agent-neutral guidance
block into `AGENTS.md` (creating the file if absent). Host-specific files
like `.claude/skills/` are not written by this skill — host-specific
complement skills handle those.

After `goc install` returns, verify `.game-of-cards/deck/` exists before
continuing.

If the user said **No** to AGENTS.md in Stage 3, strip the GoC block back
out of the file:

```bash
python3 - <<'PY' <file>
import re, sys
from pathlib import Path
path = Path(sys.argv[1])
if not path.exists():
    sys.exit(0)
text = path.read_text()
pattern = re.compile(r"\n*<!-- BEGIN GOC v[\d.]+ -->.*?<!-- END GOC -->\n*", re.DOTALL)
new = pattern.sub("\n", text).strip()
header_only = re.fullmatch(r"# (Agent Guidelines|the host Guidelines)\s*", new)
if not new or header_only:
    path.unlink()
else:
    path.write_text(new + "\n")
PY
```

The snippet is idempotent: it removes the marker-bounded GoC section,
deletes the file when `goc install` created it from scratch (header +
GoC block only), and otherwise preserves any pre-existing user content
above or below the block. The same snippet is reused by host-specific
complement skills (e.g. `claude-kickoff`) to strip declined host-specific
guidance files.

---

## Stage 5 — confirm ready and hand off to host complement

Report to the user:

```
GoC is set up. The deck is live; `goc` and `goc validate` work.
```

If the host has its own kickoff complement (the host ships
`claude-kickoff`, OpenClaw ships its own equivalent when present), invite
the user to run it for host-specific finishing touches (permission
grants, agent-runtime hook registration, private notes files). Otherwise
recommend the next step:

```
What should the first card be?
```

The deck is now live. All other GoC skills work immediately — no further
generic kickoff needed.
