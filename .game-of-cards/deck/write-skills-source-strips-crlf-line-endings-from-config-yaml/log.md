# Log

## 2026-06-23 — filed and closed (fix-through)

Surfaced during an audit pass when the autonomous pull queue was empty.
`_write_skills_source` (`goc/install.py`) read `.game-of-cards/config.yaml`
with `Path.read_text()` and wrote it back with `Path.write_text()`, so a
CRLF-authored config had every line rewritten to LF the first time
install/upgrade/mode-switch set `skills_source:`.

The closed card `install-marker-merge-rewrites-crlf-briefing-files-to-lf`
had already added `_read_text_keep_newline` / `_write_text_keep_newline`
and its DoD called for sweeping the other install/upgrade write-paths;
`_write_skills_source` was missed by that sweep.

Fix: route the two re-encoding calls through the existing helpers
(`_read_text_keep_newline` for the load, `_write_text_keep_newline` for
the store). The LF-normalized text keeps the existing regexes unchanged;
the detected newline is restored on write.

- reproduce.py: CR bytes before 4 / after 4 (was 0 before the fix), exit 0.
- Added two regression tests to `tests/test_install.py`
  (`test_write_skills_source_preserves_crlf_line_endings`,
  `test_write_skills_source_lf_config_stays_lf`).
- Plugin mirrors (`claude-plugin`, `codex-plugin`, `openclaw-plugin`)
  re-synced via `scripts/sync_plugin_assets.py`.
- Full suite green (546 tests); `goc validate` clean.
