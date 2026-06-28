## 2026-06-22 — closed (done)

Surfaced during an audit-deck pass (queue was empty) and fixed through in
the same session.

**Root cause.** `_auto_populate_worker` resolved `where` with precedence
`flag → git-detection` only, never consulting the existing value (unlike
`who`, which is `flag → existing → git-config`). When no `--worker-where`
flag was given and git yielded no usable branch (detached HEAD / fresh
checkout → `git rev-parse --abbrev-ref HEAD` prints `HEAD`), `where`
collapsed to `None` and the worker was rewritten as a bare `who` string,
silently destroying a stored `worker.where`.

**Fix.** Added a fallback in `goc/engine.py` `_auto_populate_worker`: when
no flag is given and no branch is detected, reuse `existing_dict.get("where")`
instead of dropping to `None`. A detectable branch still updates `where`
(the documented "add/update where" intent is unchanged).

**Verification.** `reproduce.py` flips PASS after the fix (worker preserved
as `{who: alice, where: feature/foo}` on a detached HEAD). New regression
test `tests/test_auto_populate_worker_preserves_where.py` covers both the
preserve-on-detached and update-on-detectable-branch paths. Full suite
(506 tests) green; `goc validate` clean. Plugin mirrors re-synced.
