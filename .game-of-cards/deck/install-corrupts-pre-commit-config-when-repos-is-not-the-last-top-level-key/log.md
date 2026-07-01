## 2026-07-01 — Scope broadened: two more broken config shapes (audit-deck)

An empty-queue `pull-card` → `audit-deck` pass surfaced two additional
input shapes that `_append_precommit_hook` corrupts, both distinct from
the original "top-level key after `repos:`" case and both confirmed
empirically:

- **Empty inline list `repos: []`** — `repos:` is the last/only key but
  inline; appending an indented block-sequence item under it is invalid
  YAML.
- **No `repos:` key at all** (e.g. a config with only `ci:`) — appending
  a block-sequence item to a pure mapping is invalid YAML.

Root cause is identical to the filed case (naive `text + PRE_COMMIT_HOOK`
append assuming a block-style `repos:` list at the file tail), so this
was folded into the existing card rather than filed separately — a
second `decision`-gated card would fragment one mechanism decision.

Decision-relevant consequence recorded in `## Decision required`: fix
option (2) "structured-text splice (find `repos:` block end)" as
literally worded handles only the original shape; it cannot splice into
`repos: []` or an absent `repos:`, so the chosen mechanism must also
rewrite `repos: []` → block list and add a `repos:` block when none
exists.

Also refreshed stale code references (`install.py:941` → `1320`;
callsites `1176` → `1571` and `1818`) and rewrote `reproduce.py` to
exercise all three broken shapes plus the block-form happy-path control.
`reproduce.py` prints `DEFECT REPRODUCED` for `key-after-repos`,
`empty-inline-repos`, and `no-repos-key`, and exits 1 (verified under
both `uv run python` — PyYAML-absent structural path — and system
`python3` — PyYAML parse path). Card stays `open`, `human_gate:
decision`; no code change to the engine.
