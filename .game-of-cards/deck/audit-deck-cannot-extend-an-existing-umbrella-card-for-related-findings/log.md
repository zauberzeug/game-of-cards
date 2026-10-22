## 2026-05-28T04:01:37Z: decision deliberation archived

Archived from the README's `## Decision required` section by `goc decide` before it was replaced with the resolved `## Decision` block — README is the dashboard, log.md is the journal. This preserves the options and recommendation that produced the decision below.

### 1. Trigger condition — when does audit-deck *extend* vs. file fresh?

Options:

- **Manual.** Audit-deck always files fresh; humans (or a separate hygiene pass) periodically consolidate sibling cards. Status quo + an after-the-fact merge tool.
- **Tag-driven.** When a finding's primary tag (`yaml-lite`, `frontmatter-emitter`, etc.) matches an open card with the same tag, extend that card. Requires either canonical area tags or a derived "subject" from the title.
- **Same-file heuristic.** When the finding's cited file path overlaps with an open card's cited file path (`goc/engine.py` regions), extend.
- **Explicit umbrella tag.** A card tagged `umbrella: yaml-lite-roundtrip` is the auto-target for any new finding tagged `yaml-lite-roundtrip`. The umbrella is opt-in; first finding files fresh, subsequent ones append.

The fourth option scales best (explicit intent, no false matches), at the cost of requiring the first finding's author to mark the umbrella.

### 2. Append mechanism — engine verb vs. body edit

Options:

- **`goc append-dod <slug> "<text>"`** — engine verb that mutates the frontmatter `definition_of_done` block, preserving format and ordering invariants. Auto-commits per workflow.auto_commit.
- **Direct file write** — the skill writes to the README and reformats. Simpler, but loses the schema-aware safety the engine provides for other frontmatter mutations.

### 3. Closure semantics — when does an umbrella close?

Options:

- **All-DoD-ticked.** Standard: every appended item must be ticked. Works for finite umbrellas (a known set of issues to find), risky for open-ended ones (the umbrella may never close as new findings land).
- **Time-boxed.** Umbrella closes when its DoD has been stable (no new appends) for N days, even if some items are unticked-but-explicitly-deferred. Requires a `deferred: <reason>` marker on individual items.
- **Manual mark-finite.** A `--finalize` verb freezes the DoD; further appends are rejected. Closer pattern to current cards; relies on the closer to make the call.


## 2026-10-22T05:27:51Z: decision recorded

Trigger: Explicit umbrella tag. Append: goc append-dod <slug> "<text>". Closure: All-DoD-ticked. — The maintainer answered the three design questions in a human session on 2026-10-22: an opt-in umbrella marker gives explicit intent without false matches, the engine verb keeps DoD appends schema-safe like the other frontmatter writers, and an umbrella closes like every other card once each appended item is ticked, accepting the open-ended-umbrella risk the card notes. Gate session → none.
