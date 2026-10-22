## 2026-08-07T05:35:15Z: decision deliberation archived

Archived from the README's `## Decision required` section by `goc decide` before it was replaced with the resolved `## Decision` block — README is the dashboard, log.md is the journal. This preserves the options and recommendation that produced the decision below.

Three credible mechanisms, with different cost and different coverage. A human
needs to pick one so the children stop re-deriving it four ways:

1. **Shared predicates.** Export the per-field validity predicates from
   `validate_card` and have every writer call them. Cheapest; keeps the
   `ERROR:` + exit 2 CLI contract and precise per-flag messages. But it is
   opt-in — a new writer that forgets to call one reopens the family, exactly
   how we got here. This is what the two closed instances did locally.
2. **Validate the result at the write boundary.** Route every frontmatter write
   through one function that runs `validate_card` on the rendered text and
   refuses to write on error. Closes the family structurally — no writer can
   escape it. Costs a parse+validate per write, and turns precise input errors
   into generic "the resulting card would be invalid" messages unless writers
   *also* keep their own checks. Interacts with cards that are legitimately
   invalid mid-transition (drafts, `migrate`) and would need an escape hatch.
3. **Schema-driven per-field validators.** Move field rules into
   `goc/schema.yaml` as declarative constraints; generate both the validator and
   the writers' input checks from them. Best long-term fit with the open
   [support-custom-frontmatter-fields-with-enum-and-required-when-rules](../support-custom-frontmatter-fields-with-enum-and-required-when-rules/)
   work, and the only option that makes a *new field* automatically covered on
   both sides. Largest change, and it should probably not land independently of
   that card.

Sub-question regardless of choice: is the enforcement a runtime guard, a test
that enumerates verbs × fields, or both? A test alone cannot stop a consumer's
verb from corrupting their deck; a runtime guard alone leaves no signal at
review time. Note the open
[static-source-guards-never-prove-they-can-catch-an-offender](../static-source-guards-never-prove-they-can-catch-an-offender/)
card — whatever guard is chosen should be proven able to catch a planted
offender, or it will pass green while the family keeps growing.


## 2026-10-22T05:29:04Z: decision recorded

2. Validate the result at the write boundary: every frontmatter write goes through one function that runs validate_card on the rendered card and refuses to write on error, with an explicit escape hatch for drafts and migrate; enforced by both a runtime guard and a verbs x fields test proven to catch a planted offender — The maintainer chose the only option that closes the family structurally in a human session on 2026-10-22; writers may keep their precise per-flag checks for better messages, and the test must prove it can fail before its green run is trusted. Gate decision → none.

## 2026-10-22T05:29:32Z — Decision reconciled into the dashboard

- Recorded option 2 (validate the result at the write boundary) with both enforcement forms, as decided in the 2026-10-22 human session. DoD item 1 ticked; a MECHANICAL item for the boundary function and its draft/migrate escape hatch added; the TDD item now requires the planted-offender proof.
- README gains an "## Agreed mechanism" section, since `goc decide` archived the option catalogue here.
- No cascade: three children closed through point fixes earlier; the only open child, `worker-mapping-with-only-a-branch-emits-invalid-empty-who`, is left untouched because it is being handled with the worker-identity work split out of PR #11.
