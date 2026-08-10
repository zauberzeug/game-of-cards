---
title: deck-prompt-router-exploration-and-tooling-lists-can-never-suppress-the-reminder
summary: "The UserPromptSubmit hook computes has_exploration and has_tooling from 13 regexes, but its two-branch gate makes the output a pure function of has_work: the suppression branch is guarded by `not has_work` and the only print is guarded by `has_work`, so no input can make either list change the verdict. The module docstring's 'Silent for pure exploration / explanation / one-shot tooling' contract is therefore implemented by a no-op, and the two open sibling cards diagnose the mechanism as a live 'precedence rule' that does not exist."
status: open
stage: null
contribution: medium
created: "2026-07-31T06:37:36Z"
closed_at: null
human_gate: decision
advances:
  - deck-prompt-router-i-want-to-pattern-fires-on-pure-exploration-prompts
  - deck-prompt-router-work-verb-as-noun-fires-reminder-on-exploration-questions
advanced_by: []
tags: [bug, infra, documentation]
definition_of_done: |
  - [ ] PROCESS: the `## Decision required` question below is answered and recorded via `Skill(decide-card)`, lowering the gate to `none`. The answer must state whether the router is work-only by design (delete the lists) or whether suppression is meant to be load-bearing (wire it up).
  - [ ] TDD: `reproduce.py` exits non-zero — either the two lists are gone (so the ablation has nothing left to delete and the script's premise no longer holds), or at least one input's verdict depends on EXPLORATION / TOOLING.
  - [ ] TDD: a regression test pins the chosen semantics against the corpus in `reproduce.py`, asserting BOTH directions — every prompt that must fire still fires, and every prompt that must stay silent stays silent — so the next edit to `WORK_INITIATING` cannot silently flip either side.
  - [ ] MECHANICAL: the module docstring of `goc/templates/hooks/deck_prompt_router.py` describes what the code actually does; if the lists are deleted, the "Silent for pure exploration / explanation / one-shot tooling" sentence goes with them.
  - [ ] MECHANICAL: the change reaches all 7 source copies — the 5 Python mirrors via `python scripts/sync_plugin_assets.py` (`--check` clean) and the OpenClaw TypeScript port at `openclaw-plugin/index.ts` (plus its `dist/` build output) by hand.
  - [ ] PROCESS: the two cards this one advances are reconciled — their bodies no longer describe a "precedence rule" that lets work beat a matched exploration pattern, because no such rule exists. Record in `log.md` whether the chosen path closes them, narrows them, or leaves them untouched.
  - [ ] PROCESS: `uv run python -m unittest discover -s tests` and `uv run goc validate` both pass.
---

# The prompt router's exploration and tooling lists cannot change its output

## Location

`goc/templates/hooks/deck_prompt_router.py:83-90` — the whole gate:

```python
    has_work = any(re.search(p, prompt) for p in WORK_INITIATING)
    has_exploration = any(re.search(p, prompt) for p in EXPLORATION)
    has_tooling = any(re.search(p, prompt) for p in TOOLING)
    if (has_exploration or has_tooling) and not has_work:
        return 0
    if has_work:
        print(REMINDER)
    return 0
```

The two lists it reads are `EXPLORATION` (8 patterns,
`deck_prompt_router.py:38-47`) and `TOOLING` (5 patterns,
`deck_prompt_router.py:49-55`).

The OpenClaw TypeScript port makes the same structure explicit as two
consecutive returns — `openclaw-plugin/index.ts:745-746`:

```ts
      if ((hasExploration || hasTooling) && !hasWork) return;
      if (!hasWork) return;
```

## What's broken

The two branches partition on `has_work`, so the suppression branch can
only ever be reached when the print is already unreachable:

- `has_work` true → the first condition's `not has_work` is false, so
  control falls to `if has_work:` and the reminder prints. `has_exploration`
  and `has_tooling` are never consulted.
- `has_work` false → either the first branch returns without printing, or
  control falls to `if has_work:`, which is false, and returns without
  printing. Both paths produce the same output.

Output is therefore a pure function of `has_work`. The 13 suppression
patterns are unreachable: no input exists that makes either list change the
verdict. This is not "the suppression is too weak" — there is no
suppression.

That contradicts the module docstring, `deck_prompt_router.py:6-7`:

> Silent for pure exploration / explanation / one-shot tooling — those
> don't need cards. The reminder is opt-in (matched), not blanket.

The second sentence is true and is carried entirely by `WORK_INITIATING`.
The first sentence names a mechanism the file does not implement.

## Empirical evidence

`uv run python .game-of-cards/deck/deck-prompt-router-exploration-and-tooling-lists-can-never-suppress-the-reminder/reproduce.py`:

```
1. Exhaustive truth table over the three signals the hook computes
   work expl tool | shipped | both lists deleted
     0    0    0  |    0    |         0
     0    0    1  |    0    |         0
     0    1    0  |    0    |         0
     0    1    1  |    0    |         0
     1    0    0  |    1    |         1
     1    0    1  |    1    |         1
     1    1    0  |    1    |         1
     1    1    1  |    1    |         1
   rows where the two disagree: 0

2. Ablation over 27 prompts (8 EXPLORATION + 5 TOOLING patterns each represented)
   prompts matching an EXPLORATION or TOOLING pattern: 15
   prompts whose verdict changes when both lists are deleted: 0

3. Source copies carrying the unreachable lists
   - goc/templates/hooks/deck_prompt_router.py
   - .claude/hooks/deck_prompt_router.py
   - claude-plugin/hooks/deck_prompt_router.py
   - claude-plugin/goc/templates/hooks/deck_prompt_router.py
   - codex-plugin/hooks/deck_prompt_router.py
   - codex-plugin/goc/templates/hooks/deck_prompt_router.py
   - openclaw-plugin/index.ts
   total: 7

4. Dry-run of a fix option an open sibling card already proposes:
   'add understand|investigate|know|learn|see to EXPLORATION'
   work=1 expl=1 -> reminder fires: true   'I want to understand the parser'
   work=1 expl=1 -> reminder fires: true   'I want to know how values are computed'
   work=1 expl=1 -> reminder fires: true   'I want to learn about the deck'
   work=1 expl=1 -> reminder fires: true   'we need to investigate the flaky test'
   the added words now match, and the reminder still fires: yes

DEFECT CONFIRMED: no input can make EXPLORATION or TOOLING change the hook's output — the docstring's 'silent for pure exploration / explanation / one-shot tooling' contract is a no-op in 7 source copies.
```

The truth table settles it by construction — all eight rows of the boolean
triple agree — so the ablation's clean sweep is not an artifact of the
corpus. 15 of the 27 corpus prompts do match a suppression pattern; none of
them has its verdict changed by deleting both lists.

Section 4 is the cost made concrete. It replays, verbatim, one of the three
fix options that
[deck-prompt-router-i-want-to-pattern-fires-on-pure-exploration-prompts](../deck-prompt-router-i-want-to-pattern-fires-on-pure-exploration-prompts/)
offers in its own DoD — "add `understand|investigate|know|learn|see` to
EXPLORATION". The words match after the edit (`expl=1` on all four of that
card's named prompts), and all four still fire the reminder. An implementer
who picks that option ships a change with provably zero effect, then
watches `reproduce.py` on that card still fail and has no idea why.

## Why it matters

Three costs, in ascending order.

**Maintenance.** 13 regexes are carried in 7 source copies. Six of them are
byte-identical Python mirrors that `scripts/sync_plugin_assets.py`
regenerates and CI enforces with `--check`; the seventh is a hand-ported
TypeScript translation whose comment claims the patterns "mirror
`goc/templates/hooks/deck_prompt_router.py` exactly"
(`openclaw-plugin/index.ts:343`). Every future edit to the suppression
vocabulary pays full sync and review cost for zero behavior.

**Misdirected diagnosis.** Two open cards attribute the router's
over-firing to a live precedence policy:

- [deck-prompt-router-work-verb-as-noun-fires-reminder-on-exploration-questions](../deck-prompt-router-work-verb-as-noun-fires-reminder-on-exploration-questions/)
  states "Exploration only suppresses the reminder when **no** work pattern
  fires. Any work match wins."
- [deck-prompt-router-i-want-to-pattern-fires-on-pure-exploration-prompts](../deck-prompt-router-i-want-to-pattern-fires-on-pure-exploration-prompts/)
  shares the same framing; its sibling's DoD requires the fix be
  "coordinated with the sibling card (both cards share the precedence root
  cause)".

The first half of that sentence is false: when no work pattern fires,
nothing prints regardless, so exploration suppresses nothing.

Both cards propose narrowing `WORK_INITIATING`, which is a reasonable fix
for their symptom — but it leaves the dead layer in place, and leaves the
next reader believing a suppression mechanism guards the exploration path.
Worse, the `i want to` card's DoD offers three fix paths and one of them is
unworkable for a reason the file never states: "add
`understand|investigate|know|learn|see` to EXPLORATION". Section 4 of the
evidence above runs exactly that edit; the words match and nothing changes.
That option is not a weak fix, it is a no-op. That is why this card advances
both: whichever way the question below is answered changes what
"coordinated" means for them.

**Reachability.** This is not a latent path. The hook is registered on
`UserPromptSubmit` by `GOC_CLAUDE_HOOKS` in `goc/install.py` and shipped in
both plugin payloads, so it evaluates on every prompt in every session of
every consuming repo that installs GoC. The dead branch executes constantly;
it simply never decides anything.

## Sibling shape: populated structure with no reachable consumer

Recorded 2026-07-31 at filing time. Not a scope expansion of this card and
not an umbrella — context for whoever answers the question below, because
the same shape already has one open card.

[agent-manifest-guidance-block-is-built-but-silently-ignored](../agent-manifest-guidance-block-is-built-but-silently-ignored/)
is the other instance: the Claude agent manifest declares a `guidance`
block, `_load_agent_shim` faithfully builds `GuidanceBlock` tuples onto
`AgentShim.guidance`, and nothing reads that attribute — the briefing flow
uses hardcoded `AGENTS_GUIDANCE` / `CLAUDE_GUIDANCE` constants instead. Its
"why it matters" is this card's argument verbatim: a contributor edits the
dead surface expecting effect, ships a no-op, and debugs it.

Both are the same shape, and neither is the classic dead code a linter
finds. The structure is *populated on every run*, so coverage tools see it
executing; what is missing is a consumer that can act on the value. That is
why both survived — the code is live, only the effect is absent.

**Sweep, bounded and reported.** Scanned every module-level constant in
`goc/` and `scripts/` (93 names, `_vendor/` excluded as third-party) for
definitions with no reader anywhere in `goc/`, `scripts/`, or `tests/`. One
hit: `SUPERSEDE_REL_FIELDS` (`goc/engine.py:1231`), whose three neighbours
`LIST_REL_FIELDS`, `ADVANCE_REL_FIELDS` and `INVERSE_REL` all have readers —
`HalfEdge.is_advance` (`goc/engine.py:1268`) consults `ADVANCE_REL_FIELDS`,
while the supersession branch is written out longhand as
`edge.field == "superseded_by"` (`goc/engine.py:5918`) rather than through
the constant sitting right beside it. That is the degenerate case of this
shape — an unused name, not a misleading contract — so it is noted here
rather than filed. The sweep did NOT cover unread dataclass *fields* or dict
keys, which is the shape both real instances actually take; doing that
properly needs call-graph analysis, not grep.

**No umbrella filed.** Two instances, both open, both with a concrete fix
path already written. A third substantive instance — a populated structure
whose absent consumer misleads an author into a no-op change — is the signal
to file the root, per the deck-hygiene rule that filing must not outpace
deciding.

## Decision required

Is the router meant to be work-only, or is suppression meant to be
load-bearing?

**Option A — delete the suppression layer.** Remove `EXPLORATION`,
`TOOLING`, and the dead branch; keep the gate as `if has_work: print(...)`.
Drop the docstring's "silent for pure exploration" sentence. Behavior is
unchanged (proven above), the file shrinks by ~20 lines across 7 copies, and
the two sibling cards become purely about tightening `WORK_INITIATING` —
which is what they already propose. Cost: gives up a suppression vocabulary
someone may have wanted, and the two siblings' false positives (`"how does
the update logic work?"`) stay until their own fixes land.

**Option B — make suppression load-bearing.** Give exploration/tooling real
precedence, e.g. `if has_exploration or has_tooling: return 0` before the
work check, so a prompt that reads as a question stays silent even when it
names a work verb. This closes
[deck-prompt-router-work-verb-as-noun-fires-reminder-on-exploration-questions](../deck-prompt-router-work-verb-as-noun-fires-reminder-on-exploration-questions/)
outright — all five prompts in its DoD match an EXPLORATION pattern today
(verified). It does **not** close the `i want to` card on its own: none of
that card's four prompts matches EXPLORATION, so B has to be paired with
adding the vocabulary its DoD names — which only becomes a real fix once B
lands. Cost: B inverts the precedence, so a genuine mixed request
(`"explain how to add a card"`, `"run the tests and fix the failures"` —
both in the corpus) loses its reminder. That is a recall regression on
exactly the shape
[deck-prompt-router-missing-rename-update-change-delete-edit-verbs](../deck-prompt-router-missing-rename-update-change-delete-edit-verbs/)
and [prompt-hook-misses-rename-work-requests](../prompt-hook-misses-rename-work-requests/)
were closed to prevent.

**Option C — a scoring rule.** Fire only when work signal outweighs
exploration signal (e.g. an imperative work match at the start of the
prompt beats a mid-sentence noun use). Strictly more expressive than A or
B and would close the siblings without the recall regression, but it is a
new mechanism to design, test, and port to TypeScript — materially more
work than either alternative, and it needs its own corpus to tune against.

The question is not which is cheapest to implement; it is whether the
router's job is "detect work" (A) or "route between work and questions"
(B/C). Answer that and the fix follows.

## Fix

Determined by the decision above. Whichever option is chosen, the change
must land in `goc/templates/hooks/deck_prompt_router.py` (the
source-of-truth), be propagated to the 5 Python mirrors by
`python scripts/sync_plugin_assets.py`, and be hand-ported to
`openclaw-plugin/index.ts:739-752` plus its committed `dist/` build output —
the porter script does not cover `index.ts`.
