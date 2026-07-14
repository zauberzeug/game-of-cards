## 2026-07-14 — Filed, fixed, closed

Surfaced as the sole suite failure while verifying the codex hooks
upgrade fix on a macOS host. Root cause: GNU-only sed invocation as
GIT_SEQUENCE_EDITOR; BSD sed rejects `-i "1a break"`, the rebase never
pauses, setup asserts. Replaced with a portable Python todo editor
(temp-dir helper + sys.executable). Test green on macOS; guard
semantics untouched.
