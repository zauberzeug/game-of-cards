---
title: hook-scripts-keep-spawning-one-crash-fix-per-malformed-input-shape
summary: "The three Python lifecycle hooks have no failure boundary and no contract test for the rule each of their crash fixes restates: a hook exits 0 (2 for the Stop hook's reminder) whatever its input. Five cards have each found one input that crashes a hook, from non-mapping stdin to a card or config that does not decode, and four were fixed one shape at a time while the fifth waits on a decision. Decide whether to close the family at the source with an entry-point boundary, a malformed-input contract test discovered from the hook directory, or both."
status: open
stage: null
contribution: medium
created: "2026-10-14T05:27:10Z"
closed_at: null
human_gate: decision
advances: []
advanced_by:
  - hook-scripts-crash-on-non-dict-stdin-json-with-attributeerror
  - hook-scripts-crash-on-non-string-field-values-with-attribute-or-typeerror
  - pattern-generalization-check-jsonl-per-line-loader-trusts-non-dict-entries
  - session-start-hook-crashes-on-a-card-whose-bytes-do-not-decode
  - pattern-generalization-stop-hook-crashes-on-a-config-or-transcript-that-does-not-decode
tags: [meta-fix, infra, api-contract]
definition_of_done: |
  - [ ] PROCESS: the mechanism in `## Decision required` (entry-point boundary, malformed-input contract test, or both) and the OpenClaw scope are chosen and recorded in `log.md` with the rationale
  - [ ] TDD: one test discovers every script in `goc/templates/hooks/` from the directory and asserts it exits 0 (2 only for the Stop hook's reminder) on each malformed input the five instances found; it fails against a hook with one of those guards removed
  - [ ] MECHANICAL: `pattern-generalization-check-jsonl-per-line-loader-trusts-non-dict-entries` is closed by the chosen mechanism, or kept open with a `log.md` note saying why it is not
  - [ ] MECHANICAL: mirrors regenerated — `python scripts/sync_plugin_assets.py --check` is clean
  - [ ] PROCESS: `uv run python -m unittest discover -s tests` and `uv run goc validate` both pass
---

# Hook scripts keep spawning one crash fix per malformed input shape

## The recurring shape

The hooks under `goc/templates/hooks/` (`deck_session_start.py`,
`deck_prompt_router.py`, `pattern_generalization_check.py`) run at every
session start, prompt and turn end in every consuming repo, through both
plugin payloads and the vendored install. Each ends in
`raise SystemExit(main())`, so an exception that escapes `main` exits 1,
and the host reports a hook error every time the event fires until
someone finds the input that trips it.

Each hook guards its inputs by hand, one `isinstance` check or `except`
clause at a time. Every gap so far was found by an audit and fixed as its
own card:

1. [hook-scripts-crash-on-non-dict-stdin-json-with-attributeerror](../hook-scripts-crash-on-non-dict-stdin-json-with-attributeerror/)
   (done 2026-05-30): hook-input JSON that parses to a list, a scalar or
   `null`.
2. [hook-scripts-crash-on-non-string-field-values-with-attribute-or-typeerror](../hook-scripts-crash-on-non-string-field-values-with-attribute-or-typeerror/)
   (done 2026-05-31): a `prompt` or `transcript_path` that is not a
   string.
3. [pattern-generalization-check-jsonl-per-line-loader-trusts-non-dict-entries](../pattern-generalization-check-jsonl-per-line-loader-trusts-non-dict-entries/)
   (open, decision): a transcript line that parses to something other
   than a mapping.
4. [session-start-hook-crashes-on-a-card-whose-bytes-do-not-decode](../session-start-hook-crashes-on-a-card-whose-bytes-do-not-decode/)
   (done 2026-10-14): a card README that is not UTF-8.
5. [pattern-generalization-stop-hook-crashes-on-a-config-or-transcript-that-does-not-decode](../pattern-generalization-stop-hook-crashes-on-a-config-or-transcript-that-does-not-decode/)
   (done 2026-10-14): a `config.yaml` or transcript the host's default
   encoding could not decode.

Each fix restated the same contract for its own site: input the hook
cannot use counts as absent, and the hook still exits 0. Each pinned it
with a test of the one shape that was found. Nothing states the contract
once, and nothing checks the next shape before it ships.

## Sibling families

- [unguarded-loader-callsites-keep-spawning-non-dict-shape-guard-fixes](../unguarded-loader-callsites-keep-spawning-non-dict-shape-guard-fixes/)
  covers the non-mapping shape across the engine's loaders. Instance 3
  advances it too. It lists the hooks' stdin readers only under
  "possibly more", as trusted input.
- [goc-crashes-on-hosts-whose-default-encoding-is-not-utf-8](../goc-crashes-on-hosts-whose-default-encoding-is-not-utf-8/)
  is the codec question for the engine and installer. Instances 4 and 5
  were its hook-side counterparts, and every hook file read now names
  UTF-8.
- [session-start-hook-reimplements-engine-waiting-and-frontmatter-logic-and-keeps-drifting](../session-start-hook-reimplements-engine-waiting-and-frontmatter-logic-and-keeps-drifting/)
  is about the SessionStart hook's parsing drifting from the engine.
  Instance 4 advances it too. That card asks whether the hook reads cards
  the way the engine does; this one asks whether a hook survives input
  it cannot read at all.

## Why it matters

A crashing hook fails twice. It is loud in the host: an error at every
session start or turn end, in every repo holding the input. And it
silently drops its job: the SessionStart reminder of claimed, parked and
impeded cards is not printed, so an agent can claim work another session
holds. Every consuming repo stays exposed until a release ships the point
fix. The point fixes are cheap, but each new shape is found only by an
audit, after it has shipped.

## Decision required

How should the hook contract be enforced, once, for every hook?

1. **Entry-point boundary.** Replace `raise SystemExit(main())` with a
   guard: an exception that escapes `main` prints one
   `[GoC] <hook> skipped: <error>` line to stderr and exits 0. The Stop
   hook's deliberate `return 2` is untouched. This covers shapes nobody
   has found yet, and tests that call `main()` in-process still see the
   exception. The cost is in the field: a regression that always raises
   turns a loud hook error into a reminder that silently never appears.
2. **Malformed-input contract test.** One test walks
   `goc/templates/hooks/*.py`, so a new hook is covered automatically,
   and runs each script against a shared corpus: non-mapping hook input,
   non-string fields, a `cwd` that does not exist, missing and
   undecodable card, config and transcript files, and non-mapping
   transcript lines. It asserts exit 0, or 2 for the Stop hook's
   reminder. Crashes stay loud in CI and the contract is written down
   once, but only the corpus is covered.
3. **Both.** The test pins the known shapes and the boundary contains
   the unknown ones.

Also answer: the OpenClaw plugin reimplements the hooks in TypeScript
(`api.on(...)` handlers in `openclaw-plugin/index.ts`). Are its handlers
in scope here, or tracked with
[openclaw-hook-predicates-reimplement-engine-logic-and-keep-drifting](../openclaw-hook-predicates-reimplement-engine-logic-and-keep-drifting/)?

Once decided, rewrite the DoD's TDD item to the chosen mechanism, and
say whether instance 3 closes with it.
