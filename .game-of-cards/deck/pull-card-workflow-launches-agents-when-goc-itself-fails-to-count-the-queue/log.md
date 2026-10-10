## 2026-10-10T04:43:27Z — Confirmed, fix verified on a scratch copy, parked at session

`reproduce.py` landed and confirms the hypothesis. Under the runner
default `bash -e {0}`, both count steps (`queue`, `post`) exit 0 with
`count=''` when the `uv`/`goc` stand-ins exit 2, so the `!= '0'` gates
launch the agent and the re-trigger. It exits 1 at HEAD by design. A
real engine crash reproduces it end to end through the live step body: a
card holding one non-UTF-8 byte makes goc exit 1 on a
`UnicodeDecodeError`, and the step still exits 0 with `count=`.

The fix was verified before parking. `pull-card-yml.patch` (pipefail via
workflow-level `defaults`, `> 0` gates, the `--ready` count) passes
`git apply --check` at d84a9b38, and `reproduce.py --workflow` on the
patched copy exits 0. Variants run through the same harness:

- the sibling's `--ready` line alone still exits 1, which is the
  cross-check DoD item 3 asked for;
- a per-step `shell: bash`, a job-level `defaults`, `set -o pipefail` in
  the body, and an explicit exit-status check each exit 0;
- `continue-on-error: true` or an `always()` gate on the count step exits
  1, as it should.

The `> 0` coercion claim was checked against GitHub's expressions
reference: an empty string becomes 0, a non-numeric string becomes NaN,
and a relational comparison with NaN is false.

Gate raised to `session` by hand (no verb raises a gate) and the claim
released. The remaining DoD item is the workflow edit, which the bot's
token cannot push. One human edit closes this card and
`pull-card-workflow-launches-agent-sessions-when-the-ready-queue-is-empty`
together. That card's Fix section now points here.
