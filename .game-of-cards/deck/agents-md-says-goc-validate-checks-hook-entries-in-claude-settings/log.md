## 2026-10-07T04:53:19Z — Closure

- **What changed**: `AGENTS.md` (§ "Skill and hook files have two copies", the
  `.claude/settings.json` paragraph). The "and `goc validate` enforces the
  parity" clause is gone. The paragraph now says the file is not one of the three
  hook registries `goc validate` covers, so a dropped or repointed goc-owned
  registration passes it. It says a vendored-mode `goc upgrade` re-adds every
  missing `GOC_CLAUDE_HOOKS` entry, even at the same version, and that a
  repointed entry stays behind, linking
  `goc-upgrade-leaves-stale-prior-version-hook-registrations-in-claude-settings`.
  New guard `tests/test_claude_settings_hook_edit_claims.py`
  (`ClaudeSettingsHookEditClaimsTest`, 3 tests) checks each clause both ways
  against a scratch install. Added `reproduce.py`.
  Deck: post-close pointer on the origin card
  `agents-md-mislabels-claude-settings-json-as-user-owned-permission-list`
  (README and log). This card and the origin now advance
  `doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them`;
  the origin had called itself an instance but had no edge. That card gets two
  table rows and a paragraph for this instance.
- **Verification**: `reproduce.py` went from exit 1 to exit 0. `goc validate` exits 0 on
  the hand edit both before and after (hypothesis confirmed, not disproved). The
  new guard reports 4 problems across all 3 checks against `AGENTS.md` at the
  pre-fix `HEAD`, and 0 against the fix. `uv run goc validate` is clean (no new
  WARN). `scripts/sync_plugin_assets.py --check` OK; the card-language and
  card-YAML guards are clean (795 cards).
- **Audit**: no rubric configured; mechanical fix
- **Project impact**: n/a
- **Tests**: 1242 passed / 0 failed / 0 xfailed

## Closure verification (2026-10-07T04:53:21Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-10-07 — Closure' present
