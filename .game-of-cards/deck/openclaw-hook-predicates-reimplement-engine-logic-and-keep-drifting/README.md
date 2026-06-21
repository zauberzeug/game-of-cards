---
title: openclaw-hook-predicates-reimplement-engine-logic-and-keep-drifting
summary: "META-FIX. The OpenClaw plugin's `index.ts` hand-reimplements several Python engine predicates (parseWaitingUntil/isImpeded/frontmatterTail/stripQuotes/opt-out regex) in TypeScript. They keep drifting from the engine one bug at a time — three fixed so far — because the only parity guard is a hand-maintained isImpeded matrix test that catches only what someone remembered to add. Decide a systematic port-parity guard."
status: open
stage: null
contribution: medium
created: "2026-06-05T05:19:57Z"
closed_at: null
human_gate: decision
advances: []
advanced_by:
  - openclaw-session-start-frontmatter-reader-truncates-colon-bearing-values-via-typescript-split-limit
  - openclaw-session-start-hook-accepts-calendar-impossible-waiting-until
tags: [meta-fix, infra]
definition_of_done: |
  - [ ] (replace after the decision is recorded)
---

# OpenClaw hook predicates reimplement engine logic and keep drifting

## The recurring shape

`openclaw-plugin/index.ts` is a hand-maintained TypeScript port of several
`goc.engine` predicates, used by the OpenClaw lifecycle hooks (session-start
active-card reminder, deck-prompt router, pattern-generalization self-assess).
Unlike the skills mirrors (porter `--check` + `tests/test_plugin_mirror_parity.py`)
and the engine mirror trees (byte-for-byte sync tripwire), these runtime
predicates have **no systematic parity guard against their Python sources** —
the port is a genuine reimplementation, not a copy, so it cannot be diffed
byte-for-byte.

The predicates currently ported by hand:

- `parseWaitingUntil` ⟷ `goc.engine._waiting_until_instant` (+ `_is_iso_date`)
- `isImpeded` ⟷ `goc.engine.waiting_impedes`
- `frontmatterTail` ⟷ `deck_session_start._frontmatter_tail`
- `stripQuotes` ⟷ the Python tail's `.strip('"').strip("'")`
- the `agent_end` opt-out regex ⟷ `pattern_generalization_check` opt-out

Each drifts independently, and each drift has been discovered and fixed as its
own one-off card rather than caught by a guard:

1. `openclaw-session-start-frontmatter-reader-truncates-colon-bearing-values-via-typescript-split-limit`
   (done) — `split(":", 2)` truncated ISO datetimes.
2. The bare-deferral malformed-`waiting_until` backstop drift (the cell
   `tests/test_openclaw_session_start_hook.py`'s docstring documents).
3. `openclaw-session-start-hook-accepts-calendar-impossible-waiting-until`
   (done) — `Date.parse` rolled `2026-02-30` forward instead of rejecting it.

The only existing guard is the hand-written `isImpeded` matrix in
`tests/test_openclaw_session_start_hook.py`: it extracts the TS functions and
runs them under Node, but it asserts a fixed list of cells someone thought to
add. It is not derived from the engine, so a new engine behavior (or a new
ported predicate) is invisible to it until a human extends it. This is the same
"reimplements the same logic and keeps drifting" shape the deck already tracks
for [yaml-lite-quote-scanners-reimplement-the-same-state-machine-and-keep-drifting](../yaml-lite-quote-scanners-reimplement-the-same-state-machine-and-keep-drifting/)
and [dod-fence-mask-reimplements-commonmark-fences-and-keeps-drifting](../dod-fence-mask-reimplements-commonmark-fences-and-keeps-drifting/).

## Why it matters

These predicates gate which cards the OpenClaw hooks announce as resumable and
which prompts trigger deck-first routing. A silent drift means the OpenClaw
host behaves differently from every other host (Claude, Codex, pipx) for the
same deck — and the read-time guards run *before* `goc validate`, so they are
the last line of defense on hand-edited decks. Fixing them one at a time means
every future engine change to one of these predicates is a latent OpenClaw bug
until someone happens to re-port and re-test it by hand.

## Decision required

What is the right systematic parity guard for the hand-ported `index.ts`
predicates? Candidate mechanisms (not mutually exclusive):

1. **Shared-matrix parity test** — generalize the `reproduce.py` from
   `openclaw-session-start-hook-accepts-calendar-impossible-waiting-until`
   into a test: define ONE input matrix per predicate, run the extracted TS
   under Node AND the Python engine, assert agreement cell-by-cell. Cheap,
   already prototyped, but still requires a human to grow the matrix as engine
   behavior expands (it pins agreement on enumerated inputs, not on all inputs).
2. **Property/fuzz parity test** — generate random/edge-case inputs (dates,
   frontmatter lines, opt-out strings), feed both implementations, assert
   agreement. Catches un-enumerated drift but flakier and needs careful input
   generators.
3. **Codegen the port** — emit the TS predicates from a single source so they
   cannot drift (heavier; the port currently exists precisely because the host
   shapes differ, so this may not be feasible for all five predicates).
4. **Catalogue + lint** — at minimum, a doc/registry listing every ported
   predicate and its Python source, plus a CI reminder when either side
   changes (weakest; documents the contract without enforcing it).

Scope question: which predicates does the guard cover (just the
`waiting`/`frontmatter` pair, or all five including the opt-out regex)? And
where does it live — extend `tests/test_openclaw_session_start_hook.py`, or a
new `tests/test_openclaw_engine_parity.py`?

Pick a mechanism + scope; then rewrite the DoD to implement it.
