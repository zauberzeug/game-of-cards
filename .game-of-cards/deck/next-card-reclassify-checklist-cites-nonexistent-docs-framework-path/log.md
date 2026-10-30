## 2026-10-30T04:56:00Z — Proposed DoD fenced

Wrapped the body's "definition_of_done (replace after decision)" list in a code
fence, with the content unchanged. Unfenced, its five lines read as a frontmatter
DoD at the block indent, which the new `goc validate` warning
`BODY_REPEATS_FRONTMATTER` reports
(goc-validate-accepts-a-card-body-that-carries-a-second-copy-of-the-frontmatter).
The fence marks the list as the proposal it is. The decision and the gate are
untouched.
