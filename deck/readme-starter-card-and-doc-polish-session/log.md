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

## 2026-05-04 - implementation and smoke evidence

- Implemented no-flag `goc install` auto-detection in `goc/install.py`:
  Claude markers are `CLAUDE.md`, `.claude/`, or `.mcp.json`; Codex
  markers are `AGENTS.md` or `.codex/`. Explicit `--agents`, `--claude`,
  and `--codex` still override detection.
- Changed post-install output to lead with prompting the LLM agent:

  ```text
  Next: ask your LLM agent: "create a card for the next change I want to make."
  Engine/debug: `goc` shows the queue; `goc validate` checks cards. Run `goc upgrade` later to sync template updates.
  ```

- Rewrote README `Try it`, `Agent harnesses`, `What you get`, and
  `Status` around the LLM-first install path, with CLI commands framed as
  engine/debug affordances.
- Updated local PyPI-facing metadata in `pyproject.toml`: description is
  now "LLM-first backlog cards for coding agents, stored as markdown in
  your repo." Keywords now include `llm`, `coding-agents`, `agents-md`,
  `codex`, and `developer-tools`. Live PyPI rendering remains old until a
  future release publishes this README/metadata.
- Updated GitHub About via `gh repo edit` and verified with
  `gh repo view zauberzeug/game-of-cards --json description,homepageUrl,repositoryTopics`:

  ```json
  {"description":"LLM-first backlog cards for coding agents, stored as markdown in your repo","homepageUrl":"https://pypi.org/project/game-of-cards/","repositoryTopics":[{"name":"agile"},{"name":"claude-code"},{"name":"codex"},{"name":"agents-md"},{"name":"ai-agents"},{"name":"coding-agents"},{"name":"developer-tools"},{"name":"kanban"},{"name":"llm"}]}
  ```

### Fresh install smokes

Claude-only marker repo:

```bash
cd /private/tmp/goc-readme-claude.4uDVT4
git init .
touch CLAUDE.md
uv run --project /Users/rodja/Projects/game-of-cards goc install
```

Output:

```text
goc 0.0.2 installed for agents: claude (auto-detected).
Next: ask your LLM agent: "create a card for the next change I want to make."
Engine/debug: `goc` shows the queue; `goc validate` checks cards. Run `goc upgrade` later to sync template updates.
```

`uv run --project /Users/rodja/Projects/game-of-cards goc` exited 0 with
empty output. `uv run --project /Users/rodja/Projects/game-of-cards goc
validate` exited 0 with empty output. Installed directories include
`.claude/skills/`, `.claude/hooks/`, `.game-of-cards/`, and `deck/`.

Codex-only marker repo:

```bash
cd /private/tmp/goc-readme-codex.iLgGbg
git init .
touch AGENTS.md
uv run --project /Users/rodja/Projects/game-of-cards goc install
```

Output:

```text
goc 0.0.2 installed for agents: codex (auto-detected).
Next: ask your LLM agent: "create a card for the next change I want to make."
Engine/debug: `goc` shows the queue; `goc validate` checks cards. Run `goc upgrade` later to sync template updates.
```

`uv run --project /Users/rodja/Projects/game-of-cards goc` exited 0 with
empty output. `uv run --project /Users/rodja/Projects/game-of-cards goc
validate` exited 0 with empty output. Installed directories include
`.codex/skills/`, `.game-of-cards/`, and `deck/`.

Both-detected marker repo:

```bash
cd /private/tmp/goc-readme-both.RMlkmC
git init .
touch CLAUDE.md
mkdir .codex
uv run --project /Users/rodja/Projects/game-of-cards goc install
```

Output:

```text
goc 0.0.2 installed for agents: claude,codex (auto-detected).
Next: ask your LLM agent: "create a card for the next change I want to make."
Engine/debug: `goc` shows the queue; `goc validate` checks cards. Run `goc upgrade` later to sync template updates.
```

`uv run --project /Users/rodja/Projects/game-of-cards goc` exited 0 with
empty output. `uv run --project /Users/rodja/Projects/game-of-cards goc
validate` exited 0 with empty output. Installed directories include
`.claude/skills/`, `.claude/hooks/`, `.codex/skills/`, `.game-of-cards/`,
and `deck/`.

No-marker/default repo:

```bash
cd /private/tmp/goc-readme-default.icxPpH
git init .
uv run --project /Users/rodja/Projects/game-of-cards goc install
```

Output:

```text
goc 0.0.2 installed for agents: claude (default).
Next: ask your LLM agent: "create a card for the next change I want to make."
Engine/debug: `goc` shows the queue; `goc validate` checks cards. Run `goc upgrade` later to sync template updates.
```

`uv run --project /Users/rodja/Projects/game-of-cards goc` exited 0 with
empty output. `uv run --project /Users/rodja/Projects/game-of-cards goc
validate` exited 0 with empty output. Installed directories include
`.claude/skills/`, `.claude/hooks/`, `.game-of-cards/`, and `deck/`.

### Verification

- `uv run python tests/test_install.py -k "install_auto_detects"`: 3 tests
  passed.
- `uv run python tests/test_install.py -k "install_help_describes_auto_detected_default"`:
  1 test passed.
- `uv run python tests/test_install.py -k "no_marker_install_output"`: 1
  test passed.
- `uv run python tests/test_install.py -k "install_smoke"`: 2 tests passed.
- `uv run goc validate`: all cards OK.
- `uv run python tests/test_install.py`: 20 tests passed.

## 2026-05-04 - Closure

- **What changed**: `goc/install.py`, `README.md`, and `pyproject.toml` now
  present install as an LLM-first workflow: no-flag install auto-detects
  Claude/Codex markers, the post-install next step is an agent prompt, local
  package metadata matches that positioning, and GitHub About metadata was
  updated to the same description/topics.
- **Verification**: four fresh install smokes passed; `uv run python
  tests/test_install.py` ran 20 tests successfully; `uv run goc validate`
  reported all cards OK.
- **Audit**: PASS - no rubric configured; mechanical fix
- **Project impact**: first-run experience now matches the agent-facing
  methodology substrate.
- **Tests**: 20 passed / 0 failed / 0 xfailed
- **Bundled with**: n/a

## Closure verification (2026-05-04)
