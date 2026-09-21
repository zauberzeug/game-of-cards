---
title: contributor-guide-sends-readers-to-a-conventions-file-that-holds-no-conventions
summary: "CONTRIBUTING.md routes human contributors to CLAUDE.md three times for project conventions, but CLAUDE.md is an 11-byte file holding one `@AGENTS.md` line — a Claude Code harness import that a human, a browser, or a non-Claude agent cannot follow, so the guide's central pointer lands on an empty page. Six more claim groups in the same file have drifted from the tree they describe: 4 source files (6), two plugin payloads (three; codex-plugin is never named), four release-rewritten manifests (five), a pre-commit set that omits the two card guards and claims a formatter that does not exist, `goc upgrade` named as the mirror-refresh mechanism when it writes into none of the three payloads, and a single-quote style rule the package violates in 94 percent of its string literals. CONTRIBUTING.md is the one reader-facing doc surface no accuracy guard has ever swept, and GitHub links it from every issue and pull-request form."
status: active
stage: null
contribution: high
created: "2026-09-21T01:18:50Z"
closed_at: null
human_gate: none
advances:
  - doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them
advanced_by: []
tags: [bug, documentation]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero — all seven claim groups agree with the tree; it exits 1 with eight FAIL lines before the fix.
  - [ ] MECHANICAL: the three `CLAUDE.md` pointers (lines 6, 50, 74) name the file that actually carries the conventions, and the file-role line at 5-7 describes `AGENTS.md` as the conventions document rather than only "deck workflow".
  - [ ] MECHANICAL: the tree-derived counts are corrected — source files under `goc/`, the plugin-payload roster (all three named at lines 16, 46 and 169-170), and the release-rewritten manifest count at 121.
  - [ ] MECHANICAL: both `pre-commit run --all-files` comments (lines 42, 91) name the four hooks that actually run and drop the formatter claim.
  - [ ] MECHANICAL: the coding-conventions bullets at 81-84 state the quote style the package uses and name the pre-commit sync hook — not `goc upgrade` — as the mirror-refresh mechanism.
  - [ ] TDD: a guard pins the tree-derived claims so this surface cannot rot again silently, and is fed a historical clause verbatim to prove it fires.
  - [ ] PROCESS: wired as a new instance row on [doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them](../doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them/) — the `advances` edge alone is not the table.
  - [ ] PROCESS: `uv run goc validate` passes and `uv run python -m unittest discover -s tests` is green.
worker: {who: "claude[bot]", where: main}
---

# The contributor guide sends readers to a conventions file that holds no conventions

## Location

`CONTRIBUTING.md`, seven claim groups:

| Line | Claim |
|---|---|
| 6, 50, 74 | `[CLAUDE.md](CLAUDE.md)` named as the project-conventions document |
| 14 | "The Python package is small (4 source files under `goc/`)" |
| 16, 46, 169-170 | "the two plugin payloads (`claude-plugin/`, `openclaw-plugin/`)" |
| 42, 91 | what `pre-commit run --all-files` runs |
| 81 | "Single quotes for strings; f-strings preferred." |
| 82-84 | "Edit `goc/templates/...` and re-run `goc upgrade`" as the mirror-refresh mechanism |
| 121 | "Rewrites the version literals in `goc/__init__.py` and the four plugin manifests." |

## What's broken

### The pointer that carries the most weight points at nothing

CONTRIBUTING.md is a routing document: it says so in its own second
sentence, and then routes.

```markdown
# CONTRIBUTING.md:4-7
This page is the short version — the long-form context lives in
[`README.md`](README.md) (methodology), [`AGENTS.md`](AGENTS.md) (deck workflow),
[`CLAUDE.md`](CLAUDE.md) (project conventions), and the header comment of
[`.github/workflows/release.yml`](.github/workflows/release.yml) (release machinery).
```

```markdown
# CONTRIBUTING.md:72-75
Project-specific conventions (template/mirror dogfooding, version
literals, marker-bounded merges, etc.) are documented in
[`CLAUDE.md`](CLAUDE.md). Read it before non-trivial changes — most
"surprises" in the codebase are dogfooding side effects that the file
already explains.
```

The file it names is eleven bytes:

```
$ cat -A CLAUDE.md
@AGENTS.md$
```

`@AGENTS.md` is a Claude Code harness import directive, not markdown.
Claude Code expands it into context; GitHub renders it as the literal
text `@AGENTS.md`; a human opening the file, a browser following the
relative link, and every non-Claude agent get one line and no
conventions. The three sites are not a stale filename — they are the
guide's entire conventions hand-off, and it terminates on an empty
page. AGENTS.md is where the content lives, and CONTRIBUTING.md
reduces it to "(deck workflow)" in the same sentence that routes past
it.

This is the repo's own documented arrangement, stated from the other
side:

> In this repo, `CLAUDE.md` intentionally contains only `@AGENTS.md` so
> Claude Code loads this shared file without duplicating the guidance.
> — `AGENTS.md:470-472`

So the arrangement is deliberate and correct; the guide that points
into it was written against a CLAUDE.md that no longer exists in that
form.

### Six more claim groups describe a tree that has moved

Each is a restatement of something derivable from the tree, and each
now disagrees with it:

- **`CONTRIBUTING.md:14`** — "4 source files under `goc/`". Six:
  `__init__.py`, `cli.py`, `engine.py`, `install.py`,
  `_vendor/__init__.py`, `_vendor/yaml_lite.py`. The vendored parser
  arrived with `replace-pyyaml-with-vendored-parser` and the count was
  never revisited.
- **`CONTRIBUTING.md:16, 46, 169-170`** — "the two plugin payloads
  (`claude-plugin/`, `openclaw-plugin/`)", repeated as "Don't edit
  `claude-plugin/` or `openclaw-plugin/goc/` directly." There are
  three. `codex-plugin/` is never named anywhere in the file, yet
  `scripts/sync_plugin_assets.py` regenerates `codex-plugin/goc` and
  `codex-plugin/hooks` from the same source-of-truth and CI fails on
  their drift exactly as it does for the other two. A contributor who
  reads the maintainer bullet literally concludes that editing
  `codex-plugin/` by hand is allowed.
- **`CONTRIBUTING.md:82-84`** — "Edit `goc/templates/...` and re-run
  `goc upgrade` rather than editing `.claude/skills/...` directly".
  `goc upgrade` writes into a *consuming* repo; `goc upgrade --dry-run`
  here plans **0** writes into any `*-plugin/` payload. The mechanism
  that actually regenerates the mirrors — and the one AGENTS.md names —
  is the `sync-plugin-assets` pre-commit hook, backed by
  `scripts/sync_plugin_assets.py --check` in CI. The bullet names a
  verb that covers one of the ten mirror destinations and none of the
  three payloads the same guide calls byte-for-byte mirrors.
- **`CONTRIBUTING.md:121`** — "the four plugin manifests".
  `scripts/release_rewrite_versions.py` rewrites five
  (`openclaw-plugin/package.json`, `openclaw-plugin/package-lock.json`,
  `claude-plugin/.claude-plugin/plugin.json`,
  `codex-plugin/.codex-plugin/plugin.json`,
  `.claude-plugin/marketplace.json`) plus two dogfood surfaces
  (`.game-of-cards/deck/.goc-version`, the `AGENTS.md` marker). The
  count matters because the paragraph below it describes the tripwire
  that fails a release on a human commit touching those files.
- **`CONTRIBUTING.md:42, 91`** — the two descriptions of
  `pre-commit run --all-files`: "sync plugin assets + goc validate" and
  "formats, mirrors plugin assets, runs goc validate". No hook runs a
  formatter, and both omit `card-language` and `card-frontmatter-yaml`.
  Those two are the hooks a new contributor is most likely to meet
  first: they reject a card at commit time, and `goc new --commit`
  shells out to `git commit` without `--no-verify`, so they fire on the
  filing path itself. AGENTS.md states the set correctly — "sync plugin
  assets + goc validate + card language + card YAML".
- **`CONTRIBUTING.md:81`** — "Single quotes for strings; f-strings
  preferred." 2085 of 2211 non-docstring string literals under `goc/`
  (94 percent) are double-quoted. A contributor who follows the stated
  rule writes code that does not look like the file it lands in.

## Empirical evidence

`reproduce.py` re-derives every claim from the tree — the source-file
walk, the payload roster, `sync_plugin_assets.SYNC_PAIRS`,
`release_rewrite_versions.py`'s target list, `.pre-commit-config.yaml`'s
hook ids, and a `tokenize` pass over the package — so it cannot itself
go stale against a moving tree:

```
$ uv run python .game-of-cards/deck/contributor-guide-sends-readers-to-a-conventions-file-that-holds-no-conventions/reproduce.py
CONTRIBUTING.md routes the reader to CLAUDE.md at lines: [6, 50, 74]
CLAUDE.md is 11 bytes: '@AGENTS.md\n'
  lines of prose in CLAUDE.md (excluding the @import): 0

CONTRIBUTING.md:14 claims 4 source files under goc/
  actual (6): goc/__init__.py, goc/_vendor/__init__.py, goc/_vendor/yaml_lite.py, goc/cli.py, goc/engine.py, goc/install.py

plugin payloads in the tree (3): claude-plugin, codex-plugin, openclaw-plugin
  named anywhere in CONTRIBUTING.md (2): claude-plugin, openclaw-plugin
  CONTRIBUTING.md:16 says 'the two plugin payloads'

mirror destinations the sync hook regenerates (10):
    .claude/hooks
    .claude/skills
    .claude/skills/_goc-bootstrap.sh
    .codex/skills/_goc-bootstrap.sh
    claude-plugin/goc
    claude-plugin/hooks
    claude-plugin/skills
    codex-plugin/goc
    codex-plugin/hooks
    openclaw-plugin/goc
  CONTRIBUTING.md:82 names `goc upgrade` as the refresh mechanism

CONTRIBUTING.md:121 says the release rewrites '`goc/__init__.py` and the four plugin manifests'
  release_rewrite_versions.py rewrites 5 manifests: .claude-plugin/marketplace.json, claude-plugin/.claude-plugin/plugin.json, codex-plugin/.codex-plugin/plugin.json, openclaw-plugin/package-lock.json, openclaw-plugin/package.json
  plus non-manifest targets: .game-of-cards/deck/.goc-version, AGENTS.md, goc/__init__.py

.pre-commit-config.yaml hooks (4): sync-plugin-assets, goc-validate, card-language, card-frontmatter-yaml
  CONTRIBUTING.md:42 describes it as: 'sync plugin assets + goc validate'
  CONTRIBUTING.md:91 describes it as: 'formats, mirrors plugin assets, runs goc validate'

CONTRIBUTING.md:81 states the style rule: 'Single quotes for strings; f-strings preferred.'
  single-quoted string literals under goc/: 126 (6%)
  double-quoted string literals under goc/: 2085 (94%)

FAIL: CONTRIBUTING.md sends readers to CLAUDE.md for project conventions at 3 sites, but CLAUDE.md carries 0 lines of prose — it is a bare `@AGENTS.md` import a non-Claude reader cannot follow
FAIL: claims 4 source files under goc/; the tree has 6
FAIL: CONTRIBUTING.md calls the mirror set 'the two plugin payloads' and never names codex-plugin
FAIL: CONTRIBUTING.md's coding-conventions bullet names `goc upgrade` as the mirror-refresh mechanism; `goc upgrade` plans no write into any *-plugin/ payload (it writes into a consuming repo), so it refreshes none of the three plugin mirror trees the same guide calls byte-for-byte
FAIL: claims the release rewrites 'four plugin manifests'; release_rewrite_versions.py rewrites 5
FAIL: CONTRIBUTING.md says `pre-commit run --all-files` 'formats'; no hook in .pre-commit-config.yaml runs a formatter
FAIL: both CONTRIBUTING.md descriptions of the pre-commit set omit card-language and card-frontmatter-yaml — the two hooks that reject a card a contributor just filed
FAIL: states 'Single quotes for strings' while 94% of the package's string literals (2085 of 2211) are double-quoted

8 finding(s) across 7 checked CONTRIBUTING.md claim groups.
```

Supporting run, for the `goc upgrade` clause:

```
$ uv run goc upgrade --dry-run | grep -c 'claude-plugin/\|codex-plugin/\|openclaw-plugin/'
0
```

## Why it matters

CONTRIBUTING.md is not an internal comment. GitHub surfaces it from
the issue form, the pull-request form and the repository sidebar, so
it is the first file an outside contributor opens — the one audience
the project has none of yet and says it wants
(`README.md:52`: the project asks people to install it and try it).
Every other instance of this family so far rotted on a surface an
existing contributor could route around; this one rots on the
on-ramp, and each of the seven groups misdirects a concrete action:
open the wrong file for conventions, hand-edit `codex-plugin/`, run
`goc upgrade` expecting the mirrors to refresh, trust a pre-commit
description that omits the hook about to reject the commit, write
single-quoted Python into a double-quoted package.

Two commits touched this file: `5c721dd6` created it and `a1ecb2f7`
rewrote only the release section. Nothing has swept the rest since,
and nothing can — the file appears in no guard, no parity test, and no
audit card. It is the fifteenth instance of
[doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them](../doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them/),
and it sharpens that card's open scope question in one specific way:
every group here except the quote rule and the CLAUDE.md pointer is
*mechanically derivable* — a file count, a directory roster, a
manifest list, a hook-id list. That is the cheap half the root card
calls "not just possible but cheap", sitting on a surface the root
card already names as in-scope for a sweep but which no sweep has run
over.

The CLAUDE.md pointer is the exception worth separating: it is not a
number that drifted but a cross-runtime assumption. A `@`-import is
readable by exactly one of the four runtimes this project ships for,
and the guide treats it as a document. The same shape would recur for
any repo whose briefing target is `CLAUDE.local.md` — `goc install`
offers that as a `--briefing-target` choice — so the fix should name
the conventions file, not patch a path.

## Fix

Mechanical, one file. Per group:

1. `CONTRIBUTING.md:6` — describe `AGENTS.md` as the conventions and
   deck-workflow document, and either drop the `CLAUDE.md` entry or
   annotate it as the Claude Code import shim it is. Repoint `:50` and
   `:74` at `AGENTS.md`.
2. `:14` — 6 source files.
3. `:16`, `:46`, `:169-170` — name all three payloads.
4. `:42`, `:91` — "sync plugin assets + goc validate + card language +
   card YAML" (the wording AGENTS.md already uses); drop "formats".
5. `:81` — double quotes.
6. `:82-84` — name the `sync-plugin-assets` pre-commit hook and the CI
   `--check`; keep `goc upgrade` only for the consuming-repo case it
   actually covers.
7. `:121` — five plugin manifests plus `goc/__init__.py` and the two
   dogfood surfaces.

Then add the guard the DoD asks for. `tests/test_guidance_accuracy.py`
is where this family's derive-from-tree assertions live; the five
mechanical groups (2, 3, 4, 6, 7) each have a one-line tree
derivation, which is why this instance is the cheapest yet to pin.
Groups 1 and 5 are prose judgements and are out of a derive-from-tree
guard's reach — note that in the closure entry rather than stretching
the guard to cover them.
