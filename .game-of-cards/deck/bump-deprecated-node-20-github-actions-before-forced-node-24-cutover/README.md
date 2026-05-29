---
title: bump-deprecated-node-20-github-actions-before-forced-node-24-cutover
summary: "GitHub flagged actions/checkout@v4 and astral-sh/setup-uv@v5 as running on the deprecated Node 20 runtime, which the runner force-migrates to Node 24 on 2026-06-02. Bump both pins (and the other Node-20 actions/* pins) to their current Node-24 majors across all workflows so CI keeps working past the cutover."
status: done
stage: null
contribution: medium
created: "2026-05-29T04:31:06Z"
closed_at: 2026-05-29T04:46:38Z
human_gate: none
advances: []
advanced_by: []
tags: [story, infra]
definition_of_done: |
  - [x] MECHANICAL: every `actions/checkout@v4` pin bumped to `@v6` across `.github/workflows/`
  - [x] MECHANICAL: every `astral-sh/setup-uv@v5` pin bumped to `@v7` across `.github/workflows/`
  - [x] MECHANICAL: `grep -rn "checkout@v4\|setup-uv@v5" .github/workflows/` returns no matches
  - [x] PROCESS: all workflow files still parse as valid YAML after the edit
  - [x] PROCESS: CI run d8a4b9d is fully green on the new pins — all 4 Python matrix jobs (3.10–3.13) pass with checkout@v6 + setup-uv@v7 on Node 24
worker: {who: Rodja Trappe, where: main}
---

# bump-deprecated-node-20-github-actions-before-forced-node-24-cutover

## What's flagged

A successful `pull-card.yml` run on 2026-05-29 emitted this runner annotation:

> Node.js 20 actions are deprecated. The following actions are running on
> Node.js 20 and may not work as expected: `actions/checkout@v4`,
> `astral-sh/setup-uv@v5`. Actions will be forced to run with Node.js 24 by
> default starting **June 2nd, 2026**. Node.js 20 will be removed from the
> runner on September 16th, 2026.

The annotation is per-run, so it only named the two actions that
`pull-card.yml` happens to use. A repo-wide grep shows the same two
action families pinned to Node-20 majors across every workflow.

## Location

`actions/checkout@v4` (9 occurrences):
`pages.yml:75`, `audit-deck.yml:37`, `pull-card.yml:48`,
`release.yml:186,450,598`, `ci.yml:29`, `claude.yml:29`,
`claude-code-review.yml:30`.

`astral-sh/setup-uv@v5` (5 occurrences):
`audit-deck.yml:42`, `ci.yml:38`, `release.yml:192,453`,
`pull-card.yml:53`.

## Fix

Bump both pins to the current **floating Node-24 major tag** (not a SHA
pin — matches the existing convention in these workflows). Both runtimes
confirmed `using: node24` at the pinned tag:

- `actions/checkout@v4` → `actions/checkout@v6` (floating `v6` tag exists)
- `astral-sh/setup-uv@v5` → `astral-sh/setup-uv@v7`

**Why `setup-uv@v7`, not `@v8`:** the releases API reports `v8.1.0` as
the newest release, but `astral-sh/setup-uv` does **not** publish a
floating `v8` major tag (only `v5`/`v6`/`v7` moving majors plus exact
`v8.x.x` tags). A first attempt at `@v8` failed CI at "Set up job" with
`Unable to resolve action astral-sh/setup-uv@v8, unable to find version
v8`. `v7` is the highest floating major that resolves, and it already
runs on Node 24. `actions/checkout` *does* publish a floating `v6`, so
`@v6` is correct there.

`checkout@v6` carries no behavioural change for our usage. `setup-uv@v7`
does: it bundles a newer default `uv` that refuses `uv pip install` into
a non-virtual environment (the GHA runner's system Python is PEP-668
externally-managed, so `--system` is also rejected). Applied fix in
`ci.yml`: set `activate-environment: true` on the `setup-uv@v7` step so
it creates and activates a `.venv` for the whole job (exported via
`GITHUB_PATH`/`GITHUB_ENV`); `uv pip install -e .` then targets that venv
and the later bare `goc --version` / `goc validate` steps resolve the
console script. The `uv sync`-based workflows (`pull-card.yml`,
`audit-deck.yml`) were unaffected — `uv sync` manages its own `.venv`.
(The interim `--system` attempt and the `@v8`-doesn't-resolve dead-end
are recorded in `log.md`.)

## Scope note — what is deliberately left out

`release.yml` and `pages.yml` also pin other Node-20-era actions
(`actions/setup-node@v4`, `actions/upload-artifact@v4`,
`actions/download-artifact@v4`, the `actions/*-pages-*` family). The
artifact actions in particular had a breaking v4 rewrite, and v4 is the
current widely-used line — bumping those is a separate, higher-risk
change that touches the OIDC trusted-publishing path. They were NOT
flagged by the annotation and are out of scope for this card. If they
start emitting the Node-20 warning closer to the 2026-09-16 removal,
file a follow-up that bumps them with a dedicated release dry-run.

## Why it matters

After 2026-06-02 the runner force-runs these on Node 24 regardless of
the pin; until then they emit a warning. After 2026-09-16 Node 20 is
removed from the runner entirely. Bumping now is a cheap, deadline-bound
chore that keeps `ci.yml`, `pull-card.yml`, `audit-deck.yml`, `pages.yml`,
and the three-registry `release.yml` green through both dates.
