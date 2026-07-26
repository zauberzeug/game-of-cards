---
title: claude-code-plugin-readme-undercounts-its-skills-and-still-requires-uv
summary: "`claude-plugin/README.md` is the payload README a consumer reads in Claude Code's plugin browser, and it misdescribes the payload it ships: it claims \"14 skills\" and lists 14 table rows while `claude-plugin/skills/` ships 16 (`claude-kickoff` and `upgrade` are missing), and its intro still says the bundled CLI \"runs via the `uv` tool manager\" — contradicted three lines later by its own Install section, by `claude-plugin/bin/goc`, and by AGENTS.md. The `uv` clause is the surface that plugin-and-marketplace-descriptions-still-advertise-uv-as-required missed when it swept the same false prerequisite out of plugin.json and marketplace.json."
status: open
stage: null
contribution: high
created: "2026-07-26T18:45:37Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [documentation, infra]
draft: true
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero — every README claim agrees with the shipped payload
  - [ ] TDD: a regression test in `tests/` pins `claude-plugin/README.md`'s skill catalogue (bold count, table rows, prose restatement) to `claude-plugin/skills/`, so the next added skill fails CI instead of rotting the README
  - [ ] MECHANICAL: the catalogue table gains `claude-kickoff` and `upgrade` rows, and both count claims read 16
  - [ ] MECHANICAL: the intro's "`uv` tool manager" clause is replaced with the true runtime (`python3`), so the intro, Install, and Requirements sections agree
  - [ ] PROCESS: [plugin-and-marketplace-descriptions-still-advertise-uv-as-required](../plugin-and-marketplace-descriptions-still-advertise-uv-as-required/) amended with a forward pointer to this card (post-closure evidence: its sweep missed a third surface)
  - [ ] PROCESS: `uv run goc validate` clean; `uv run python -m unittest discover -s tests` green; `python scripts/sync_plugin_assets.py --check` green
---

# Claude Code plugin README undercounts its skills and still requires `uv`

## Location

- [`claude-plugin/README.md:11`](../../../claude-plugin/README.md) — `**14 skills**` count claim.
- [`claude-plugin/README.md:13-28`](../../../claude-plugin/README.md) — the catalogue table: 14 rows.
- [`claude-plugin/README.md:85-86`](../../../claude-plugin/README.md) — "all 14 skills are immediately available."
- [`claude-plugin/README.md:5-7`](../../../claude-plugin/README.md) — "the GoC CLI is bundled and runs via the `uv` tool manager".
- Ground truth for the catalogue: `claude-plugin/skills/` (16 directories).
- Ground truth for the runtime: [`claude-plugin/bin/goc:26`](../../../claude-plugin/bin/goc).

## What's broken

Two independent claim clusters in one consumer-facing file disagree
with the payload the file describes.

### 1. The skill catalogue is two skills short

`claude-plugin/README.md:11`:

```markdown
**14 skills** — invoked as `/skill-name` or `Skill(name)` inside Claude Code:
```

followed by a 14-row table, and restated at line 85:

```markdown
Kickoff will introduce GoC, ask which working style fits your project
(solo / team / OSS-eval / agent-runtime), and scaffold the
`.game-of-cards/` project state directory. Once it completes, all 14
skills are immediately available.
```

`claude-plugin/skills/` ships **16**. The two absent from every count
and from the table are:

| Skill | Shipped since | Description (from its `SKILL.md`) |
|---|---|---|
| `claude-kickoff` | `b30853e6`, 2026-05-09 | Claude Code-specific complement to kickoff — `Bash(goc:*)` permission grant, `/plugin install` cadence, CLAUDE.md merge prompts |
| `upgrade` | `f76dace6`, 2026-05-30 | Run `goc upgrade`, then drive LLM reconciliation of evolving `.game-of-cards/` files from the engine's divergence report |

Neither was ever added to the table, so the count has been wrong since
2026-05-09 and wrong by two since 2026-05-30. The payload set is not
hand-maintained — `scripts/sync_plugin_assets.py` derives it from
`goc/templates/skills/` filtered by `skill_for_agent(name, "claude")`
(`goc/install.py:1166`), which is exactly why adding a skill silently
widens the gap: the tree grows, the prose does not.

Both omissions are load-bearing for a reader. `upgrade` is the only
documented path for re-syncing an existing install's project state, and
`claude-kickoff` is the Claude-specific half of onboarding — the skill
that grants the `Bash(goc:*)` permission without which the bundled CLI
cannot be called at all.

### 2. The intro still advertises `uv` as the CLI runtime

`claude-plugin/README.md:5-7`:

```markdown
This plugin delivers the full GoC
skill and hook set to Claude Code in a single install step. No separate
package installation is required — the GoC CLI is bundled and runs via
the `uv` tool manager that ships with most developer environments.
```

Three sources contradict this, including the same file:

- `claude-plugin/README.md:45-47` (Install): "The plugin is
  self-contained — no `pip install`, `pipx install`, or `uv` required.
  The bundled engine is pure-stdlib Python and runs via the `python3`
  already on your PATH."
- `claude-plugin/README.md:94` (Requirements): "Python 3.10+ on host
  `PATH` (as `python3` or `python`)".
- `claude-plugin/bin/goc:26` — the actual wrapper:

  ```bash
  exec env PYTHONPATH="${PLUGIN_ROOT}:${PYTHONPATH:-}" "$PYTHON" -m goc.cli "$@"
  ```

  with its own header comment: "No venv, no uv, no first-call latency."
- AGENTS.md § "Plugin runs goc from a vendored engine — Python 3.10+ is
  the only host prerequisite".

The drift has a precise origin. Commit `8d64a3fb` ("feat: drop uv from
plugin wrapper; python3 -m goc.cli is now the entry point", 2026-05-09)
rewrote this README's Install and Requirements sections — its diff hunk
header is literally `@@ -42,10 +42,9 @@ the \`uv\` tool manager that ships
with most developer environments.`, i.e. the stale intro sentence sat in
the context lines of the very patch that corrected the other two
sections, and was left untouched.

## Empirical evidence

`reproduce.py` derives both ground truths from the tree and checks every
claim against them:

```
$ uv run python .game-of-cards/deck/claude-code-plugin-readme-undercounts-its-skills-and-still-requires-uv/reproduce.py
=== 1. skill catalogue ===
shipped under claude-plugin/skills/ : 16
rows in README catalogue table      : 14
shipped but not catalogued          : ['claude-kickoff', 'upgrade']
catalogued but not shipped          : []
bold count claim                    : 14
prose count restatement             : 14

=== 2. host prerequisite ===
bin/goc actually shells out via uv  : False
README:7: the `uv` tool manager that ships with most developer environments.

[FAIL] 4 claim(s) drifted from the shipped payload:
  - catalogue table disagrees with claude-plugin/skills/ (missing=['claude-kickoff', 'upgrade'], extra=[])
  - README claims **14 skills**, payload ships 16
  - README's 'all 14 skills are immediately available' restates a count the payload contradicts (16)
  - README intro advertises the `uv` tool manager as the CLI's runtime, but claude-plugin/bin/goc execs `python3 -m goc.cli` (no uv)
EXIT=1
```

Sibling surfaces are clean, so this is a single-file defect, not a
family: `goc.md:89` already says "**16 GoC skills**", and
`openclaw-plugin/README.md:25` already says "**16 skills**".
`codex-plugin/README.md` ships no catalogue table at all.

## Why it matters

1. **Reachability — this file IS the consumer-facing listing.** Claude
   Code's marketplace install extracts the `source: ./claude-plugin`
   subtree, so `claude-plugin/README.md` is the README a prospective
   installer reads in the plugin browser. No agent, no engine code path,
   and no test reads it; a human deciding whether to install does. That
   makes it the one doc surface in the repo whose only consumer is
   someone with no other source of truth.

2. **The `uv` claim reintroduces the exact false prerequisite a closed
   card swept out.**
   [plugin-and-marketplace-descriptions-still-advertise-uv-as-required](../plugin-and-marketplace-descriptions-still-advertise-uv-as-required/)
   (done 2026-05-31) fixed `plugin.json` and `marketplace.json` on the
   grounds that a false prerequisite makes a reader "either install uv
   unnecessarily (waste) or skip the plugin entirely (lost install)".
   That card's body asserts `8d64a3f` "only touched `bin/goc`,
   `claude-plugin/README.md`, and `CLAUDE.md`" — treating this README as
   already-fixed. It was fixed in two of its three places. This is
   post-closure evidence on that card, so its README needs a forward
   pointer here (`Skill(finish-card)` § "After closure").

3. **A missing `upgrade` row hides the only re-sync path.** A plugin
   user who never learns `Skill(upgrade)` exists has no documented way
   to reconcile an existing `.game-of-cards/` against new templates.

4. **The listing is a pending deliverable.** The active card
   [list-game-of-cards-on-anthropic-community-marketplace](../list-game-of-cards-on-anthropic-community-marketplace/)
   submits this plugin to Anthropic's community marketplace; its own
   `submission-draft.md:16` already carries the same "14 skills" figure.
   Shipping the submission with a wrong payload description is a
   first-impression cost that is free to avoid now.

5. **No guard exists.** `tests/test_readme_hook_catalogue_parity.py`
   pins the deck README's workflow-hook table to the shipped
   `hooks/*.md` set for precisely this failure mode — but nothing does
   the equivalent for the plugin README's skill table. This is the
   eighth-plus instance of the unguarded-doc-claim shape catalogued on
   [doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them](../doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them/);
   that card owns the architectural sweep decision. This card fixes the
   one instance and adds the one guard, following the
   `test_readme_hook_catalogue_parity.py` pattern — it does not
   pre-empt the architectural pick.

## Fix

All edits in `claude-plugin/README.md` (not auto-synced —
`scripts/sync_plugin_assets.py` explicitly excludes it, per AGENTS.md
§ "Plugin assets are auto-synced").

1. Line 11: `**14 skills**` → `**16 skills**`.
2. Insert two table rows, keeping the table's existing
   onboarding-then-workflow-then-reference order:
   - `| \`claude-kickoff\` | Claude Code specifics — \`Bash(goc:*)\` grant, plugin install cadence, CLAUDE.md merge |`
     after the `kickoff` row.
   - `| \`upgrade\` | Re-sync templates and reconcile evolving \`.game-of-cards/\` files |`
     near the `deck` / `card-schema` reference rows.
3. Line 85-86: "all 14 skills" → "all 16 skills".
4. Line 5-7: replace the `uv` clause so the intro matches the Install
   section, e.g. "the GoC CLI is bundled and runs on the `python3`
   already on your PATH."
5. Add `tests/test_plugin_readme_skill_catalogue_parity.py` modelled on
   `tests/test_readme_hook_catalogue_parity.py`: derive the shipped set
   from `claude-plugin/skills/*/SKILL.md`, assert it equals the table's
   first-cell slugs, and assert both numeric claims equal its size.

## Dedup

- [plugin-and-marketplace-descriptions-still-advertise-uv-as-required](../plugin-and-marketplace-descriptions-still-advertise-uv-as-required/)
  (done 2026-05-31) — same false prerequisite, different surfaces
  (`plugin.json`, `marketplace.json`). This card is the third surface it
  missed, plus an unrelated catalogue drift.
- [cli-reference-plugin-sections-describe-a-payload-goc-no-longer-ships](../cli-reference-plugin-sections-describe-a-payload-goc-no-longer-ships/)
  (done) — same defect shape (a doc describing a stale payload) in
  `goc.md`. It corrected `goc.md` to "16 GoC skills" and did not touch
  `claude-plugin/README.md`.
- [add-plugin-update-instructions-to-marketplace-readme](../add-plugin-update-instructions-to-marketplace-readme/)
  (done) — added this README's "Updating an existing install" section;
  did not revisit the catalogue or the intro.
- [doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them](../doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them/)
  (open, `decision`) — the architectural meta-fix for the unguarded-claim
  family. Governing cluster, so no edge is wired; this card is one
  instance of the evidence it governs.
- No `disproved` card cites `claude-plugin/README.md`, the skill count,
  or the catalogue.
