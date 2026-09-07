---
title: deck-auto-commit-prints-raw-git-output-before-the-verbs-own-report
summary: "goc's deck auto-commit ran `git add` and `git commit` without `capture_output=True` — the only subprocess calls in engine.py that did not — so git's own porcelain landed on goc's stdout. When stdout is a pipe (agent tool capture, CI logs, `| head`) Python's block buffering makes git's lines arrive BEFORE the verb's own report, scrambling the output of every auto-committing verb, `goc status <title> active` included. The closed sibling `move-fallback-leaks-git-fatal` had already fixed this exact shape at the `git mv` call site."
status: done
stage: null
contribution: medium
created: "2026-08-10T05:35:14Z"
closed_at: "2026-08-10T05:45:21Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, infra]
definition_of_done: |
  - [x] TDD: `uv run python .game-of-cards/deck/deck-auto-commit-prints-raw-git-output-before-the-verbs-own-report/reproduce.py` exits zero — no git porcelain on goc's stdout and the verb report arrives in code order for `status`, `wait` and `advance`
  - [x] TDD: regression test under `tests/` pins that an auto-committing verb's piped stdout contains only goc's own lines, and that a FAILING `git commit` still surfaces git's diagnostic (captured output is reported, not swallowed)
  - [x] TDD: source-level guard fails on ANY `subprocess.run` in `goc/engine.py` that omits `capture_output=`/`stdout=` — the behavioral tests only reach `_git_auto_commit`, so a future uncaptured call would reintroduce the interleaving unseen
  - [x] MECHANICAL: `git add` and `git commit` in `_git_auto_commit` pass `capture_output=True` like every other `subprocess.run` in `goc/engine.py`
  - [x] PROCESS: `uv run python -m unittest discover -s tests` no worse than main; `uv run goc validate` passes
worker: {who: "claude[bot]", where: main}
---

# deck auto-commit prints raw git output before the verb's own report

## Location

`goc/engine.py:4685` and `goc/engine.py:4693` (`_git_auto_commit`):

```python
        subprocess.run(["git", "add", "--", *paths], check=True, cwd=git_cwd)
        ...
        subprocess.run(["git", "commit", "-m", message, "--", *paths], check=True, cwd=git_cwd)
```

`_git_auto_commit` holds the **only** `subprocess.run` calls in
`goc/engine.py` that omit `capture_output=True` — these two plus the
`git diff --cached --quiet` check between them. Every call outside this
function passes it: `git mv` (`goc/engine.py:6271`), `git push`,
`git rebase`, `git fetch`, `git show`, `git ls-files`, `git config`,
`git rev-parse`, `git check-ignore`, `git merge-base`.

The `--quiet` diff check never actually leaked (the flag suppresses its
output), so the observable defect is the `add`/`commit` pair; it is listed
because the invariant worth restoring is "no child of goc writes to goc's
stdout", not "the two noisy ones were silenced".

## What's broken

Without `capture_output=True` the child inherits goc's stdout, so `git
commit`'s porcelain summary is written to it directly. Two consequences:

**A — noise.** The verb already prints its own deliberate one-line report of
the commit. `_cmd_status` ends with:

```python
        if _git_auto_commit(commit_targets, f"deck: {title} {prior} → {new_status}"):
            print("  committed")
```

so `[master 4fdd27c] deck: alpha open → active` / ` 1 file changed, …` is
redundant with the `  committed` line goc chose to emit.

**B — reordering.** `_cmd_status` prints its report *before* it commits —
`print(f"{title}: {prior} → {new_status}")` at `goc/engine.py:5595`, the
`_git_auto_commit` call at `goc/engine.py:5605`. When stdout is a pipe,
CPython block-buffers goc's own prints while the git child writes to the
inherited descriptor immediately, so git's lines land *first* and the verb's
report arrives after. On a tty stdout is line-buffered and the order is right,
which is why this is invisible in interactive use and visible everywhere
output is captured: agent tool calls, CI logs, `goc … | head`.

This is the same defect shape the closed card
[move-fallback-leaks-git-fatal](../move-fallback-leaks-git-fatal/) diagnosed
and fixed at the `git mv` call site — "The subprocess does not capture
stderr" — with the fix "Capture stdout/stderr for the attempted `git mv`".
The auto-commit path was never brought into line.

## Empirical evidence

`uv run python .game-of-cards/deck/deck-auto-commit-prints-raw-git-output-before-the-verbs-own-report/reproduce.py`, run against the engine as it stood
at the filing commit (before the fix below):

```text
--- goc status alpha active  (stdout through a pipe) ---
  [0] [master 4fdd27c] deck: alpha open → active
  [1]  1 file changed, 2 insertions(+), 1 deletion(-)
  [2] alpha: open → active
  [3] Next: implement the card; tick DoD items as you go; then goc done alpha.
  [4]   committed

--- goc wait alpha --reason external  (stdout through a pipe) ---
  [0] [master e7efcc8] deck: alpha waiting_on external
  [1]  1 file changed, 1 insertion(+)
  [2] alpha: waiting_on='external' waiting_until=None
  [3]   committed

--- goc advance alpha --by beta  (stdout through a pipe) ---
  [0] [master 4e55872] deck: beta advances alpha
  [1]  2 files changed, 4 insertions(+), 2 deletions(-)
  [2] advance: alpha.advanced_by += beta; beta.advances += alpha
  [3]   committed

defect present:
  - status-active: git porcelain on goc stdout: '[master 4fdd27c] deck: alpha open → active'
  - status-active: git line at [0] precedes the verb report at [2] — output reordered under a pipe
  - wait: git porcelain on goc stdout: '[master e7efcc8] deck: alpha waiting_on external'
  - wait: git line at [0] precedes the verb report at [2] — output reordered under a pipe
  - advance: git porcelain on goc stdout: '[master 4e55872] deck: beta advances alpha'
  - advance: git line at [0] precedes the verb report at [2] — output reordered under a pipe
```

The same command with stdout on a pty prints the verb report first and the
git summary after it — the ordering half of the defect is pipe-only, the
noise half fires everywhere.

After the fix, the same three verbs emit only goc's own lines and the script
exits zero:

```text
--- goc status alpha active  (stdout through a pipe) ---
  [0] alpha: open → active
  [1] Next: implement the card; tick DoD items as you go; then goc done alpha.
  [2]   committed
...
defect fixed: no git porcelain on goc stdout; verb report in code order
```

## Why it matters

Auto-commit is on by default (`workflow.auto_commit: true` is the shipped
default in `.game-of-cards/config.yaml`, and `auto_commit_enabled` defaults to
`True` when the key is absent), and seven verbs route through
`_git_auto_commit`: `status`, `publish`, `new --commit`, `wait`, `advance`,
`unadvance`, `decide`. `goc status <title> active` is the first mutation of
every `pull-card` session, so every autonomous run in every consuming repo
emits this.

The reordering matters more than the noise. goc's CLI contract is a small set
of structured lines an agent reads back — the verb's own state-transition
line, then `  committed`. Interleaving another program's output ahead of them
means the first line an agent sees after claiming a card is git's, and the
line that says what actually happened is buried below. That is precisely the
capture path — agent tool calls, CI logs — where nobody is watching a
terminal, and it is the same reason
[goc-leaks-brokenpipeerror-when-stdout-pipe-closes-early](../goc-leaks-brokenpipeerror-when-stdout-pipe-closes-early/)
was worth closing: goc owns its stdout, and anything else writing there is a
contract break.

## Fix (applied)

All three `subprocess.run` calls in `_git_auto_commit` now pass
`capture_output=True, text=True`, matching every other `subprocess.run` in the
module: `git add`, `git commit`, and the `git diff --cached --quiet` check
between them. The diff check was silent anyway — it is captured so the
invariant is "no child of goc writes to goc's stdout", not "the two noisy ones
were silenced", which is what a source-level guard can actually enforce.

Capturing does not swallow diagnostics. Both mutating calls are `check=True`,
so a failure raises `CalledProcessError` into the handler below them, which now
replays the captured `stderr` and `stdout` as indented lines under the existing
`  (auto-commit failed: …)` message. git routes pre-commit hook output to
stderr, so a refusing hook still reports why — verified by
`tests/test_auto_commit_stdout_isolation.py::test_failing_commit_still_reports_gits_diagnostic`,
which installs a hook that writes a marker to each stream and asserts both
reach goc's stderr. Without the replay loop that test fails, so the fix cannot
regress into a silent no-op.

The third test in that file is a source-level guard: it parses every
`subprocess.run(` call in `goc/engine.py` and fails on any that omits
`capture_output=`/`stdout=`. The behavioral tests only reach `_git_auto_commit`,
so a new uncaptured call elsewhere would reintroduce the interleaving without
turning anything red. That guard is what caught the `git diff --cached` call
this card's own body originally described as already captured.
