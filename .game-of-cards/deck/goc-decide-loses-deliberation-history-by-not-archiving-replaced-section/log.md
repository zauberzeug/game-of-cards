# Log

## 2026-05-23T05:06:53Z: Decision required (archived at filing)

Archived from README's `## Decision required` section before `goc decide` replaced it with the resolved `## Decision` block, so the deliberation (options + recommendation + trade-offs) survives the dashboard rewrite. Manual application of this card's own approved fix (Option A), per the workaround precedent in commit `674cc5e`.

Three credible scopes for the fix.

### Option A — `goc decide`-specific archival (minimum viable)

Modify `goc decide` in `goc/engine.py`: before replacing `## Decision required` in README, parse the existing section content and append a dated archive entry to log.md with the full prior content. Update `goc/templates/skills/decide-card/SKILL.md` "What this skill does to the card" to describe the dual-write behaviour.

Pros: narrow blast radius, single CLI command, single SKILL.md edit, easy to test. Lands the discipline where it bites today.

Cons: doesn't generalise. If `goc advance` or future commands also replace named README sections (e.g., a future `goc supersede-fix-proposal` that rewrites `## Fix`), they'll need bespoke archival logic.

### Option B — Generalised engine convention (broader fix)

Introduce a `goc archive-section <card> <section>` CLI helper that any command can call before rewriting a named README section. The helper:

1. Reads the named H2 section from `deck/<card>/README.md`.
2. Appends it to `deck/<card>/log.md` as a dated entry with a configurable header (e.g., `## <date>: <section-name> archived — <one-line reason>`).
3. Returns success so the caller can proceed with the README rewrite.

`goc decide` uses this helper for `## Decision required`. Future commands that replace named sections use the same helper.

Pros: generalises the README-dashboard / log.md-journal discipline to the whole engine. Single implementation, multiple callers. Establishes a pattern other tools can follow.

Cons: larger scope, larger test surface, adds a new public CLI verb. The current `goc decide` is the only confirmed caller — risk of over-engineering for a pattern that hasn't generalised yet.

### Option C — Skill-workflow-only fix (no engine change)

Update `goc/templates/skills/decide-card/SKILL.md` to instruct the agent to *manually* append the archive entry to log.md *before* running `goc decide`. No engine change.

Pros: smallest blast radius (one SKILL.md edit, no engine touch). Lands instantly via the next sync.

Cons: relies on agent discipline — easy to forget. The skill body becomes the enforcement surface, which contradicts the broader trend of moving discipline from skill-prose into engine-checks (see `goc validate`'s schema enforcement vs the prior "remember to check schema" prose discipline). The user feedback that surfaced this defect explicitly asked whether we could do better than relying on manual recovery — Option C is doing the same thing more carefully, not better.

### Option D — Defer

Wait for additional patterns of replaced-section-content loss before fixing. Risk: every `goc decide` call on every consuming repo continues to lose deliberation history. The manual workaround applied to the predecessor card is repeatable but adversarial — it requires the user (or agent) to notice the loss and remember to recover it.

### Recommendation

Option A. Minimum-viable fix that lands the discipline at the engine level for the one confirmed caller. Option B is the right shape if a second caller appears; defer the helper-extraction refactor until then.

## 2026-05-26T12:10:35Z: decision recorded

Option A — goc decide-specific archival. Modify goc decide in engine.py to append the prior Decision-required section content to log.md as a dated archive entry before replacing it in the README, and update the decide-card SKILL.md to document the dual-write behaviour (README replaced; log.md archives prior section AND records resolution). — Minimum-viable fix that lands the discipline at the engine level for the one confirmed caller; narrow blast radius and easy to test. The generalised archive-section helper (Option B) is deferred until a second section-replacing caller appears.. Gate decision → none.
