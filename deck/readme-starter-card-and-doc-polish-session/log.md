## 2026-05-04 - card refinement

- Read the current card and README. The README no longer clearly promises
  automatic starter-card creation; the remaining product question is whether
  install should stay empty-deck-first or create an example card.
- Found live version drift: `pyproject.toml` and `goc.__version__` are
  `0.0.2`, while the README Status section still says `0.0.1`.
- Noted concurrent local context: the README now has an `Agent harnesses`
  section, and the working tree has an installer-manifest refactor in
  `goc/install.py` plus `goc/templates/agents/`. The card scope now tells
  the README pass to reconcile that section without owning the refactor.
- Ran a fresh Codex install smoke in `/private/tmp/goc-readme-smoke.fbr2s7`:
  `git init .`, then
  `uv run --project /Users/rodja/Projects/game-of-cards goc install --agents codex`.
  Output:

  ```text
  goc 0.0.2 installed for agents: codex.
  Next: `goc new my-first-card`. Run `goc upgrade` later to sync template updates.
  ```
- Observed installed files: `.codex/skills/`, `.game-of-cards/`,
  `.pre-commit-config.yaml`, `AGENTS.md`, `deck/log.md`, and
  `deck/.goc-version`; no `deck/<card>/` directory was created. `goc` and
  `goc validate` both exited 0 with no output on the empty deck.

## 2026-05-04: decision recorded

Install should auto-detect existing Claude/Codex project usage, install matching harnesses, and present LLM prompting as the primary first-run interface rather than CLI card commands — Game of Cards is an agent-facing methodology substrate; users should experience the LLM workflow first while the goc CLI remains the engine behind the installed guidance. Gate session → none.

## 2026-05-04 - metadata check

- PyPI JSON API reports live `game-of-cards` version `0.0.2`. The rendered
  package README still contains old first-run copy saying `goc install`
  adds "deck/, CLAUDE.md/AGENTS.md sections, a starter card" and still
  leads with `goc new` / `goc done` examples. Local `pyproject.toml`
  description is "Backlog tracking as a folder of markdown story-cards in
  your repo. Agent-readable. No proprietary state." Keywords are
  `agile`, `kanban`, `xp`, `ai-agents`, `agentic-workflow`, `substrate`,
  `claude-code`, `agents-md`, `methodology`.
- GitHub API reports description "Agile development in the age of AI
  agents", empty homepage, and topics `agents`, `agile`, `claude`,
  `claude-code`, `codex`, `openclaw`, `todo`, `workflow`.
- Card scope now requires the implementation pass to align README,
  pyproject/PyPI metadata, and GitHub About/topics around the LLM-first
  interface. `openclaw` should be removed until the OpenCLAW harness ships.
