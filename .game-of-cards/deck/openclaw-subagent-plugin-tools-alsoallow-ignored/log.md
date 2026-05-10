
## 2026-05-10 — Slack sandbox first-class tool ENOENT follow-up

A Slack-thread retest found the first-class `goc` plugin tool can be visible but fail with `python3 ENOENT` in sandboxed Slack sessions, while the local CLI fallback works.

Likely cause: the plugin tool executes through OpenClaw's host-side plugin runtime and passes the agent-provided sandbox cwd (for example `/workspace`) into `runCommandWithTimeout(["python3", ...], { cwd })`. On the host, `/workspace` does not exist, so Node reports `spawn python3 ENOENT`; this is probably a cwd-path mismatch, not a missing Python binary. A local repro on the host confirms `spawnSync("python3", ..., { cwd: "/workspace" })` produces `ENOENT`.

Follow-up for the plugin-side fix: normalize sandbox paths such as `/workspace` to the corresponding host workspace before calling `runCommandWithTimeout`, or fall back to a known existing project directory when the requested cwd does not exist. Keep the sandbox CLI wrapper as a temporary fallback only.
