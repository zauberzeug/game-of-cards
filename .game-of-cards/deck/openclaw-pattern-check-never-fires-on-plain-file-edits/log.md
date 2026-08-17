# Log

## 2026-08-17 — Falsification recipe run; card confirmed, `unverified` cleared

Ran the `## Falsification recipe` during a deck hygiene pass. `npm install`
in `openclaw-plugin/` resolved the peer dependency to **openclaw 2026.5.7**
and the host's tool names were read out of the installed SDK.

**Verdict: confirmed, not disproved.** No registered tool is named `Edit`,
`Write`, or `NotebookEdit`. The SDK registers its file tools in lowercase:

| Registered tool id | Role |
|---|---|
| `edit` | file edit |
| `write` | file write |
| `apply_patch` | patch application |
| `read` | read-only |

Recipe step 3 says the card is disproved if any registered edit tool is
named `Edit`/`Write`/`NotebookEdit`. None is, so the structural finding
stands on the host's real vocabulary rather than on inference, and the
`unverified` tag is dropped. The DoD's EMPIRICAL item is checked; every
other item is untouched and the card stays open at its decision gate.

### Bearing on the recorded options

The SDK ships its own mutation classifier at `src/agents/tool-mutation.ts`
(bundled as `node_modules/openclaw/dist/tool-mutation-*.js`), exporting
`MUTATING_TOOL_NAMES`, `isLikelyMutatingToolName(toolName)` and
`isMutatingToolCall(toolName, args)`. `MUTATING_TOOL_NAMES` is
`{write, edit, apply_patch, exec, bash, process, message, sessions_spawn,
sessions_send, cron, gateway, canvas, nodes, session_status}` — a superset
of file mutation that also counts messaging and process control, so it is
not a drop-in for a *code*-mutation predicate.

This is the host-supplied signal option C hoped for, with one constraint
that narrows the choice: **the helpers are internal, not public API.**
Neither name appears in any entry reachable from the package's `exports`
map (`.`, `./plugin-sdk`, `./plugin-sdk/core`, `./plugin-sdk/runtime`, and
the rest), so a plugin cannot import them without reaching into a hashed
bundle filename that changes every release. Option C therefore costs an
upstream export request, not just a call site — worth recording before the
decision is made rather than discovering it during implementation.

Enumerating the three lowercase names (option A) needs no upstream change.
The list above is the enumeration that option A would consume, pinned to
openclaw 2026.5.7.
