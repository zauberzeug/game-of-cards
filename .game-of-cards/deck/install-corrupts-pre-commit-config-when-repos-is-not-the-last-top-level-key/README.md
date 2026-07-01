---
title: install-corrupts-pre-commit-config-when-repos-is-not-the-last-top-level-key
summary: "`goc install`/`goc upgrade` call `_append_precommit_hook` (goc/install.py:1320), which appends its `- repo: local` hook block to the END of an existing `.pre-commit-config.yaml`, assuming the file ends with a block-style `repos:` list. That assumption breaks three ways, each producing invalid YAML that `pre-commit run` refuses to parse: (a) a top-level key *after* `repos:` (e.g. `default_language_version`, `exclude`, `fail_fast`); (b) an empty *inline* list `repos: []`; (c) no `repos:` key at all (e.g. only `ci:`). In every case the install silently corrupts the user's pre-commit configuration."
status: open
stage: null
contribution: medium
created: "2026-05-30T09:29:04Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [ ] PROCESS: decision recorded in `## Decision required` — parse-and-insert (load YAML, append into `repos:`, dump) vs. structured-text-insert (find `repos:` block end, splice before next top-level key) vs. error-out-with-instructions. Body should weigh round-trip preservation (comments, key order, quoting) against complexity. NOTE: option (2) as literally written ("splice before next top-level key") does not handle the `repos: []` inline-list or absent-`repos:` cases — the chosen mechanism must cover all three shapes below.
  - [ ] TDD: `reproduce.py` exits zero — appending the GoC hook to each of the three broken shapes (top-level key after `repos:`; empty inline `repos: []`; no `repos:` key at all) leaves a parseable, semantically-correct config in which the goc-validate hook is a member of `repos:`.
  - [ ] TDD: a regression test in `tests/` covers the three top-level keys observed in real pre-commit configs (`default_language_version`, `exclude`, `fail_fast`) appearing after `repos:`, the empty inline `repos: []` case, the absent-`repos:` case (e.g. a config with only `ci:`), plus the existing happy-path case where a block-form `repos:` is last.
  - [ ] MECHANICAL: the fix lands in `goc/install.py:1320` (`_append_precommit_hook`).
  - [ ] TDD: `uv run goc validate` passes.
---

# `goc install` corrupts `.pre-commit-config.yaml` when `repos:` is not the last top-level key

## Location

`goc/install.py:1320` — `_append_precommit_hook`.

```python
def _append_precommit_hook(target: Path) -> None:
    """Append (or refresh) the `goc validate` hook in `.pre-commit-config.yaml`."""

    if not (target.parent / ".git").exists():
        return
    if not target.exists():
        target.write_text("repos:\n" + PRE_COMMIT_HOOK)
        return
    text, newline = _read_text_keep_newline(target)
    if "id: goc-validate" in text:
        # ... refresh a drifted GoC-managed stanza in place, then return ...
        refreshed = _refresh_goc_validate_block(text)
        if refreshed != text:
            _write_text_keep_newline(target, refreshed, newline)
        return
    if not text.endswith("\n"):
        text += "\n"
    _write_text_keep_newline(target, text + PRE_COMMIT_HOOK, newline)
```

`PRE_COMMIT_HOOK` is the list item only (`  - repo: local\n    hooks:\n      ...`),
indented two spaces — i.e. it is meant to be a child of a block-style
`repos:` list. The final `text + PRE_COMMIT_HOOK` append only produces
valid YAML when the file *ends* with such a list. Three realistic
config shapes violate that precondition (see "What's broken").

## What's broken

The function works for the happy path: a fresh repo with no
`.pre-commit-config.yaml`, or one whose `repos:` block is a block-style
list that is the LAST top-level key in the file. In those cases,
appending the indented list item produces well-formed YAML.

Three realistic config shapes break it — all with the same root cause
(raw text-append that assumes a block-style `repos:` list at the file's
tail):

1. **Top-level key after `repos:`.** Real pre-commit configurations
   routinely carry other top-level keys
   ([pre-commit reference](https://pre-commit.com/#pre-commit-configyaml---top-level)):
   `default_language_version`, `default_stages`,
   `default_install_hook_types`, `exclude`, `fail_fast`, `files`,
   `minimum_pre_commit_version`, `ci`. When any such key appears
   *after* `repos:`, raw text-append places the new list item below it.
   The appended `- repo: local` is then a sibling at the document root
   — not a child of `repos:` — and the YAML is malformed.

2. **Empty inline list `repos: []`.** A valid, common starting point
   (`repos:` *is* the last/only key, but as an inline empty list).
   Appending an indented `- repo: local` under a scalar/inline-list
   mapping value produces `repos: []` immediately followed by a block
   sequence — invalid YAML.

3. **No `repos:` key at all.** Incremental pre-commit setups often
   carry only `ci:` or `default_language_version:` first. Appending a
   block sequence item to a pure mapping is invalid YAML, and even if
   it parsed the goc-validate hook would not be under any `repos:`.

Compounding the problem, `_append_precommit_hook` runs unconditionally
on `goc install` (and again on `goc upgrade`, `goc/install.py:1818`)
whenever the repo has a `.git` directory; there is no preflight check.
So the command silently rewrites the user's existing pre-commit config
into something `pre-commit run` refuses to parse.

## Empirical evidence

`reproduce.py` writes a realistic existing config:

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: trailing-whitespace

default_language_version:
  python: python3.11

exclude: '^vendor/'
```

…then calls `_append_precommit_hook` directly and reads the result.
Observed output (run 2026-05-30 on `main`):

```
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: trailing-whitespace

default_language_version:
  python: python3.11

exclude: '^vendor/'
  - repo: local
    hooks:
      - id: goc-validate
        ...
```

The `- repo: local` block is appended after `exclude: '^vendor/'`, not
inside `repos:`. The reproduce script's structural check returns exit 1.

Cross-checking with PyYAML directly:

```text
$ python3 -c "import yaml; yaml.safe_load(open('.pre-commit-config.yaml'))"
yaml.parser.ParserError: while parsing a block mapping
  in ".pre-commit-config.yaml", line 1, column 1
expected <block end>, but found '<block sequence start>'
  in ".pre-commit-config.yaml", line 11, column 3
```

`pre-commit` itself uses ruamel.yaml and fails with the same shape of
parse error, refusing to run any hooks.

The two additional shapes fail identically. Running
`_append_precommit_hook` directly (observed 2026-07-01 on `main`):

```
=== empty-inline-repos: input "repos: []\n" ===
repos: []
  - repo: local
    hooks:
      - id: goc-validate
        ...
  parses OK: False -> ParserError: while parsing a block mapping

=== no-repos-key: input "ci:\n  autofix_prs: true\n" ===
ci:
  autofix_prs: true
  - repo: local
    hooks:
      - id: goc-validate
        ...
  parses OK: False -> ParserError: while parsing a block mapping

=== block-repos (control) ===
  parses OK: True; goc-validate under repos: True
```

`reproduce.py` exercises all three broken shapes plus the block-form
control and exits 1 while any shape produces unparseable YAML.

## Why it matters — reachability path

`_append_precommit_hook` is called from
`goc/install.py:1571` inside the main `goc install` command (and from
`goc/install.py:1818` inside `goc upgrade`) — the canonical entry
points new consumers run. Consumers with a non-trivial
existing pre-commit config are exactly the audience most likely to
have multiple top-level keys (mature repos), so this is not a
hypothetical corner case. The corruption is silent: `goc install`
reports success, and the first failure surfaces only when the user
next runs `pre-commit run` (often on the *next* commit, well after the
install has scrolled out of the terminal).

The post-install pre-commit hook is also the gating mechanism for
`goc validate`. A corrupted config means `goc validate` does not run
on subsequent commits — exactly the safety net the install was meant
to wire up.

## Decision required

Three credible fix paths; need a human choice before implementing.

1. **Parse-and-insert with `_vendor/yaml_lite`** — load the existing
   YAML, append the goc-validate item under `repos:`, dump back. The
   project already ships a `yaml_lite` parser
   (`goc/_vendor/yaml_lite.py`) used by the frontmatter pipeline. Trade
   off: a YAML round-trip loses comments and may renormalize quoting /
   key order. The `yaml_lite` emitter is conservative but not a
   round-trip-preserving emitter.

2. **Structured-text splice** — find the line range that contains the
   `repos:` block (header + its indented children), find the index of
   the next top-level key (line that starts at column 0 and is not
   `repos:`), splice `PRE_COMMIT_HOOK` immediately before that index.
   Preserves comments and surrounding formatting; the regex for
   "next top-level key boundary" is small. Trade off: more code than
   today's two-liner; needs care around trailing blank lines inside
   the `repos:` block. **Caveat — as literally worded this option only
   covers shape (1).** It presumes a block-style `repos:` list exists
   to splice into; it does nothing for empty inline `repos: []` (shape
   2, where there is no block list to find the "end" of) or for a
   config with no `repos:` key at all (shape 3). Whichever mechanism is
   chosen must additionally rewrite `repos: []` into a block list and
   add a `repos:` block when none exists — so option (2) grows toward
   option (1)'s YAML-awareness for those shapes.

3. **Error out with instructions** — detect the "repos is not last"
   shape, print a one-screen explanation, and tell the user to insert
   the goc-validate hook by hand. The simplest fix, but trades silent
   corruption for friction.

The trade off matters: option (1) is the smallest diff but may upset
authors who care about their pre-commit config's exact text; option
(2) is the most respectful of existing content; option (3) is the
safest fall-through if the structural splice itself isn't trustworthy
in all cases.

Adjacent prior art: the marker-bounded `_append_marker_block` in the
same file uses a regex to *replace* an existing block, but the
pre-commit config has no marker convention to lean on — option (2)
would need to invent one or use the YAML structure as the boundary.
