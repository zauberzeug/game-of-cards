---
title: test-install-assertions-still-target-old-next-hint
summary: "Three assertions in tests/test_install.py still expect the pre-65e222b 'create a card for the next change' wording from the install command's Next: hint. The hint was intentionally redirected to 'expand the deck' in 65e222b but the tests were not updated, so CI has been red on every push since then."
status: active
stage: null
contribution: medium
created: 2026-05-05
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] All 3 assertions in tests/test_install.py for the install "Next:" hint match the current goc/install.py output (the "expand the deck" wording from 65e222b)
  - [ ] `uv run python -m unittest discover -s tests` passes locally with 0 failures
  - [ ] `uv run goc validate` passes
---

# tests/test_install.py asserts the pre-65e222b "Next:" hint

## Why

CI run https://github.com/zauberzeug/game-of-cards/actions/runs/25378542474
fails three install-smoke tests with:

```
AssertionError: 'Next: ask your LLM agent: "create a card for the next change I want to make."' not found in
'... Next: ask your LLM agent to "expand the deck" — it audits the repo and files initial cards. ...'
```

`goc/install.py:598` was intentionally rewritten in commit `65e222b
install: redirect "Next:" hint to extend-deck for fresh installs` —
that change was deliberate (the new flow leads with the audit-driven
extend-deck skill). But `tests/test_install.py` still asserts the
old single-targeted-card wording on lines 125, 184, 207. Pre-existing
CI red since 65e222b; surfaced when the next push (the homepage
redesign, 36954f9) re-ran the test job.

## What

Update the three assertions to assert against the current intended
output ("expand the deck" wording). Do not weaken the assertions to
just `Next:` — the *content* of the hint is the contract.

## Pointers

- Implementation: `goc/install.py:598`
- Failing assertions: `tests/test_install.py:125`, `:184`, `:207`
- Failing CI: https://github.com/zauberzeug/game-of-cards/actions/runs/25378542474
- Originating commit: `65e222b install: redirect "Next:" hint to extend-deck for fresh installs`
