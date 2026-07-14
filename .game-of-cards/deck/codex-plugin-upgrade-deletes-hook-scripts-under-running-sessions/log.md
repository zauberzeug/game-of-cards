## 2026-07-14 — Filed, fixed, closed

Live incident: the 0.0.26→0.0.27 Codex plugin upgrade deleted the
versioned cache dir under a running session; every hook fire ENOENTed.
Immediate repair: compat symlink 0.0.26→0.0.27 in the machine's Codex
cache (router verified exit 0 at the old path). Durable fix: rewrote all
three commands in codex-plugin/hooks/hooks.json as self-healing sh
fallbacks that resolve the newest surviving install by mtime when the
session's PLUGIN_ROOT vanished. reproduce.py red (6/6 failing) before
the rewrite, green after; regression coverage added in
tests/test_codex_hooks_survive_upgrade.py (5 tests, both substitution
models, mtime-beats-lexical, loud failure when nothing survives).
Claude Code needs no equivalent — it retains in-use version dirs via
.in_use PID markers. Full suite green except the unrelated pre-existing
macOS sed portability failure in test_git_auto_commit_rebase_guard,
tracked separately.
