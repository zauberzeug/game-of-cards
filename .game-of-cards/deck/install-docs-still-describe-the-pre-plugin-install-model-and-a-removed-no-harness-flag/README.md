---
title: install-docs-still-describe-the-pre-plugin-install-model-and-a-removed-no-harness-flag
summary: "ABOUT.md documented a --no-harness flag that goc install rejects (exit 2), said --agents claude writes .claude/skills/ and .claude/hooks/, and routed OpenCode to goc install --agents claude, while README.md routed OpenCode to plain goc install. Since the plugin became the Claude default neither invocation vendors a skill, and goc.md's skill count carried the same false parenthetical under a guard that required it verbatim (reproduce.py: six contradicted claims). ABOUT.md, README.md, goc.md and site/llms.txt now describe the plugin-default model and send OpenCode to goc install --agents claude --local-skills. tests/test_install_doc_claims.py runs every documented install flag and per-flag effect against a real install."
status: done
stage: null
contribution: high
created: "2026-09-28T01:34:50Z"
closed_at: "2026-10-03T05:13:07Z"
human_gate: none
advances:
  - doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them
advanced_by: []
tags: [bug, documentation, api-contract]
definition_of_done: |
  - [x] TDD: a reproduce.py extracts every install flag and per-flag effect `ABOUT.md` (lines 72-80), `README.md:46` and `goc.md:89` state, runs each against a scratch repo, and reports the claims the installer contradicts — or the run disproves the hypothesis and the card flips to `disproved`
  - [x] MECHANICAL: the three surfaces describe the plugin-default model: `--agents claude` writes no skills unless `--local-skills` is passed, `--no-harness` is gone, and OpenCode / generic-runner users are told which invocation actually vendors skill files
  - [x] TDD: `tests/test_guidance_accuracy.py`'s `test_claude_skill_count_matches_payload` no longer requires the false "(same as `goc install --agents claude`)" parenthetical to match; drop the `unverified` tag once reproduce.py lands
worker: {who: "claude[bot]", where: main}
---

# Install docs still describe the pre-plugin install model and a removed `--no-harness` flag

> Later evidence: the `--local-skills` help-text card this closure says was "Filed separately" was never filed — see [codex-install-guidance-predates-the-codex-plugin-and-its-bundled-engine](../codex-install-guidance-predates-the-codex-plugin-and-its-bundled-engine/).

## What was broken

Three reader-facing pages described `goc install` as it worked before
e69dc698 (2026-05-07) made the Claude Code plugin the Claude default:

- `ABOUT.md` § "Agent harnesses" said `--agents claude` writes
  `.claude/skills/` and `.claude/hooks/`, documented a `--no-harness` flag in
  a bullet and in the detection sentence, and said
  `goc install --agents claude` gives OpenCode the skill files.
- `README.md`'s Generic CLI bullet named plain `goc install` as "the path for
  OpenCode, custom runners, or running `goc` by hand".
- `goc.md`'s Claude plugin section said "**16 GoC skills** (same as
  `goc install --agents claude`)".

What the code does: `_should_use_local_skills` in `goc/install.py` returns
`agent != "claude" or local_skills`, so a Claude install vendors skills, hook
scripts and settings entries only with `--local-skills`. The install parser in
`goc/cli.py` defines no `--no-harness`. That flag was removed by
`claude-install-defaults-to-plugin-path`, which updated `AGENTS.md`,
`CLAUDE.md` and `goc.md` but not `ABOUT.md`.

So a scripted install copied from `ABOUT.md` exited 2. An OpenCode user who
followed either page got a repo with no skill files. The one guard on these
pages, `test_claude_skill_count_matches_payload`, matched the goc.md count
with a regex that required the false parenthetical verbatim, so correcting
the page turned CI red. `ABOUT.md` is published at `/about/` and linked from
`llms.txt`, so this was also what an LLM read when it installed GoC.

This is another member of
[doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them](../doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them/).

## Evidence

`reproduce.py` reads the install flags and per-flag effects out of the three
pages and runs each against a scratch repo. It lists every claim the
installer contradicts. Against the pre-fix tree (f27e415e) it exits 1:

```
checked 14 install claims across ABOUT.md, README.md, goc.md
  CONTRADICTED  ABOUT.md: names `--no-harness`, which `goc install` rejects (not in its --help usage)
  CONTRADICTED  ABOUT.md: says `goc install --agents claude` writes .claude/skills/, .claude/hooks/; a real install does not
  CONTRADICTED  ABOUT.md: `goc install --no-harness` exits 2: goc install: error: unrecognized arguments: --no-harness
  CONTRADICTED  ABOUT.md: routes OpenCode (which reads .claude/skills/) to an install that vendors no skill there: `goc install --agents claude` vendors 0
  CONTRADICTED  README.md: routes OpenCode (which reads .claude/skills/) to an install that vendors no skill there: `goc install` vendors 0
  CONTRADICTED  goc.md: '**16 GoC skills** (same as `goc install --agents claude`)' — `goc install --agents claude` vendors 0
```

Neither escape in the original falsification recipe fired: `--no-harness`
exits 2, and `goc install --agents claude` leaves no `SKILL.md`, no `.claude/`
directory, and `skills_source: plugin`. On the fixed tree the script checks
16 claims and exits 0.

## Fix

- `ABOUT.md` § "Agent harnesses":
  - The `--agents claude` bullet now says it writes `CLAUDE.md` and no skills
    or hooks.
  - A new `--agents claude --local-skills` bullet lists what vendoring writes.
  - `--no-harness` is gone from the bullets and from the detection sentence.
  - The OpenCode paragraph names `goc install --agents claude --local-skills`
    and says a plain `goc install` does not give OpenCode skills.
- `README.md` Generic CLI bullet: plain `goc install` is enough to run `goc`
  by hand. OpenCode and custom runners are sent to
  `goc install --agents claude --local-skills`.
- `goc.md`: the count's parenthetical now names the invocation that vendors
  those 16 skills. § "Install into a repo" gains a three-bullet list of what
  each harness writes.
- `site/llms.txt` § "Install (other agent runtimes / CI)", the canonical
  recipe `README.md` points to, gets the same OpenCode sentence.
- `tests/test_guidance_accuracy.py`: `test_claude_skill_count_matches_payload`
  now pins only the count, scoped to the Claude plugin section.
- New guard `tests/test_install_doc_claims.py`. It runs the claims rather than
  restating them, with four checks:
  - every flag a doc or shipped template names for `goc install` or
    `goc upgrade` must be in that verb's `--help` usage;
  - every harness bullet in `ABOUT.md` and `goc.md` must match what a scratch
    install with those flags writes;
  - every OpenCode route on an install page must name an invocation that
    vendors `.claude/skills/`;
  - goc.md's skill count must equal what its named invocation vendors.

  A second test feeds the pre-fix wording verbatim and requires all four
  checks to fire. Run against the pre-fix tree, the live test reports the
  same contradictions `reproduce.py` does, plus the bullet's
  one-hook-script-per-template clause.

## Surfaced while fixing

- `.github/workflows/pages.yml` embeds its own `llms.txt`, which still
  describes the old model. `site/llms.txt` overwrites it during the build, so
  the site does not serve it. Already tracked as
  [pages-workflow-embeds-stale-llms-txt-kept-off-the-site-only-by-copy-order](../pages-workflow-embeds-stale-llms-txt-kept-off-the-site-only-by-copy-order/).
- `goc install --help` describes `--local-skills` as "Default for Codex (no
  plugin yet)", and the `_should_use_local_skills` docstring says the same,
  though `codex-plugin/` ships. Filed separately (see `log.md`).
- `ABOUT.md`'s "Project state" bullet and its § Contributing still abbreviate
  the deck as `deck/`. Left alone: whether that short form stays is the open
  decision on
  [shipped-docs-abbreviate-the-deck-path-to-a-root-install-no-longer-creates](../shipped-docs-abbreviate-the-deck-path-to-a-root-install-no-longer-creates/).

## Post-close follow-up

The § Surfaced while fixing finding on `LOCAL_SKILLS_HELP`'s "no plugin yet"
said a card would be filed, and none was. The stale help text and docstring
were fixed by
[codex-install-guidance-predates-the-codex-plugin-and-its-bundled-engine](../codex-install-guidance-predates-the-codex-plugin-and-its-bundled-engine/),
and the Codex install-default question behind them is filed as [codex-install-defaults-to-plugin-path](../codex-install-defaults-to-plugin-path/).
