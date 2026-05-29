---
title: openclaw-session-start-frontmatter-reader-truncates-colon-bearing-values-via-typescript-split-limit
summary: "The OpenClaw session-start hook's frontmatter reader at `openclaw-plugin/index.ts:192-202` calls `line.split(\":\", 2)[1]` for status / human_gate / waiting_on / waiting_until. TypeScript's `String.prototype.split(sep, limit)` truncates the result *array* to `limit` elements — it does NOT cap the number of splits the way Python's `str.split(sep, maxsplit)` does. So `\"waiting_until: 2026-06-15T12:00:00Z\".split(\":\", 2)` yields `[\"waiting_until\", \" 2026-06-15T12\"]` — everything past the second colon is dropped. The downstream `parseWaitingUntil` then fails both ISO regexes and returns null, and a card with a bare datetime-form `waiting_until` (no `waiting_on` reason) is misclassified as resumable instead of impeded. The Python sibling at `goc/templates/hooks/deck_session_start.py:81` correctly uses `split(\":\", 1)` (maxsplit=1) and reads `[1]`, capturing the full tail. The TS port copied the Python literal `2` without translating split-limit semantics. Today only `waiting_until` carries colon-bearing values; status / human_gate / waiting_on are latent fragility against any future colon-bearing enum or migration shape."
status: done
stage: null
contribution: medium
created: "2026-05-29T22:50:29Z"
closed_at: "2026-05-29T22:56:51Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero (post-fix, a `status: active` card with bare datetime-form `waiting_until` is classified as impeded; pre-fix exits non-zero showing the card incorrectly classified as resumable).
  - [x] MECHANICAL: all four `line.split(":", 2)[1].trim()` call sites in `openclaw-plugin/index.ts:192-202` switched to a semantic that captures the full post-`:` tail (e.g. `line.slice(line.indexOf(":") + 1).trim()` or a shared helper that mirrors Python `split(":", 1)[1]`). The comment / docstring above the loop names the engine contract being mirrored.
  - [x] PROCESS: cross-reference recorded — this card cites the closed siblings `session-start-hook-misreads-same-day-datetime-waiting-until-as-not-impeded` and `deck-session-start-hook-strips-quotes-asymmetrically-across-frontmatter-readers` (both touched the same four readers; this is the next instance in the family).
  - [x] MECHANICAL: `npx tsc --noEmit` from `openclaw-plugin/` is clean, and `uv run python -m unittest discover -s tests` stays green.
  - [x] PROCESS: a generalization check: confirm no other TS file in the tree uses `.split(<sep>, N)[N-1]` expecting Python-style maxsplit semantics on a colon-bearing input. If found, file siblings.
worker: {who: "claude[bot]", where: main}
---

# OpenClaw session-start frontmatter reader truncates colon-bearing values via TypeScript split-limit

## Location

`openclaw-plugin/index.ts:192-202` — the four-line `if/else` ladder inside `findActiveCards` that reads `status`, `human_gate`, `waiting_on`, and `waiting_until` from each frontmatter line.

## What's broken

The four readers all use the same shape:

```ts
for (const line of m[1].split("\n")) {
  if (line.startsWith("status:")) {
    status = stripQuotes(line.split(":", 2)[1].trim());
  } else if (line.startsWith("human_gate:")) {
    const val = stripQuotes(line.split(":", 2)[1].trim());
    if (val) humanGate = val;
  } else if (line.startsWith("waiting_on:")) {
    waitingOn = stripQuotes(line.split(":", 2)[1].trim());
  } else if (line.startsWith("waiting_until:")) {
    waitingUntil = stripQuotes(line.split(":", 2)[1].trim());
  }
}
```

`String.prototype.split(separator, limit)` in TypeScript / ECMA-262 truncates the resulting array to `limit` elements; it does **not** cap the number of splits performed. So:

```
"waiting_until: 2026-06-15T12:00:00Z".split(":", 2)
  // => ["waiting_until", " 2026-06-15T12"]
```

Everything past the second `:` is dropped from the array. The Python sibling reads the same field via `split(":", 1)[1]`:

```python
# goc/templates/hooks/deck_session_start.py:81
val = line.split(":", 1)[1].strip().strip('"').strip("'")
```

Python's `str.split(sep, maxsplit)` second arg is the *maximum number of splits*, so `"waiting_until: 2026-06-15T12:00:00Z".split(":", 1)` correctly returns `["waiting_until", " 2026-06-15T12:00:00Z"]` and `[1]` is the full timestamp. The TS port copied the literal `2` from an earlier Python form (or from the four-element Python split contract) without translating the semantic; the two languages name nearly-identical functions with non-identical contracts.

Downstream of the truncation, the TS `parseWaitingUntil` at `openclaw-plugin/index.ts:138-149` is asked to parse `"2026-06-15T12"`:

```ts
function parseWaitingUntil(value: string): Date | null {
  if (ISO_DATETIME_UTC_RE.test(value)) { /* ... */ }
  if (ISO_DATE_RE.test(value)) { /* ... */ }
  return null;
}
```

Both regexes fail (the datetime regex needs the `:MM:SSZ` tail, the date regex rejects the `T12` suffix) and the function returns `null`. `isImpeded` at `openclaw-plugin/index.ts:151-163` then evaluates:

- `untilDt = null`, `untilFuture = false`.
- For a bare-deferral card (`waiting_on: ""`), `IMPEDED_WAITING_ON.has("")` is false.
- Returns `untilFuture` → `false`. **Card NOT impeded.**

The engine contract at `goc/engine.py:1751` (`waiting_impedes`) says the opposite for the same shape:

```python
if reason is None and until_dt is None:
    return until_unparseable
if until_dt is None:
    # Reason set, no date — open-ended wait; hide from queue.
    return True
# Future instant hides; elapsed instant resurfaces the card.
return until_dt > now
```

A card with `waiting_until` set to a future instant (and no `waiting_on` reason) is hidden from queues. The TS port surfaces it as resumable.

## Empirical evidence

`uv run python .game-of-cards/deck/openclaw-session-start-frontmatter-reader-truncates-colon-bearing-values-via-typescript-split-limit/reproduce.py`:

```
# 1) Split-limit semantic demonstration
  input:                          'waiting_until: 2026-06-15T12:00:00Z'
  JS  split(':', 2):              ['waiting_until', ' 2026-06-15T12']
  Py  split(':', 1):              ['waiting_until', ' 2026-06-15T12:00:00Z']
  JS  [1].strip()                 -> '2026-06-15T12'
  Py  [1].strip()                 -> '2026-06-15T12:00:00Z'
  JS  parseWaitingUntil parses?   False
  Py  parseWaitingUntil parses?   True

# 2) Bug presence check in openclaw-plugin/index.ts
  call sites with split(":", 2)[1].trim(): 4

# 3) Engine-contract divergence for the bare-deferral case
  card frontmatter: status: active / waiting_until: 2030-01-01T00:00:00Z / waiting_on absent
  engine.waiting_impedes(card)  -> True  (card hidden from queues)
  ts.isImpeded(...) (pre-fix)    -> False (BUG: surfaces as resumable)

VERDICT: pre-fix. Split-limit truncation present in 4 reader(s); datetime-form waiting_until is lost. exit 1.
```

Exit code 1 pre-fix (4 truncating call sites; the datetime-form value `2026-06-15T12:00:00Z` is collapsed to `2026-06-15T12` which fails both ISO regexes). Exit code 0 once all four readers use a non-truncating semantic.

## Why it matters

Reachability is direct and current:

1. An operator runs `uv run goc wait <title> --until 2030-01-01T00:00:00Z` (datetime form, no `--reason`).
2. The frontmatter emitter at `goc/engine.py` writes `waiting_until: 2030-01-01T00:00:00Z` into the card.
3. The operator starts a new agent session in OpenClaw.
4. The TS session-start hook at `openclaw-plugin/index.ts` reads the deck, applies the split-limit truncation, and lists the card as resumable.
5. The agent sees `[GoC] Active card(s): <title> — resume or close before starting new work.` for a card the engine deliberately hides from `goc --ready` until the deferral instant elapses.

Cross-host parity is a stated goal of the TS port; the `isImpeded` docstring at `openclaw-plugin/index.ts:152-155` advertises "Mirrors `goc.engine.waiting_impedes` across the four-cell `waiting_on × waiting_until` matrix at full UTC timestamp precision." That mirroring is broken upstream of `isImpeded`, in the line-split that feeds it.

This is a sibling-sweep finding on top of two closed cards:

- [`session-start-hook-misreads-same-day-datetime-waiting-until-as-not-impeded`](../session-start-hook-misreads-same-day-datetime-waiting-until-as-not-impeded/) — fixed `parseWaitingUntil` precision but left the truncating call site alone.
- [`deck-session-start-hook-strips-quotes-asymmetrically-across-frontmatter-readers`](../deck-session-start-hook-strips-quotes-asymmetrically-across-frontmatter-readers/) — added `stripQuotes` symmetrically across the four TS readers but did not touch the underlying `split(":", 2)` shape.

The split-limit defect was carried through both fixes because each was scoped to a narrower concern.

The other three readers (`status`, `human_gate`, `waiting_on`) are not symptomatic today because their canonical enum values contain no colon. They will become symptomatic the moment any colon-bearing value (a timestamped reason, a URI-shaped status flag, a future schema extension) lands. Fixing all four together avoids relitigating the same shape per-field.

## Fix

Replace each of the four `line.split(":", 2)[1].trim()` expressions with a `split(":", 1)`-equivalent shape. The minimal mechanical fix (sketch):

```ts
function frontmatterTail(line: string): string {
  const i = line.indexOf(":");
  return i < 0 ? "" : line.slice(i + 1).trim();
}

for (const line of m[1].split("\n")) {
  if (line.startsWith("status:")) {
    status = stripQuotes(frontmatterTail(line));
  } else if (line.startsWith("human_gate:")) {
    const val = stripQuotes(frontmatterTail(line));
    if (val) humanGate = val;
  } else if (line.startsWith("waiting_on:")) {
    waitingOn = stripQuotes(frontmatterTail(line));
  } else if (line.startsWith("waiting_until:")) {
    waitingUntil = stripQuotes(frontmatterTail(line));
  }
}
```

The helper makes the "everything after the first `:`" intent explicit and de-duplicates the shape across the four readers, mirroring the Python hook's `split(":", 1)[1]` semantic without re-introducing the same trap.

The accompanying docstring / loop comment should name the engine contract and the `split` semantic that motivated the helper — so the next porter does not regress to `split(":", N)[N-1]`.
