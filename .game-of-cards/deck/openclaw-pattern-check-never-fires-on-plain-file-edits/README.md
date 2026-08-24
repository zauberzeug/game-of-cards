---
title: openclaw-pattern-check-never-fires-on-plain-file-edits
summary: "The OpenClaw plugin's `agent_end` hook decides whether a turn mutated code by matching tool names. Its shell branch accepts both hosts' spellings (`exec` OR `Bash`), but its file-edit branch reuses `CODE_MUTATING_TOOLS` verbatim from the Claude Code hook — `Edit`/`Write`/`NotebookEdit` — names OpenClaw does not use. So on OpenClaw the pattern-generalization reminder can only fire via a broad git command, never via a plain file edit, and the opt-in feature is silently dead for the common case."
status: open
stage: null
contribution: medium
created: "2026-08-04T06:19:15Z"
closed_at: null
human_gate: decision
advances:
  - openclaw-hook-predicates-reimplement-engine-logic-and-keep-drifting
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [ ] PROCESS: human resolves `## Decision required` — recognizer strategy chosen (enumerate OpenClaw's edit-tool names / invert to a read-only denylist / drop tool-name matching for a host-supplied mutation signal), recorded in log.md
  - [x] EMPIRICAL: OpenClaw's actual file-edit tool names enumerated from the installed SDK (recipe in `## Falsification recipe`), verdict recorded in log.md either way — this is what clears the `unverified` tag
  - [ ] TDD: reproduce.py exits 1 — the detector fires for the host's own edit-tool spellings, not only for Claude Code's three
  - [ ] TDD: baselines preserved — still fires on `Edit`/`Write`/`NotebookEdit` (Claude-shaped transcripts remain covered) and on a broad git command under both `exec` and `Bash`; still silent on a read-only-tools-only turn
  - [ ] MECHANICAL: fix lands in `openclaw-plugin/index.ts` (hand-ported, not auto-synced) and `openclaw-plugin/dist/` is rebuilt; the Python hook `goc/templates/hooks/pattern_generalization_check.py` is left alone unless the chosen strategy is host-neutral
  - [ ] PROCESS: `tests/test_openclaw_session_start_hook.py` (or a sibling openclaw test) gains a regression row asserting the host's edit-tool names are recognized, so this cannot silently regress
---

# OpenClaw pattern-check never fires on plain file edits

## Location

`openclaw-plugin/index.ts:410` — `CODE_MUTATING_TOOLS`.
`openclaw-plugin/index.ts:784-791` — the `agent_end` handler's `mutating`
predicate that reads it.

## What's broken

The `agent_end` hook is the OpenClaw port of the pattern-generalization
Stop hook. It decides whether the turn just ended mutated code, and if so
injects a self-assessment reminder. It makes that decision by matching
**tool names**, and it treats the two kinds of mutating tool inconsistently:

```ts
// openclaw-plugin/index.ts:410
const CODE_MUTATING_TOOLS = new Set(["Edit", "Write", "NotebookEdit"]);

// openclaw-plugin/index.ts:784-791
const mutating = toolCalls.some((tc: any) => {
  if (CODE_MUTATING_TOOLS.has(tc?.name)) return true;
  if (tc?.name === "exec" || tc?.name === "Bash") {
    const cmd = (tc?.params?.command ?? tc?.params?.cmd ?? "") as string;
    return isBroadGitMutation(cmd);
  }
  return false;
});
```

The shell branch is **host-generalized**: it accepts `exec` (OpenClaw's
shell tool) *and* `Bash` (Claude Code's). The edit branch is not — it
reuses the Claude-only set verbatim.

Those two branches cannot both be right. The `exec` alias exists precisely
because OpenClaw's tool vocabulary differs from Claude Code's; the plugin's
own README says so when it describes the registered `goc` tool as sharing a
surface with the host's built-ins:

> `openclaw-plugin/README.md:105-107` — "The `goc` tool is a typed function
> (`{ verb, args, flags, cwd }`) that the model can call as it would any
> other tool — same surface as `exec`, `browser`, `web_search`."

`Edit`, `Write` and `NotebookEdit` are Claude Code tool names. Nothing in
the OpenClaw payload aliases them, so on OpenClaw the edit branch is dead
code and the hook can only fire through the shell branch — i.e. only when
the turn happened to run `git commit` or a broad `git add`.

The Claude-side docstring the port inherits states the intended trigger set,
which the OpenClaw behavior does not deliver:

> `goc/templates/hooks/pattern_generalization_check.py:3-4` — "Fires only on
> turns that included code-mutating tool calls (Edit, Write, or
> NotebookEdit, or Bash containing a git-commit)."

## Empirical evidence

`uv run python .game-of-cards/deck/openclaw-pattern-check-never-fires-on-plain-file-edits/reproduce.py`
extracts the production predicate from `index.ts` and runs it under Node
(the same extraction technique `tests/test_openclaw_session_start_hook.py`
uses, so no `npm install` is required):

```
agent_end mutation detector — openclaw-plugin/index.ts

  SHELL branch (host-generalized: `exec` OR `Bash`):
    exec                 git add -A  -> fires=True
    Bash                 git add -A  -> fires=True

  EDIT branch (CODE_MUTATING_TOOLS — Claude Code names only):
    Edit                 -> fires=True
    Write                -> fires=True
    NotebookEdit         -> fires=True

  EDIT branch, OpenClaw-native spellings:
    edit                 -> fires=False
    write                -> fires=False
    edit_file            -> fires=False
    write_file           -> fires=False
    apply_patch          -> fires=False
    str_replace_editor   -> fires=False
    fileWrite            -> fires=False
    patch                -> fires=False

shell branch accepts both host spellings : True
edit branch accepts all 3 Claude names   : True
edit branch accepts 0/8 OpenClaw names : True

DEFECT PRESENT: the same predicate aliases the shell tool across hosts but
hard-codes Claude Code's edit-tool vocabulary, so on OpenClaw the
pattern-generalization reminder can only fire via a broad git command —
never via a plain file edit.
```

The 8 OpenClaw-side spellings are a *sweep*, not a claim about which name
is real: the finding is that no spelling outside the Claude triple can
satisfy the predicate, whichever one OpenClaw actually uses.

## Falsification recipe — run 2026-08-17, card confirmed

The recipe was run against **openclaw 2026.5.7** (`npm install` in
`openclaw-plugin/`, then reading the host's registered tool ids out of
`node_modules/openclaw/dist/`). Its step 3 disproves this card if any
registered edit tool is named `Edit` / `Write` / `NotebookEdit`. None is —
the host registers `edit`, `write`, `apply_patch` (and read-only `read`),
all lowercase. The card is confirmed on the host's real vocabulary, and
the `unverified` tag is dropped. Full readout in `log.md`.

Those three names are the enumeration option A would consume. The SDK also
carries its own mutation classifier (`isMutatingToolCall`,
`isLikelyMutatingToolName`, `MUTATING_TOOL_NAMES` in
`src/agents/tool-mutation.ts`) — the host-supplied signal option C wants —
but it is **internal**: no public entry in the package's `exports` map
re-exports it, so option C costs an upstream export request. That
constraint is new information for the decision below; `log.md` records how
it was established.

## Why it matters

The hook is opt-in and default-off, so nothing breaks loudly. That is the
problem: a repo that turns `pattern_generalization_check: true` on under
OpenClaw gets a feature that appears configured and does almost nothing —
the reminder is suppressed on exactly the turn shape it exists for (an
agent edits files and yields). Only the minority of turns that also ran a
broad `git add`/`git commit` through the shell reach the reminder.

This is a different shape from
[openclaw-hook-predicates-reimplement-engine-logic-and-keep-drifting](../openclaw-hook-predicates-reimplement-engine-logic-and-keep-drifting/),
which this card advances: that meta-fix covers TS predicates that drifted
from their *Python engine* counterparts (`isImpeded`, `parseWaitingUntil`,
`frontmatterTail`, `stripQuotes`). Here the port is faithful to its Python
source — and that faithfulness is the bug, because the copied value is
host-specific vocabulary that does not survive the port.

The closed card
[pattern-generalization-mutation-detector-skips-notebookedit-tool-calls](../pattern-generalization-mutation-detector-skips-notebookedit-tool-calls/)
entrenched it: its DoD reads "`openclaw-plugin/index.ts` `CODE_MUTATING_TOOLS`
mirror updated by hand", treating the TS set as a mirror that should carry
Claude's names rather than the host's. That closure is correct on its own
terms (it added `NotebookEdit` where it belonged) and needs no reopening —
this card is the forward pointer.

## Decision required

The fix depends on a strategy choice no single reading settles. Three
credible paths:

**A. Enumerate OpenClaw's edit-tool names.** Add the host's real spellings
to `CODE_MUTATING_TOOLS` (or a second host-specific set). Smallest change,
matches the existing `exec` / `Bash` aliasing style. Cost: it is the same
enumerate-the-surface strategy that the sibling meta-fix
[pattern-generalization-mutation-detector-matches-git-staging-by-literal-flag-tokens](../pattern-generalization-mutation-detector-matches-git-staging-by-literal-flag-tokens/)
is open to *replace* for git flags — it will need another patch per host
and per upstream tool rename.

**B. Invert to a read-only denylist.** Treat any tool call as mutating
unless its name is in a known read-only set (read / grep / glob / search /
the `goc` tool itself). Self-maintaining for new edit tools; risks
over-firing the reminder on read-only turns whose tools are unrecognized,
which costs an agent round-trip each time (the reason the hook is opt-in).

**C. Stop matching tool names.** Ask the host for the mutation signal —
if OpenClaw's `agent_end` context exposes file-change or diff metadata,
key off that instead of a name list. Most robust, and would let the
`TODO(verify-context-shape)` at `index.ts:789-792` be resolved in the same
pass. Requires knowing what `agent_end` actually carries, which the same
`npm install` spike in the falsification recipe would establish.

Note the choice interacts with strategy: if **C** is picked, the `exec`
branch's `isBroadGitMutation` call may become unnecessary on OpenClaw,
which touches the open git-grammar meta-fix's scope. Recording which of
A/B/C is chosen — and whether it subsumes the Claude-side hook or is
OpenClaw-only — is the first DoD item.
