## 2026-05-07: worker field migrated

Set worker: {who: "claude[bot]", where: main} — card was claimed before auto-populate existed; migrated by hand per DoD requirement.

## 2026-05-07: closed

Added `worker` optional field to schema.yaml; `Card.worker` property; `emit_frontmatter` dict handling; `validate_card` shape checks; `--worker` on `goc new`; `_auto_populate_worker` on `goc status active` with `--worker-who`/`--worker-where` overrides; `--worker`/`GOC_WORKER` filter on `cli` and `triage`; worker display in `render_table` (`-v`) and `render_board`; `render_json` worker field; `next-card` skill GOC_WORKER-aware queue line; CLAUDE.md + AGENTS.md + templates updated; both active cards migrated.
