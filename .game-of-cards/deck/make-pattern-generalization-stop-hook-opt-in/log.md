# Log

## 2026-06-26 — closed (implemented)

Flipped the pattern-generalization Stop hook from default-on (opt-out) to
default-off (opt-in), per the user decision recorded in the README.

**Surfaces changed:**

- `goc/templates/hooks/pattern_generalization_check.py` — `_opted_out` →
  `_enabled`; regex unchanged but interpretation inverted (`group == "true"`
  enables; absent config / absent key / any other value → disabled). Call
  site flipped to `if not _enabled(...)`. Docstring rewritten opt-out → opt-in.
- `goc/templates/game_of_cards/config.yaml` — `pattern_generalization_check:
  false` with a "set true to enable" comment explaining the per-turn blocking cost.
- `openclaw-plugin/index.ts` — `isOptedOut` → `isEnabled` (regex matches
  `…: true`); the `agent_end` guard now runs only when the file enables it
  OR `ctx.config.pattern_generalization_check === true`. The host-level
  `allowConversationAccess` gate is untouched (separate concern).
- Docs — `claude-kickoff/SKILL.md` row + `claude-plugin/README.md` and
  `openclaw-plugin/README.md` hook tables reworded to "off by default; opt-in".
  (codex-kickoff / codex-plugin mentions are bare hook-name lists that assert
  no default, so left as-is.)
- `tests/test_pattern_generalization_hook.py` — new `OptInDefaultTest` (7
  cases): four on the `_enabled` gate (absent config, absent key, explicit
  false, explicit true) and three on `main()` end-to-end (no-op exit 0 when
  disabled/absent even on a code-mutating turn; exit 2 + reminder on stderr
  when enabled).

**Scope note:** the two open cards
`pattern-generalization-opt-out-regex-matches-anywhere-in-the-file` and
`pattern-generalization-opt-out-regex-misses-quoted-yaml-values` describe
parsing-robustness defects in the *same* regex. They were intentionally NOT
folded in (orthogonal to polarity; the inverted check is no less robust than
before and leaves them a clean surface). The user opted to keep this change
minimal rather than batch them.

**Non-breaking:** repos that already wrote `pattern_generalization_check:
true` (including this repo's own `.game-of-cards/config.yaml`) keep the hook
on. Only new installs and key-absent repos go quiet.

**Verification:** `tests.test_pattern_generalization_hook` 30/30 green;
`sync_plugin_assets.py --check` and `port_skills_to_openclaw.py --check` both
clean; `goc validate` clean (pre-existing UNTAGGED_DOD_ITEM WARNs on unrelated
cards only). Full `unittest discover` is green except one pre-existing
macOS-local failure in `test_git_auto_commit_rebase_guard` whose *setup*
needs a paused `git rebase -i` (blocked in this sandbox; GNU-`sed`/Linux-only
in practice) — it fails at the setup assertion before exercising any product
code and is independent of this change.

**Observed during work (not filed):** on this machine the Stop hook
double-fired — once from `${CLAUDE_PLUGIN_ROOT}/hooks/` (installed plugin,
older reminder text) and once from `${CLAUDE_PROJECT_DIR}/.claude/hooks/`
(vendored copy, newer text). That's a plugin+vendored coexistence / version
drift symptom, separate from this card; surfaced to the user for a possible
follow-up.
