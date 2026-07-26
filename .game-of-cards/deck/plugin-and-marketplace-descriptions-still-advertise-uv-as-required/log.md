## 2026-05-31T01:36:05Z — Closure

- **What changed**: `claude-plugin/.claude-plugin/plugin.json:3` and `.claude-plugin/marketplace.json:15` — replaced the stale "requires uv on host PATH" clause with "requires Python 3.10+ on host PATH" in both plugin descriptions. The wrapper at `claude-plugin/bin/goc` shells out via `python3 -m goc.cli` (commit 8d64a3f dropped uv), and AGENTS.md already documents Python 3.10+ as the only host prerequisite — the two description strings were the only remaining surfaces still advertising the old prerequisite.
- **Verification**: `grep -rn "requires uv" claude-plugin/ .claude-plugin/` returns no hits; `python scripts/sync_plugin_assets.py --check` prints `OK — plugin payloads + dogfood self-host copies match goc/ and goc/templates/ byte-for-byte.`
- **Audit**: PASS — no rubric configured; mechanical doc-string alignment.
- **Project impact**: marketplace-visible plugin description now matches the actual host prerequisite (Python 3.10+), removing a false-positive uv install requirement from the listing copy users see before installing.
- **Tests**: `python scripts/sync_plugin_assets.py --check` passes; no test suite runs for these JSON metadata files. `uv run goc validate` introduces no new errors (pre-existing deck errors unchanged, verified by comparing output with and without these edits).
- **Bundled with**: (none)

## Closure verification (2026-05-31T01:38:32Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-05-31 — Closure' present

## 2026-07-26 — Post-closure evidence: one surface was missed

- **Found**: `claude-plugin/README.md:7` still advertised the `uv` tool
  manager as the bundled CLI's runtime — a third surface carrying the
  same false prerequisite this card swept out of `plugin.json` and
  `marketplace.json`.
- **Why the closure check missed it**: the recorded verification was
  `grep -rn "requires uv" claude-plugin/ .claude-plugin/`. The surviving
  claim reads "runs via the `uv` tool manager" and has no `requires uv`
  substring. Lesson for prerequisite sweeps: grep the mechanism token,
  not one phrasing of the claim.
- **Follow-up**: [claude-code-plugin-readme-undercounts-its-skills-and-still-requires-uv](../claude-code-plugin-readme-undercounts-its-skills-and-still-requires-uv/)
  fixed the README and added `tests/test_plugin_readme_skill_catalogue_parity.py`.
- **This card's verdict is unchanged**: both surfaces it fixed remain correct.
