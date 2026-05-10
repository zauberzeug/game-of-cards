# Log

## Closure 2026-05-10

Templates slimmed; reference content folded into skill bodies that
already auto-invoke at the moment of acting.

**Token-cost A/B (template baseline):**

| File | Before | After | Reduction |
|---|---|---|---|
| `AGENTS_GOC.md` | 132 lines / 6882 B | 22 lines / 1069 B | -84% / -85% |
| `CLAUDE_GOC.md` | 105 lines / 5190 B | 15 lines /  484 B | -86% / -91% |
| **Total**       | **237 / 12072 B** | **37 / 1553 B**   | **-84% / -87%** |

The 87% byte reduction beats the ~80% goal in the card body. CLAUDE.md
benefits twice: its own block shrank, AND the `@AGENTS.md` import
loads a smaller AGENTS.md.

**Content moves (no information lost):**

- Three operating modes (session / autonomous / Andon-cord), with
  procedural step-list and no-card exceptions → `Skill(deck)` body
  under "What this looks like in practice".
- Daily verb table → `Skill(deck)` body under "Daily CLI verbs".
- YAML format rules — already lived in `Skill(card-schema)`; removed
  the duplicate from root.
- `worker` field semantics → `Skill(advance-card)` body under
  "Worker field — populated at claim time" (claim-time is when worker
  auto-populates).
- "What lives where" (project state vs runtime affordances) → 
  `Skill(kickoff)` body under "Reference: what gets installed".
- Worktrees → `Skill(kickoff)` body under "Reference: worktrees".
- Multi-team coordination opt-ins → `Skill(kickoff)` body under
  "Reference: multi-team coordination opt-ins".
- Plugin install (one-time per machine) → root retains the install
  one-liner; the longer pipx alternative already lived in
  `Skill(claude-kickoff)`.
- First-use kickoff guidance — already lived in `Skill(kickoff)` and
  `Skill(claude-kickoff)`; removed the duplicate from root.
- Skill surface listing (12 verbs) — Claude Code's skill registry
  already enumerates them; removed.
- Runtime hooks table → `Skill(claude-kickoff)` body under "Reference:
  runtime hooks".

**Migration:** existing repos pick up the slimmer block on the next
`goc upgrade` — the marker-bounded merge in `_append_marker_block`
rewrites only the content between markers, preserving user content
above and below.

**Plugin payload:** `scripts/sync_plugin_assets.py` re-synced the
Claude plugin templates and `scripts/port_skills_to_openclaw.py`
re-ported the OpenClaw skill bodies (15 ported; `claude-kickoff`
remains a host-specific complement).

**Smoke test:** fresh empty repo + `git init` + `goc install` +
`goc new test-card` + `goc` (queue listing) all succeed without
consulting any root-level documentation. The agent has the verbs
through `Skill(deck)` and the schema through `Skill(card-schema)`.

**Side fix (separate from the main scope but unblocked pre-commit):**
the `auto-publish-npm-and-clawhub-on-tag-push` card had two
half-edges — its `advances` listed `publish-openclaw-plugin` and
`provide-openclaw-plugin-for-skills-and-hooks`, but neither target
carried the inverse `advanced_by` entry. Added the missing entries
on both targets so `goc validate` passes.
