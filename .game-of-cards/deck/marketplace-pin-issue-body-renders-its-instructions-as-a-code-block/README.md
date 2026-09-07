---
title: marketplace-pin-issue-body-renders-its-instructions-as-a-code-block
summary: "The Marketplace Pin Check workflow builds its tracking-issue body as a double-quoted shell string whose continuation lines carry the YAML block's own 10-space indent, so everything after the first paragraph is indented four or more spaces and renders as one Markdown code block. The re-pin instructions, the submission URL and the workflow-run link all arrive as unclickable monospace source text on the only artifact the workflow exists to produce."
status: open
stage: null
contribution: low
created: "2026-08-31T01:22:51Z"
closed_at: null
human_gate: session
advances: []
advanced_by: []
tags: [bug, infra, documentation, unverified]
definition_of_done: |
  - [ ] EMPIRICAL: the rendering claim is confirmed or refuted — dispatch the
        workflow (or paste the expanded body into a scratch issue) and record in
        log.md whether the guidance renders as prose or as a code block; drop the
        `unverified` tag when it lands
  - [ ] MECHANICAL: the body is built so no continuation line carries leading
        indentation (a `<<-`/unindented heredoc, or `printf` with explicit `\n`),
        and a human with workflow-write permission pushes it
  - [ ] TDD: a check asserts no line of the generated body starts with four or
        more spaces, so the next edit to this block cannot silently re-indent it
---
# marketplace-pin-issue-body-renders-its-instructions-as-a-code-block

## Status: unverified — parked by an audit round without a rendering check

The shell expansion below is observed. What is *inferred* is how GitHub
renders the result: CommonMark turns a run of lines indented four or more
spaces after a blank line into an indented code block, and nothing about
this body escapes that rule. Nobody has looked at a rendered issue. The
`unverified` tag stays until someone does.

Surfaced by this audit round's own static sweep of `.github/workflows/`
(no subagent involved) while checking a different workflow defect; not
followed further because the fix cannot be landed by an agent (see below)
and the primary finding of the round was elsewhere.

## Location

`.github/workflows/marketplace-pin-check.yml:120-126` — the tracking-issue
body assembled inside the step's `run:` block.

## Hypothesis

The body is a double-quoted shell string spanning six lines. Its first
line starts at column 0 of the value, but every later line keeps the YAML
block scalar's own indentation — ten literal spaces, verbatim from the
file:

```yaml
          body="$stale_reason

          Marketplace users install the pinned commit, so they are not getting \`$tag\`.

          **What to do:** the marketplace repo is a read-only mirror (direct PRs are auto-closed). Request a re-pin via https://clau.de/plugin-directory-submission or coordinate with the marketplace maintainers (see issue #6 for the contact trail). This issue closes itself once the pin catches up.

          _Last checked: $(date -u +'%Y-%m-%d %H:%M UTC') · [workflow run]($GITHUB_SERVER_URL/$REPO/actions/runs/$GITHUB_RUN_ID)_"
```

The indentation is inside the quotes, so the shell keeps it. Expanding the
assignment with representative values and piping through `cat -A` (`$` marks
end-of-line) gives:

```
The marketplace pins [`abc1234`](...), which does **not** contain the latest release `v0.0.27`.$
$
          Marketplace users install the pinned commit, so they are not getting `v0.0.27`.$
$
          **What to do:** the marketplace repo is a read-only mirror (direct PRs are auto-closed). Request a re-pin via https://clau.de/plugin-directory-submission or coordinate with the marketplace maintainers (see issue #6 for the contact trail). This issue closes itself once the pin catches up.$
$
          _Last checked: 2026-08-31 01:22 UTC · [workflow run](https://github.com/zauberzeug/game-of-cards/actions/runs/1)_$
```

Blank lines inside an indented chunk do not end it, so lines 3-7 should
form a single code block: the `**What to do:**` emphasis, the
`https://clau.de/plugin-directory-submission` submission URL and the
`[workflow run](…)` link all render as literal source text rather than
as formatted, clickable prose. Only `$stale_reason` — substituted at
column 0 — renders normally.

## Why it matters

The tracking issue is the workflow's entire output. Its whole purpose is
to tell a maintainer *what to do* when a release has not reached
marketplace users, and the "what to do" half is the part that degrades:
the re-pin URL stops being a link exactly when someone needs to click it.
The failure is silent — the workflow exits 0, the issue exists, and only
a human reading it notices.

## Falsification recipe

1. `gh workflow run marketplace-pin-check.yml` on a state where the pin is
   stale and the release is older than `GRACE_HOURS` (or temporarily set
   `GRACE_HOURS: '0'` in a scratch branch), then open the issue it files.
2. Cheaper: `gh issue create --body "$(bash -c '<paste the body= assignment>')"`
   in a scratch repo and look at the rendered result.
3. Confirmed if the three guidance paragraphs render monospaced with their
   Markdown syntax visible; refuted if GitHub strips the shared indent.

## Why an agent cannot land the fix

GitHub refuses any push touching `.github/workflows/` from the autonomous
bot's App token, and naming the `workflows` scope in a `permissions:`
block breaks the workflow outright — established by
[workflows-write-in-yaml-permissions-block-breaks-autonomous-workflows](../workflows-write-in-yaml-permissions-block-breaks-autonomous-workflows/)
(closed). Human-gating workflow-file changes is the standing pattern here;
the sibling card
[marketplace-pin-check-crashes-on-repos-without-version-tags](../marketplace-pin-check-crashes-on-repos-without-version-tags/)
(open, gate `session`) is parked on the same constraint and edits the same
file, so both should be pushed in one human session.

Filed at `human_gate: session` rather than `none` for that mechanical
reason, not as a taste call: a `none` gate would put a card in the
autonomous drain queue that no autonomous run can close.

## Related

- [community-marketplace-pin-drifts-silently-behind-releases](../community-marketplace-pin-drifts-silently-behind-releases/)
  (done) — the card this workflow was built for.
