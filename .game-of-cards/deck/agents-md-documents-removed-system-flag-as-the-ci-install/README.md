---
title: agents-md-documents-removed-system-flag-as-the-ci-install
summary: "AGENTS.md's Common-commands list documents the editable install as `uv pip install --system -e .` labelled '(what CI does)', but ci.yml no longer uses --system: it now installs into a setup-uv-activated .venv via plain `uv pip install -e .`. Update the line so the documented CI recipe matches reality."
status: done
stage: null
contribution: low
created: "2026-05-29T04:54:00Z"
closed_at: "2026-05-29T04:54:50Z"
human_gate: none
advances: []
advanced_by: []
tags: [documentation]
definition_of_done: |
  - [x] MECHANICAL: AGENTS.md Common-commands line no longer claims `--system` is "what CI does"
  - [x] MECHANICAL: the documented command matches ci.yml's actual install (plain `uv pip install -e .` into the project venv)
worker: {who: Rodja Trappe, where: main}
---

# agents-md-documents-removed-system-flag-as-the-ci-install

## What's stale

`AGENTS.md` "Common commands" listed:

```
uv pip install --system -e .       # editable install (what CI does)
```

But as of [`bump-deprecated-node-20-github-actions-before-forced-node-24-cutover`](../bump-deprecated-node-20-github-actions-before-forced-node-24-cutover/),
`ci.yml` no longer uses `--system`. The `setup-uv@v7` step now sets
`activate-environment: true`, which creates and activates a project
`.venv`, and the install step runs plain `uv pip install -e .` into that
venv. The `--system` form was actually *removed* from CI because newer
`uv` (bundled by setup-uv v7) rejects it against the GHA runner's
PEP-668 externally-managed system Python. So the comment's "(what CI
does)" claim is now wrong.

## Fix

Rewrite the line to match reality — plain `uv pip install -e .` into the
project venv (which `uv sync` on the line above already creates, and
which `uv pip install` auto-detects). Drop the `--system` flag from the
"what CI does" recipe.

## Why it matters

`AGENTS.md` is read cold by agents and contributors as the source of
truth for how to work in this repo. A doc line that mislabels a removed
flag as "what CI does" sends a reader toward a command that fails under
current `uv` on an externally-managed interpreter — exactly the
failure the parent card just debugged in CI.
