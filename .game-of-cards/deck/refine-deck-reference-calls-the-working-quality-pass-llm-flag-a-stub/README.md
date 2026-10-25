---
title: refine-deck-reference-calls-the-working-quality-pass-llm-flag-a-stub
summary: "Skill(refine-deck)'s reference.md says the `goc quality-pass --llm` flag is 'Currently a stub', but it has run a real Sonnet audit since the 2026-05-04 package skeleton: it proposes title renames (applied through `goc move`) and summary and DoD rewrites, and `--yes` applies every one unreviewed. A reader who trusts the doc can run it as a no-op and rewrite live cards; the section should say what the pass does and name its `--dry-run`, `--yes` and `--limit` controls."
status: open
stage: null
contribution: low
created: "2026-10-25T04:54:16Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, documentation]
draft: true
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero (the section no longer calls the flag a stub and names every option the parser documents as "With --llm:").
  - [ ] TDD: `tests/test_guidance_accuracy.py` pins the same two checks against the template, and proves they fire on the pre-fix wording.
  - [ ] MECHANICAL: `goc/templates/skills/refine-deck/reference.md` § "Quality-pass `--llm` flag" describes what the pass sends, what it proposes, how rewrites are applied, its `--dry-run` / `--yes` / `--limit` controls and that closed cards are never sent.
  - [ ] MECHANICAL: mirrors re-synced and the OpenClaw port re-run; `scripts/sync_plugin_assets.py --check` and `scripts/port_skills_to_openclaw.py --check` are clean.
  - [ ] PROCESS: `uv run python -m unittest discover -s tests` green; `uv run goc validate` clean.
---

# Skill(refine-deck)'s reference calls the working `quality-pass --llm` flag a stub

## Location

`goc/templates/skills/refine-deck/reference.md` § "Quality-pass `--llm`
flag", the section `Skill(refine-deck)`'s routing table sends a reader
to for `goc quality-pass --llm`. The section is mirrored into
`.claude/skills/`, `.codex/skills/`, `claude-plugin/skills/`,
`codex-plugin/skills/` and `openclaw-plugin/skills/`.

## What's broken

The section reads:

```
The optional `--llm` flag on `goc quality-pass` is a hook for a
Sonnet-batched pass that extends the audit to summary quality +
per-DoD-item issues. Currently a stub. The regex-only mode is
sufficient as the always-on baseline; the batched LLM pass is a
nice-to-have, not load-bearing.
```

The engine has shipped a working pass since the 2026-05-04 package
skeleton (`bce18131`). `_run_sonnet_quality_pass` runs
`claude --model sonnet -p <prompt> --output-format json` over each
selected card's title, summary and DoD. `_apply_verdict_interactive`
then offers every proposed rewrite: a title rename runs `goc move`,
and summary and DoD fixes are written into the card's frontmatter. The
parser documents three options that only act with `--llm`:

```python
p_qp.add_argument("--limit", ..., help="With --llm: cap card count (testing/sampling).")
p_qp.add_argument("--dry-run", ..., help="With --llm: print verdicts; skip the interactive accept/reject walk.")
p_qp.add_argument("--yes", ..., help="With --llm: auto-accept every proposed rewrite (use with care).")
```

The section names none of them. The "stub" wording shipped with the
first skill templates (`94975556`, 2026-05-04), the same day as the
engine that already ran the pass. It survived the 2026-07-11 move into
`reference.md` (`8a1af2f5`) and a 2026-09-20 trim by
`installed-files-point-readers-at-a-deck-folder-install-never-creates`
(`64c2dacd`) that kept the claim.

## Empirical evidence

`reproduce.py` checks the section against the parser. On `main`
(2026-10-25):

```
[DRIFT] calls the flag a stub, but _run_sonnet_quality_pass runs `claude` and _apply_verdict_interactive writes accepted rewrites
[DRIFT] never names --limit, which the parser documents as 'With --llm: ...'
[DRIFT] never names --dry-run, which the parser documents as 'With --llm: ...'
[DRIFT] never names --yes, which the parser documents as 'With --llm: ...'
```

Exit codes: 0 = section matches the engine, 1 = drift present, 2 =
harness broken.

## Why it matters

A reader told the flag is inert has no reason to hold back:
`goc quality-pass --status all --llm --yes` then renames titles and
rewrites summaries and DoD items on every live card it selected, with
no review. Since
[goc-quality-pass-mutates-summary-and-dod-on-terminal-status-cards](../goc-quality-pass-mutates-summary-and-dod-on-terminal-status-cards/)
closed cards are never sent to the model. The section is also the
only shipped description of the flag, so a reader who wants to use
it on purpose has nothing to learn the `--dry-run` / `--yes` controls
from.

Surfaced while closing that card, which changed what `--llm` sends.

## Fix

Rewrite the section to describe the pass as shipped: what it sends to
`claude --model sonnet -p` and the prerequisite (`claude` on PATH and
logged in), the three kinds of proposal, how accepted ones are
applied, `--dry-run` / `--yes` / `--limit`, and that closed cards are
never sent. Keep the existing judgement that the regex scan is the
always-on baseline and the LLM pass is optional. Re-sync the mirrors
and re-run the OpenClaw porter. Pin the two drift checks in
`tests/test_guidance_accuracy.py`, deriving the option list from the
parser so a future `With --llm:` option is covered on the day it
lands.
