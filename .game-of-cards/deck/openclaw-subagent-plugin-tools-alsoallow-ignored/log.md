## 2026-05-26 — reclassified blocked → open + waiting_on: external

Reclassified off the `status: blocked` axis as part of the three-axis
migration (`migrate-existing-blocked-cards-to-open-or-waiting-overlay`).
This is an exogenous wait on an upstream OpenClaw release containing
the `alsoAllow` fix (PR #51388 or successor), not a card-blocks-card
dependency, so the shipped impediment overlay
(`waiting_on: external`) is the correct stored signal. The overlay
hides the card from the pull queue without overloading the progress
status; once OpenClaw ships the fix, `goc wait <title> --clear` and
re-pull to retest the remaining DoD items.

## 2026-05-10 — Slack sandbox first-class tool ENOENT follow-up

A Slack-thread retest found the first-class `goc` plugin tool can be visible but fail with `python3 ENOENT` in sandboxed Slack sessions, while the local CLI fallback works.

Likely cause: the plugin tool executes through OpenClaw's host-side plugin runtime and passes the agent-provided sandbox cwd (for example `/workspace`) into `runCommandWithTimeout(["python3", ...], { cwd })`. On the host, `/workspace` does not exist, so Node reports `spawn python3 ENOENT`; this is probably a cwd-path mismatch, not a missing Python binary. A local repro on the host confirms `spawnSync("python3", ..., { cwd: "/workspace" })` produces `ENOENT`.

Follow-up for the plugin-side fix: normalize sandbox paths such as `/workspace` to the corresponding host workspace before calling `runCommandWithTimeout`, or fall back to a known existing project directory when the requested cwd does not exist. Keep the sandbox CLI wrapper as a temporary fallback only.
