## 2026-05-18T04:09:46Z: decision recorded

Use a Codex marketplace file in zauberzeug/game-of-cards as the Codex plugin distribution path, pointing at the repo-hosted codex-plugin payload — User approved the marketplace-file path; OpenAI's official Plugin Directory publishing is not self-serve yet, so repo-hosted marketplace distribution is the actionable official path now.. Gate session → none.

## 2026-05-18T05:32:28Z — Closure

- **What changed**: `goc.md` (new "Versioning and release" subsection under "Codex plugin"), `site/llms.txt` ("Install (Codex)" gains the `codex plugin marketplace update` recipe), and this card's Implementation summary records the publication target, lockstep versioning policy, release flow, and verification surface. No code changes were required — the Codex plugin payload, marketplace file, version-rewriter coverage, and parity tests landed with the `provide-codex-plugin-for-skills-and-hooks` epic.
- **Verification**: `uv run goc validate` clean; `uv run python -m pytest` → 131 passed, 4 subtests passed.
- **Audit**: PASS — no rubric configured; documentation closure (no project principle touched).
- **Project impact**: GoC ships a fourth first-class distribution channel (Codex repo-hosted marketplace), with version lockstep and CI-enforced parity matching the Claude Code and PyPI channels.
- **Tests**: 131 passed / 0 failed / 0 xfailed.
- **Bundled with**: n/a.

## Closure verification (2026-05-18T05:33:00Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — all 1 done
- [x] dod-100-percent — 7/7 ticked
- [x] log-md-closure-entry — '## 2026-05-18 — Closure' present
