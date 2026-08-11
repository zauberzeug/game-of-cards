---
title: skill-context-blocks-truncate-deck-output-hiding-active-cards-and-breaking-json
summary: "The six `!`-blocks that feed live deck data into skill bodies bound the engine's output with a fixed `head -N`. On this repo's deck that silently drops the fifth active card from `pull-card`/`next-card`'s soft-lock table, and truncates `standup`/`refine-deck`/`retrospective`'s `--json` dumps mid-object into unparseable JSON. `head` cannot report what it removed, and the engine's only row bound (`--max-rows`) is board-only."
status: open
stage: null
contribution: high
created: "2026-08-11T05:48:53Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract, infra, meta-fix]
definition_of_done: |
  - [ ] PROCESS: the `## Decision required` question below is answered and recorded via `Skill(decide-card)`, lowering the gate to `none`.
  - [ ] TDD: `reproduce.py` exits zero against this repo's own deck — no `!`-block drops a card from a table, and every `--json` block forwards a fragment that `json.loads` accepts.
  - [ ] TDD: a regression test asserts the invariant directly rather than re-running the CLI — for every `!`-block in `goc/templates/skills/*/SKILL.md`, a `--json` query is never piped through a line-bounding filter, and any bounded table query names its bound in a way the engine can report on. It must fail on today's tree.
  - [ ] MECHANICAL: the chosen option landed across all six live sites (`pull-card` :30 and :42, `next-card` :17, `standup` :24, `refine-deck` :91, `retrospective` :17) in `goc/templates/skills/`. The two prose examples inside fenced code blocks (`scan-deck` :40, `standup` :113) are illustrative, not live — change them only if the decision makes them wrong as documentation.
  - [ ] MECHANICAL: if the fix adds or widens an engine flag, `goc --help` describes its real scope (today `--max-rows` says "Cap rows per column in --board", which is accurate — do not widen the text without widening the behaviour).
  - [ ] MECHANICAL: mirrors re-synced (`pre-commit run --all-files`) and the OpenClaw port re-run (`python3 scripts/port_skills_to_openclaw.py`), so all five consumer trees carry the fix; `python3 scripts/port_skills_to_openclaw.py --check` is clean.
  - [ ] PROCESS: `uv run python -m unittest discover -s tests` and `uv run goc validate` both pass.
---

# Skill context blocks truncate deck output, hiding active cards and breaking JSON

## Location

Six live `!`-blocks, all in `goc/templates/skills/<skill>/SKILL.md`:

| Site | Query | Cap | Failure |
|---|---|---|---|
| `pull-card/SKILL.md:30` | `--status active -v` | `head -20` | drops cards from the soft-lock table |
| `pull-card/SKILL.md:42` | `--ready -v` | `head -22` | latent — fires at ~7 ready cards |
| `next-card/SKILL.md:17` | `--status active -v` | `head -20` | drops cards from the soft-lock table |
| `standup/SKILL.md:24` | `--status open --json` | `head -60` | invalid JSON |
| `refine-deck/SKILL.md:91` | `--status open --json` | `head -100` | invalid JSON |
| `retrospective/SKILL.md:17` | `--closed-since 90d --json` | `head -100` | invalid JSON |

Engine side: `--max-rows` (`goc/engine.py`, exposed in `_build_parser`) is
the only row bound the CLI has, and it is board-only —
`goc --help` says so verbatim: `Cap rows per column in --board.`

Two further `head -N` occurrences (`scan-deck/SKILL.md:40`,
`standup/SKILL.md:113`) sit inside fenced code blocks as prose examples.
They are not live context blocks and are out of scope except as
documentation.

## What's broken

Every one of these blocks bounds an **unbounded** engine stream with a
**fixed** line count. `head` is a byte-stream filter: it has no model of
what a card is, and no channel on which to say it removed anything.

### A. The soft lock silently loses cards

`pull-card/SKILL.md:30` renders the active-card table, and the body
immediately below it instructs:

> Treat any listed active card as a soft lock. Do not claim the same card,
> or adjacent/conflicting work, unless the user explicitly asks to continue
> that active card.

"any listed" is the whole mechanism — an active card that never reaches
the render is not listed, so the lock silently does not apply to it. On
this repo's deck today the engine emits 25 lines for 5 active cards
(each card is a row plus wrapped `summary:` and `worker:` lines under
`-v`); `head -20` forwards 20. The fifth card disappears completely and
the fourth is cut mid-sentence. Nothing in the forwarded text indicates a
loss — the table simply ends.

This session reproduced it live: the `Skill(pull-card)` render listed four
active cards, while `goc --status active` lists five.

### B. `--json` blocks forward a syntax error

`standup/SKILL.md:24` pipes a JSON document through `head -60`. The
document is 5,942 lines. The forwarded fragment stops mid-object, so it is
not short JSON — it is not JSON:

```
json.decoder.JSONDecodeError: Expecting property name enclosed in double
quotes: line 60 column 327 (char 2651)
```

`--slim` does not rescue these sites: `--status open --json --slim` is
still 3,020 lines and `--closed-since 90d --json --slim` is 7,356, both far
above the caps.

The contrast that makes this a defect rather than a limitation is the
board renderer, which bounds *and reports*:

```
… +178 more
```

That line exists because of the closed card
[`board-truncates-columns-to-max-rows-without-showing-how-many-are-hidden`](../board-truncates-columns-to-max-rows-without-showing-how-many-are-hidden/),
which established the repo convention: a renderer that hides rows must say
how many. The `!`-blocks reach for `head` precisely because no such bound
exists for the table and JSON renderers, and `head` cannot honour that
convention.

## Empirical evidence

`uv run python .game-of-cards/deck/skill-context-blocks-truncate-deck-output-hiding-active-cards-and-breaking-json/reproduce.py`:

```
=== pull-card/SKILL.md:30 — goc --status active -v | head -20 ===
  engine emitted 25 lines; the block forwards 20
  cards in full output: 5; after head: 4
  DEFECT: 1 card(s) vanished with no indicator:
    - terminal-status-guard-missing-across-mutation-verbs

=== pull-card/SKILL.md:42 — goc --ready -v | head -22 ===
  engine emitted 2 lines; the block forwards 2
  no truncation at this deck size

=== standup/SKILL.md:24 — goc --status open --json | head -60 ===
  engine emitted 5942 lines; the block forwards 60
  DEFECT: forwarded fragment is not valid JSON — Expecting property name
  enclosed in double quotes: line 60 column 327 (char 2651)

=== retrospective/SKILL.md:17 — goc --closed-since 90d --json | head -100 ===
  engine emitted 13029 lines; the block forwards 100
  DEFECT: forwarded fragment is not valid JSON — Expecting value: line 100
  column 13 (char 4939)

=== Verdict ===
  FAIL pull-card:30: head -20 hid 1 card(s) from a table the skill body calls a soft lock
  FAIL next-card:17: head -20 hid 1 card(s) from a table the skill body calls a soft lock
  FAIL standup:24: head -60 truncated a 5942-line JSON document into a syntax error
  FAIL refine-deck:91: head -100 truncated a 5942-line JSON document into a syntax error
  FAIL retrospective:17: head -100 truncated a 13029-line JSON document into a syntax error
```

The script re-reads each cap out of the shipped `SKILL.md` before testing
it, so it reports drift rather than silently passing if a site is edited.

## Why it matters

The reachability path is every session: these blocks are rendered by the
skill loader *before* the agent reads a word of the body, so the truncated
text is the agent's entire picture of deck state. There is no second
source it falls back to.

- **Failure A defeats the documented parallel-agent safety mechanism.**
  AGENTS.md § Parallel-Agent Commit Safety treats concurrent work on
  shared `main` as a real hazard, and the active-card table is the
  advertised soft lock against it. The lock degrades exactly when it is
  needed most — many cards claimed at once is precisely when the table
  overflows 20 lines. It also worsens with card quality: a long `summary:`
  wraps over more lines, so the better a card is written, the more of its
  neighbours it pushes out of view.
- **Failure B hands three skills a syntax error as their data source.**
  `standup`, `refine-deck` and `retrospective` are read-only reporting
  skills whose entire input is that JSON. An agent that cannot parse it
  either reports on the prefix it can salvage or silently reconstructs
  from the fragment — both produce a confident report over a partial deck.
- **It is a family, not a site.** Six blocks across four skills, each
  copied into five consumer trees (`.claude/`, `.codex/`,
  `claude-plugin/`, `codex-plugin/`, `openclaw-plugin/`). Fixing one site
  leaves the shape in place; this card exists so it is fixed once. Related
  but distinct:
  [`empty-queue-view-prints-nothing-instead-of-saying-no-cards-match`](../empty-queue-view-prints-nothing-instead-of-saying-no-cards-match/)
  (closed) fixed the *empty* end of the same render path.

## The closed family this instance belongs to

"A view bounds its output without reporting what it hid" has been fixed
four times already, each time at the **engine-renderer** layer, and each
time the same way — bound *and* report:

- [`board-truncates-columns-to-max-rows-without-showing-how-many-are-hidden`](../board-truncates-columns-to-max-rows-without-showing-how-many-are-hidden/) — added the `… +N more` row.
- [`board-truncates-worker-label-to-eight-characters`](../board-truncates-worker-label-to-eight-characters/)
- [`triage-decision-required-preview-silently-truncates-at-six-lines`](../triage-decision-required-preview-silently-truncates-at-six-lines/)
- [`triage-summary-fallback-preview-truncates-at-140-chars-without-indicator`](../triage-summary-fallback-preview-truncates-at-140-chars-without-indicator/)

All four are closed, which is why this card carries no umbrella edge and
no new root card was filed: there is nothing left to coordinate, only a
precedent to apply. What makes this instance the awkward one is the
layer — it lives in a **shell pipe inside a skill body**, where `head` has
no channel to report on and the engine has no bound to offer. That is the
gap the decision below has to close, and the four closed cards are the
evidence for which way to close it.

## Decision required

**How should a skill `!`-block bound live deck output?** The bug is
settled — truncating a JSON document into a syntax error is wrong under
any reading, and a soft-lock table that drops rows without saying so is
wrong under the convention the board already follows. What needs a pick is
the mechanism, because the credible options trade context budget against
engine surface differently.

- **Option 1 — teach the engine to bound, drop `head` entirely.**
  Generalize the row bound past the board: `--max-rows` (or a new
  `--limit`) applies to the table and JSON renderers, each reporting what
  it hid — `… +N more` for the table, a sibling count field for JSON.
  Blocks become `goc --status active -v --max-rows 8`.
  *For:* one mechanism, honours the established convention, keeps the
  context cap the blocks were reaching for. *Against:* widens the CLI
  surface and needs a JSON schema addition, which every JSON consumer
  then sees.
- **Option 2 — bound the query, not the output.** Leave the engine alone;
  make each block ask for less. `--slim` plus narrower filters for JSON;
  drop `-v` where the summary is not load-bearing. *For:* no engine
  change, no new flags. *Against:* does not actually fix it here —
  `--slim` is still 3,020 / 7,356 lines, so the JSON sites stay broken;
  and a query bound that depends on deck size is a cap that silently
  re-breaks as the deck grows.
- **Option 3 — no cap on the correctness-critical blocks, cap the rest.**
  The soft-lock table and the JSON dumps are unbounded (correctness), and
  only advisory blocks keep a cap. *For:* smallest change, and it is
  honest about which blocks may not be truncated. *Against:* unbounded
  context on a 715-card deck is a real cost — the `--closed-since 90d`
  dump alone is 13,029 lines, which is what the caps were defending
  against; it trades a silent-corruption failure for a context-blowout
  failure.

A pick that combines 1 and 3 (engine-level bound everywhere, plus "no cap"
on the soft-lock table specifically) is available and may be the right
answer; record it as such rather than as a variant of either.

Adjacent question the answer should also settle, since it is the same
mechanism: **should `goc` refuse to emit truncated JSON at all**, or is
bounding purely the caller's responsibility? Option 1 implies the former.
