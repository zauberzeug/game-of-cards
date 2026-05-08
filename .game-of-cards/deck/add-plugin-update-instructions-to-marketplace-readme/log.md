## 2026-05-08 — Closure

Two consumer-facing doc edits in lockstep:

- `claude-plugin/README.md` — added an "Updating an existing install" section between "Install" and "First use" with the canonical `/plugin marketplace update` + `/plugin install` sequence and the `marketplace remove`+`add` round-trip as a fallback. Also added the missing second line of the install snippet (`/plugin install game-of-cards@game-of-cards`) for symmetry.
- `site/llms.txt` — line 52 changed from "bootstrap any repo with" / `/bootstrap` to "kick off any repo with" / `/kickoff` to match today's skill rename.

Verified manually by Rodja's smoke test earlier in the session: after `/plugin marketplace update` the renamed skill names `Skill(kickoff)` / `Skill(audit-deck)` were live in the running plugin, confirming the refresh idiom is the right remediation.

## Closure verification (2026-05-08)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — all 2 done
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-05-08 — Closure' present
