---
title: attest-closure-marker-check-rejects-ascii-hyphen-headings-as-missing
summary: "The `log-md-closure-entry` derived check in `goc attest` matches the closure heading with a hard-coded U+2014 em-dash separator (goc/engine.py:4720-4733), so a closure entry written with an ordinary ASCII hyphen (`## <date> - Closure`) fails the check as 'missing'. The diagnostic asserts the section is absent when it is present but mis-punctuated, sending the closer hunting for a section they already wrote. The fix approach (loosen the separator match vs. keep strict and diagnose the near-miss) awaits the decision this card is gated on."
status: open
stage: null
contribution: medium
created: "2026-06-29T02:23:40Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] TDD: a regression test asserts the `log-md-closure-entry` derived check distinguishes a closure heading that is *present but mis-punctuated* (ASCII hyphen `-`) from one that is genuinely absent — per the resolution recorded in the `## Decision` block.
  - [ ] TDD: reproduce.py reflects the resolved behavior (exits zero pre-fix to prove the defect; updated to assert the fixed behavior after the fix lands).
  - [ ] PROCESS: the fix approach (loosen the separator match vs. keep strict + emit a diagnosing message vs. both) is decided and recorded in log.md before code changes.
  - [ ] MECHANICAL: `uv run goc validate` clean; plugin mirrors synced (`python scripts/sync_plugin_assets.py --check`).
---

# `goc attest`'s closure-marker check rejects an ASCII-hyphen heading as "missing"

## Summary

The `log-md-closure-entry` derived check (run by `goc attest`, a default
layer-3 GoC check) matches the Step-4 closure journal heading with a regex
whose separator is a hard-coded Unicode em-dash (`—`). A closure entry
written with an ordinary ASCII hyphen (`## 2026-06-29 - Closure`) — the
character most editors and agents emit by default — fails the check, which
then reports `no '## <date> — Closure' section`. The diagnostic asserts the
section is **missing** when it is actually **present but mis-punctuated**,
sending the closer hunting for a section they already wrote.

## Location

`goc/engine.py:4720-4733` (`_run_derived_check`, `name == "log-md-closure-entry"`):

```python
date_prefix = _date_part(today)
# Match either legacy date-only (`## YYYY-MM-DD — Closure`) or the
# current datetime form (`## YYYY-MM-DDTHH:MM:SSZ — Closure`).
pattern = re.compile(
    rf"^## {re.escape(date_prefix)}(?:T\d{{2}}:\d{{2}}:\d{{2}}Z)? — Closure",
    re.MULTILINE,
)
if pattern.search(log_path.read_text()):
    return True, f"'## {date_prefix} — Closure' present"
return False, f"no '## {date_prefix} — Closure' section"
```

The literal ` — Closure` in the pattern is a U+2014 EM DASH framed by spaces.
There is no normalization of the separator and no near-miss detection: the
match is all-or-nothing on the exact byte sequence.

## What's broken

The `finish-card` skill (`Step 4 — append closure context to log.md`)
instructs the closer to write:

```markdown
## YYYY-MM-DDTHH:MM:SSZ — Closure
```

with a Unicode em-dash. `goc attest` (Step 5) then greps for that heading via
the regex above. The two steps are split across a human/agent-authored write
and a machine read, and the *only* shared contract between them is the exact
em-dash character. An ASCII hyphen — trivially substituted by autocorrect-off
editors, terminals, copy-paste from plain-text sources, or an LLM that emits
`-` by default — breaks the contract silently.

The failure message compounds the defect: it says the closure section is
absent (`no '## <date> — Closure' section`) when the section is right there
in `log.md`. A closer reading that message will re-add a closure entry,
re-attest, and fail again, with no hint that the problem is one character.

## Empirical evidence

`uv run python .game-of-cards/deck/attest-closure-marker-check-rejects-ascii-hyphen-headings-as-missing/reproduce.py`:

```
A closure section IS present in both logs (greppable for ' Closure'):
  ascii-hyphen log has a Closure heading: True
  em-dash    log has a Closure heading:   True

Derived-check verdict (True = PASS, the check finds a closure entry):
  em-dash heading      -> True
  ascii-hyphen heading -> False

On the ascii-hyphen log the check FAILS with the message:
  "no '## 2026-06-29 — Closure' section"
  ...even though a closure section is plainly present — the diagnostic
  claims the section is MISSING when it is only mis-punctuated.

DEFECT REPRODUCED: True
```

## Why it matters

Reachability is direct and shipping: `goc attest` is invoked by Step 5 of the
`finish-card` skill on every closure, and `log-md-closure-entry` is one of the
three default layer-3 checks in the shipped `config.yaml`
(`goc/templates/game_of_cards/config.yaml`). The closure heading is authored
by hand (human or agent) per the skill template, so the offending input — an
ASCII-hyphen heading — is produced by the routine closure flow whenever the
author's tooling does not emit a U+2014. A failed attest blocks closure
(`exits non-zero; finish-card will block closure`), so the cost is a stalled
close plus debugging time spent chasing a "missing" section that exists.

This is a sibling of
[closure-log-attestation-misfires-across-utc-midnight](../closure-log-attestation-misfires-across-utc-midnight/),
which covers a *different* over-strictness axis of the same check (the
date-prefix coupling to wall-clock `today`). That card is about *when* the
heading is dated; this card is about *how* the separator is punctuated. Both
share the root shape: the `log-md-closure-entry` regex is brittle and its
miss-message conflates "absent" with "non-matching". Two instances so far —
not yet a meta-fix family.

## Decision required

The check should stop reporting a present-but-mis-punctuated heading as
missing. Three credible fix paths:

1. **Loosen the separator match.** Accept common dash variants
   (em-dash `—`, en-dash `–`, ASCII hyphen `-`, double-hyphen `--`) with
   surrounding-space tolerance, e.g. `\s*[—–-]+\s*Closure`. Pro: closures
   succeed regardless of the author's dash. Con: drifts from the single
   documented canonical heading shape; the journal accumulates inconsistent
   punctuation.

2. **Keep the regex strict; fix the diagnostic.** When the strict pattern
   misses, run a looser probe (a `## <date> ... Closure` heading with any
   separator). If the looser probe hits, return a *diagnosing* failure —
   "found a closure heading dated <date> but its separator is not the
   em-dash `—` the template prescribes; replace `-` with `—`" — instead of
   the misleading "no section". Pro: preserves the canonical format and turns
   a silent failure into an actionable one. Con: closures still block until
   the author fixes the character (arguably correct — enforce the format).

3. **Both** — loosen the match AND keep a canonicalization hint, so closures
   never block on the dash but the author is nudged toward the em-dash.

Recommendation: option 2 (strict match, diagnosing message) most cleanly
honors the "one documented heading shape" contract while removing the
factually-wrong "missing" diagnostic; option 1 trades format consistency for
convenience. Decide before implementing.
