# Log

## 2026-05-23T05:07:26Z: Decision required (archived at filing)

Archived from README's `## Decision required` section before `goc decide` replaced it with the resolved `## Decision` block, so the deliberation (reasoning + options + recommendation + trade-offs) survives the dashboard rewrite. Manual application of the `goc-decide-loses-deliberation-history-by-not-archiving-replaced-section` fix (Option A), per the workaround precedent in commit `674cc5e`.

### Reasoning

Three coupled sub-decisions need a single human pick before mechanical implementation is safe:

1. **Tag format on the DoD line.** Bracketed prefix `[TDD] ` is parseable and visually distinct but introduces a second pair of square brackets adjacent to the existing checkbox brackets (`- [ ] [TDD] ...`), which can hurt readability and confuse the line-anchored regex. Colon-suffix prefix `TDD: ` reads more naturally and avoids the bracket-collision, but is slightly less greppable.
2. **Taxonomy size.** The proposal names four classes. XP-style **SPIKE** items (exploratory work whose "done" is "I understand X enough to file the next card") arguably belong as a fifth class — they share MECHANICAL's inspection-verifiable closure but have a fundamentally different cognitive shape (exploration with no falsifier vs edit with a known target). Folding SPIKE into MECHANICAL loses the distinction; promoting it adds vocabulary surface.
3. **Validator scope.** Strict line-anchored regex `^- \[[ x]\] \[(TDD|...)\] ` makes the discipline mechanically enforceable but rejects future format variants. Lenient any-position match is more flexible but admits drift.

Without a human go/no-go on these three, mechanical implementation could land a format that needs reworking across every existing card the moment it ships.

### Option A — Four classes, `[TDD]` bracket prefix, line-anchored validator

Adopt the proposal as drafted.

**Pros:**
- Minimal surface (one SKILL.md section, ~40 LOC validator change).
- Bracket prefix is greppable: `grep '^- \[[ x]\] \[EMPIRICAL\]' deck/*/README.md` enumerates every empirical DoD item.
- Line-anchored regex matches the existing DoD-detection predicate (`^- \[[ x]\]` at `engine.py:493`), keeping parser conventions uniform.

**Cons:**
- Double-brackets at line start (`- [ ] [TDD] ...`) is visually noisy.
- Four classes may under-serve exploratory SPIKE-shape work, forcing such items to wear `[MECHANICAL]` against semantics.

**File:line preview:**
- `goc/templates/skills/card-schema/SKILL.md:328` — insert new `### DoD method tags` subsection between `### Layer-1 format` (ends line 327) and `## Relationship fields` (starts line 329).
- `goc/templates/skills/create-card/SKILL.md:194` — update the example DoD block to use the four bracketed prefixes.
- `goc/engine.py:1119` — extend `compute_blocker_warnings` with a fourth `BlockerWarning` class that scans each card's parsed DoD lines and emits `UNTAGGED_DOD_ITEM` for any `- [ ]`/`- [x]` not matching `\[(TDD|EMPIRICAL|MECHANICAL|PROCESS)\]`.

### Option B — Four classes, `TDD:` colon-suffix prefix, line-anchored validator

Same vocabulary and validator scope as Option A; tag rendered as `TDD: ` at the start of each DoD criterion: `- [ ] TDD: reproduce.py exits zero`.

**Pros:**
- Cleaner visual: no bracket-on-bracket collision.
- Reads as natural-language: "TDD: the assertion holds" mirrors spoken framing.
- Regex stays simple: `^- \[[ x]\] (TDD|EMPIRICAL|MECHANICAL|PROCESS): `.

**Cons:**
- Slightly less greppable than brackets (colon is a common character).
- Breaks symmetry if the deck later adopts other `[bracket]` metadata conventions.

**File:line preview:** Same surfaces as Option A; only the rendered tag format differs.

### Option C — Reject the proposal

Leave the DoD as-is. Document the empirical-vs-assertion distinction informally in body prose of cards that mix the two, rather than in the schema.

**Pros:**
- Zero migration cost forever; no validator surface to maintain.
- Preserves the principle that DoD is a free-text contract — formatting discipline lives in author convention, not schema enforcement.
- Avoids the future-fork risk of having to extend the taxonomy (SPIKE, SECURITY, PERF, …) once the four classes are baked in.

**Cons:**
- Loses the most consequential discipline-clarification: empirical items continue to read as must-pass assertions, perpetuating the false-incompletion failure mode.
- Downstream repos keep maintaining duplicate prose; the next consuming repo re-derives the discipline from scratch.
- The validator-warning surface is exactly the kind of low-stakes mechanical reminder GoC is well-suited to ship (cf. `STALE_BLOCKED`).

**File:line preview:** No code change; doc-only revision to `card-schema` SKILL.md noting the four-class informal discipline as guidance without enforcement.

### Recommendation

**Option B (four classes, colon-suffix `TDD:` prefix)**, with the SPIKE sub-question deferred to a follow-up card filed once the four-class shape has been lived with for ~10 new cards. Dominant pro: the colon-suffix avoids the double-bracket visual noise without losing greppability, and the four-class baseline is a strictly-smaller-and-safer adoption surface than the five-class variant. Validator scope: line-anchored, matching the existing DoD-detection predicate.

## 2026-05-26T12:10:35Z: decision recorded

Option B — four method classes (TDD / EMPIRICAL / MECHANICAL / PROCESS) with a colon-suffix prefix on each DoD line (e.g. TDD: ...), plus a line-anchored validator emitting a warning-only UNTAGGED_DOD_ITEM. The SPIKE fifth class is deferred to a follow-up card filed once the four-class shape has been lived with for about 10 new cards. — The colon-suffix avoids the double-bracket visual noise next to the checkbox without losing greppability, and the four-class baseline is a strictly-smaller-and-safer adoption surface than the five-class variant. Line-anchored validator scope matches the existing DoD-detection predicate.. Gate decision → none.

## 2026-05-26T00:00:00Z — Closure

- **What changed**: `goc/engine.py` — added `DOD_METHOD_TAGS` + `DOD_TAGGED_BOX`/`DOD_ANY_BOX` regexes, `untagged_dod_items()` helper, and `validate_dod_method_tags()` emitting warning-only `UNTAGGED_DOD_ITEM` for non-terminal cards whose DoD checkboxes lack a `TDD:`/`EMPIRICAL:`/`MECHANICAL:`/`PROCESS:` prefix. Advisory warnings reordered before the structural-error block so the repair-edges hint stays last. `card-schema` SKILL.md gained a `### DoD method tags` subsection; `create-card` Step 5 example DoD demonstrates the convention. Plugin mirrors + OpenClaw port re-synced.
- **Verification**: `goc validate` exits 0 (warnings are advisory); 152/152 unittest suite passes including 3 new UNTAGGED_DOD_ITEM tests; sync-plugin-assets `--check` and openclaw port `--check` both clean.
- **Audit**: PASS — no rubric configured; mechanical fix (warning-only validator + doc subsection, no breaking change).
- **Project impact**: n/a
- **Tests**: 152 passed / 0 failed / 0 xfailed
- **Bundled with**: n/a

## Closure verification (2026-05-26T20:11:10Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-05-26 — Closure' present
