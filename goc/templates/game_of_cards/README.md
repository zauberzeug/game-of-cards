# `.game-of-cards/` — project-specific configuration for goc

This directory holds the per-repo configuration the goc-shipped skills
read at runtime. The skills are domain-agnostic; project specifics
live here.

Two file kinds:

## Content stubs (root)

Markdown files inlined verbatim into skill bodies at documented
injection points. The skill loads them via:

```
!`cat .game-of-cards/<filename>.md 2>/dev/null || true`
```

If the file is absent or empty, the skill falls through to its
generic flow.

| Stub | Inlined into | What goes here |
|---|---|---|
| `canonical-tags.md` | `card-schema` skill (end of predicate table) AND parsed by `goc validate` to extend the canonical-tag enum | Project-specific tag predicates + a fenced YAML block listing the new tags (see existing file's header) |
| `config.yaml` | `goc attest` | Runtime-neutral closure attestation checks (`layer_2_project_dod`, `layer_3_goc_dod`) plus workflow options. Legacy `.claude/deck-config.yaml` is migrated here on upgrade. |
| `domain-vocabulary.md` | (reserved for project use) | Glossary of project-specific terms |
| `domain-examples.md` | (reserved for project use) | Concrete example card bodies for project-specific bug classes |
| `tooling-conventions.md` | `audit-deck` skill (Phase 2 brief, model-tier guidance) | Project tooling rules (e.g., `uv run` discipline, `model: "opus"` mandate, parallelization rules) |
| `documentation-conventions.md` | (reserved for project use) | Doc-style rules — STATUS.md vs SPEC.md split, per-doc consistency invariants |
| `file-path-map.md` | (reserved for project use) | Project filesystem map — where scripts/tests/docs live, what's gitignored |

## Workflow-hook stubs (`hooks/<skill>.md`)

Markdown instructions a goc-shipped skill follows at a defined
hook-point in its workflow. Same injection syntax as content stubs:

```
!`cat .game-of-cards/hooks/<skill>.md 2>/dev/null || true`
```

| Hook | Loaded by | Workflow point |
|---|---|---|
| `hooks/create-card.md` | `create-card` | Pre-decision-gate-raise consultation (when filing a card with a substantive decision at its core) |
| `hooks/decide-card.md` | `decide-card` | Agent-invoked decision contract (citation form for `--because`) |
| `hooks/finish-card.md` | `finish-card` | Step 2 closure-criteria audit AND Step 7 post-close action (status-dashboard refresh, changelog row, etc.) |
| `hooks/pull-card.md` | `pull-card` | Lazy-Andon trial: when a parked question can be resolved by a project rubric instead of raising the gate |
| `hooks/audit-deck.md` | `audit-deck` | Phase 0 priming reads + Phase 1 probe recipe + Phase 2 hunter roster |

## Per-file ownership and `goc upgrade` behavior

Files under this directory fall into three ownership categories,
each with a different upgrade contract:

| Category | Files | `goc upgrade` behavior |
|---|---|---|
| **user-owned** | the 6 content stubs (`canonical-tags.md`, `domain-vocabulary.md`, `domain-examples.md`, `file-path-map.md`, `tooling-conventions.md`, `documentation-conventions.md`) + `hooks/*.md` | absent → scaffold blank stub; identical to template → no-op; diverged → **preserve** (never overwrite authored content) |
| **evolving** | `README.md` (this file, the hook-point catalogue), `config.yaml` | same engine behavior — never overwrite — but the `upgrade` skill offers a 2-way reconcile so real upstream changes (new hook-points documented here, new config keys) can land where the user wants them |
| **goc-owned (managed elsewhere)** | the marker-bounded block in `AGENTS.md` / `CLAUDE.md` | regenerated wholesale on every upgrade (the contract is "do not edit between the markers") |

The engine guarantee is unconditional: `goc upgrade` never destroys
authored content under `.game-of-cards/`, with or without an agent
in the loop (`Skill(upgrade)` is the reconciliation pass; running
upgrade without it still preserves everything). See `Skill(upgrade)`
for the reconciliation contract.

## Authoring guidelines

- **Empty stub = generic flow.** The skills are designed so an empty
  hook file is a no-op; the consuming repo enables project-specific
  behavior by authoring content into the file.
- **Markdown only.** Hook files are inlined verbatim into skill
  bodies, which the agent reads as prompt text. Plain markdown
  works; YAML and code blocks are rendered as-is.
- **Header comment is for the human author, not the agent.** When
  the skill `!`cat`s the file, the header comment becomes part of
  the agent's prompt. Once the file is authored, replace the
  comment with real instructions.
- **Versioned in git, kept in the repo root.** `.game-of-cards/` is
  intentionally not gitignored. Project-specific GoC configuration
  is project content; it ships with the repo.
- **Sub-card 6 handles migration.** When phasor-agents migrates off
  the vendored `deck.py`, this directory will be authored from the
  audit catalogue (`deck/goc-package-pyproject-and-pypi-release/audit_catalogue.md`).
