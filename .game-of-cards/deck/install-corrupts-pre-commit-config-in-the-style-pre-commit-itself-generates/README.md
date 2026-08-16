---
title: install-corrupts-pre-commit-config-in-the-style-pre-commit-itself-generates
summary: "`goc install`/`goc upgrade` append a hard-coded two-space-indented `- repo: local` stanza to the end of an existing `.pre-commit-config.yaml` (`_append_precommit_hook`, goc/install.py:1340-1342) without reading the indentation the file's `repos:` list already uses. Every config whose list items start at column 0 — the style `pre-commit sample-config` emits, which pre-commit's own quickstart tells users to create — is corrupted: the four-space variant becomes unparseable YAML, and the two-space variant parses but silently nests the goc stanza inside the PREVIOUS repo's `hooks:` list. Both make `pre-commit` refuse the whole config, so every hook in the consuming repo stops running, goc-validate included."
status: open
stage: null
contribution: high
created: "2026-08-16T04:34:24Z"
closed_at: null
human_gate: decision
advances: []
advanced_by:
  - install-corrupts-pre-commit-config-when-repos-is-not-the-last-top-level-key
tags: [bug, infra, api-contract]
definition_of_done: |
  - [ ] PROCESS: the `## Decision required` below is resolved. It is the SAME mechanism question as [install-corrupts-pre-commit-config-when-repos-is-not-the-last-top-level-key](../install-corrupts-pre-commit-config-when-repos-is-not-the-last-top-level-key/) — decide once, for both cards. This card's contribution to that decision is a hard constraint: the mechanism must survive a config whose list items sit at column 0, which rules out any fix that only searches for the end of the `repos:` block without reading its indentation.
  - [ ] TDD: `reproduce.py` exits zero — the `goc-validate` hook is a member of the top-level `repos:` list for both column-zero shapes AND the existing two-space control, having exited 1 before the fix.
  - [ ] TDD: a regression test in `tests/` covers the two column-zero shapes verbatim — the exact output of `pre-commit sample-config` (items at column 0, four-space content) and the hand-written `- repo:` / two-space-content variant — plus the two-space control. The `pre-commit sample-config` case must be pinned as its own named test: it is the config pre-commit's quickstart tells every user to create, so a fix that handles only hand-written styles still fails the most common repo.
  - [ ] MECHANICAL: the fix lands in `_append_precommit_hook` (goc/install.py:1322-1342) and covers `goc install` (goc/install.py:1576) and `goc upgrade` (goc/install.py:1823) alike, since both call the same function.
  - [ ] MECHANICAL: `_refresh_goc_validate_block` (goc/install.py:1271-1297) is reconciled with the chosen mechanism. Its `_PRECOMMIT_LOCAL_BLOCK_RE` (goc/install.py:1265-1268) is anchored on the literal `^  - repo: local\n` with the same hard-coded two-space indent, so a stanza written at any other indentation is invisible to the refresh path and would never receive template fixes.
  - [ ] PROCESS: whichever of the two cards lands second records in its `log.md` that the shared fix closed it, so the pair does not read as two independent repairs.
  - [ ] TDD: `uv run python -m unittest discover -s tests` and `uv run goc validate` both pass.
---

# `goc install` corrupts a `.pre-commit-config.yaml` written in pre-commit's own default style

## Location

- `PRE_COMMIT_HOOK` — `goc/install.py:64-73` (the stanza, hard-coded at two-space indent).
- `_append_precommit_hook` — `goc/install.py:1322-1342` (the blind append).
- `_PRECOMMIT_LOCAL_BLOCK_RE` / `_refresh_goc_validate_block` — `goc/install.py:1265-1297`
  (the refresh path, anchored on the same hard-coded indent).
- Call sites: `goc/install.py:1576` (`install`) and `goc/install.py:1823` (`upgrade`).

## What's broken

`PRE_COMMIT_HOOK` is a list item frozen at two-space indentation
(`goc/install.py:64-73`):

```python
PRE_COMMIT_HOOK = """\
  - repo: local
    hooks:
      - id: goc-validate
```

`_append_precommit_hook` concatenates it onto the end of the file
(`goc/install.py:1340-1342`):

```python
    if not text.endswith("\n"):
        text += "\n"
    _write_text_keep_newline(target, text + PRE_COMMIT_HOOK, newline)
```

Nothing between those two points reads how the target file indents its own
`repos:` list. YAML has no canonical indentation for block sequences — items may
sit at column 0 under their parent key, and pre-commit's own generator emits
exactly that. `uv run --with pre-commit pre-commit sample-config`:

```yaml
# See https://pre-commit.com for more information
# See https://pre-commit.com/hooks.html for more hooks
repos:
-   repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v3.2.0
    hooks:
    -   id: trailing-whitespace
```

Appending a two-space item to that list produces one of two failures.

**Shape (d1) — column zero, four-space content (the `sample-config` output).**
The appended line is indented deeper than the sequence it is meant to join but
shallower than the mapping it lands inside, which is not a valid continuation of
either. The file stops parsing at goc's own line:

```
==> File .pre-commit-config.yaml
=====> while parsing a block mapping
  in "<unicode string>", line 3, column 1
did not find expected key
  in "<unicode string>", line 11, column 3
```

Line 11 column 3 is the `  - repo: local` that `goc install` just wrote.

**Shape (d2) — column zero, two-space content (common hand-written style).**
The file still parses, which is what makes this one worse. The two-space marker
is a legal sibling of the *previous repo's* `hooks:` items, so the goc stanza is
silently reparented into that repo's hook list:

```yaml
repos:
- repo: https://github.com/psf/black
  rev: 24.1.0
  hooks:
  - id: black
  - repo: local          # <- now an element of black's `hooks:`, not of `repos:`
    hooks:
      - id: goc-validate
```

`repos` ends up with one entry, not two. pre-commit rejects the result on schema
grounds instead of syntax:

```
==> At Config()
==> At key: repos
==> At Repository(repo='https://github.com/psf/black')
==> At key: hooks
==> At Hook(id=MISSING)
=====> Missing required key: id
```

Either way `pre-commit` refuses to load the config, so **every** hook in the
consuming repo stops running — the user's formatters and linters, and
`goc validate` itself, the gate that keeps card frontmatter from drifting.

The same hard-coded indent disables the repair path. `_PRECOMMIT_LOCAL_BLOCK_RE`
(`goc/install.py:1265-1268`) matches only `^  - repo: local`, so once a stanza
exists at any other indentation `_refresh_goc_validate_block` cannot see it, and
the `"id: goc-validate" in text` early return at `goc/install.py:1331` makes
every later `goc upgrade` a no-op over the damage.

## Empirical evidence

`uv run --with pyyaml python .game-of-cards/deck/install-corrupts-pre-commit-config-in-the-style-pre-commit-itself-generates/reproduce.py`
(PyYAML is what pre-commit itself parses with; the script falls back to
`goc._vendor.yaml_lite` when PyYAML is absent and says so):

```
parser: PyYAML

[affected] column-zero, four-space content — `pre-commit sample-config` output
    parser read it pristine   : True
    existing `- repo:` indent : 0 space(s)
    appended `- repo: local`  : 2 space(s)
    indentation matches       : False
    goc-validate in repos     : False (unparseable: ParserError: while parsing a block mapping)

[affected] column-zero, two-space content — common hand-written style
    parser read it pristine   : True
    existing `- repo:` indent : 0 space(s)
    appended `- repo: local`  : 2 space(s)
    indentation matches       : False
    goc-validate in repos     : False (absent from repos (list has 1 entry/entries) — the stanza landed somewhere else in the tree)

[control] two-space list items, `repos:` last — documented happy path (control)
    parser read it pristine   : True
    existing `- repo:` indent : 2 space(s)
    appended `- repo: local`  : 2 space(s)
    indentation matches       : True
    goc-validate in repos     : True (member of repos[1])

DEFECT PRESENT — 2 of 3 shape(s) corrupted:
  - column-zero, four-space content — `pre-commit sample-config` output
  - column-zero, two-space content — common hand-written style
```

All three shapes parse cleanly *before* `goc install` runs — the `parser read it
pristine: True` row rules out "PyYAML dislikes this style" as the explanation.
The control row shows the append is correct exactly when the file already uses
goc's assumed indentation.

End-to-end, outside the unit under test: `git init` a scratch repo, drop the
`pre-commit sample-config` output in as `.pre-commit-config.yaml`, run
`goc install --local-skills`, then
`uv run --with pre-commit pre-commit validate-config .pre-commit-config.yaml`.
It exits 1 with the parse error quoted above. Both pre-commit transcripts in
"What's broken" came from that route.

## Why it matters

This fires on the **default install path** against the **most likely existing
config**. pre-commit's documented quickstart is `pre-commit sample-config >
.pre-commit-config.yaml`, so a repo that already uses pre-commit most plausibly
carries column-zero list items — the one shape goc gets wrong. The user runs
`goc install` expecting a hook to be added and instead gets their entire
pre-commit setup disabled, with no error from goc: the install prints its normal
success banner, and the breakage only surfaces at the next `git commit`.

The failure is also self-concealing in the direction that matters to goc. The
hook this stanza is supposed to install is `goc validate`, the gate on card
frontmatter. A consuming repo whose config goc just broke has *no* deck
validation running, which is precisely the state the hook exists to prevent.

Reachability: no hand-authored YAML is needed to reach the offending input.
`_append_precommit_hook` reads whatever `.pre-commit-config.yaml` the repo
already has (`goc/install.py:1330`), and that file is written by pre-commit's own
generator or by hand — neither of which goc controls, and neither of which
guarantees two-space list items.

## Relationship to the sibling card

[install-corrupts-pre-commit-config-when-repos-is-not-the-last-top-level-key](../install-corrupts-pre-commit-config-when-repos-is-not-the-last-top-level-key/)
catalogues the same function and the same root habit (blind textual append), and
carries the mechanism decision. This card is filed separately rather than as
evidence on that one because it is **not** covered by it, in three ways:

1. That card enumerates three shapes, all characterised as "producing invalid
   YAML that `pre-commit run` refuses to parse". Shape (d2) here produces
   *valid* YAML with wrong semantics — there is nothing invalid to detect, so a
   fix validated by "does it still parse?" passes while the hook is silently
   unregistered.
2. All three of its shapes concern *where* the append lands relative to other
   top-level keys, and each assumes the `repos:` list itself is two-space
   indented. Shapes (d1)/(d2) break even when `repos:` is the last top-level key
   — that card's declared happy path and the control row above.
3. Its DoD pins the regression test to those three shapes by name. Closing it as
   written leaves both shapes here live.

The `advanced_by` edge records the real dependency: the mechanism gets decided
once, on that card, and this card supplies a constraint that decision has to
satisfy. They should land in one edit.

## Decision required

The mechanism is the sibling card's open question — parse-and-insert (load YAML,
append into `repos:`, dump) vs. structured-text-insert (locate the `repos:`
block, splice a correctly-indented item into it) vs. refuse-and-instruct. Do not
re-litigate it here. What this card adds is a constraint that narrows it:

**The chosen mechanism must derive the stanza's indentation from the target
file, not from a constant.** That has consequences per option:

- *Parse-and-insert* satisfies it for free (the dumper picks a consistent style),
  at the known cost of discarding comments and key order — including the two
  `# See https://pre-commit.com` lines `sample-config` writes.
- *Structured-text-insert* satisfies it only if it reads the existing list-item
  indent and re-indents `PRE_COMMIT_HOOK` to match. "Splice before the next
  top-level key" is not sufficient on its own: in shape (d2) there is no next
  top-level key, the splice point is the end of file, and the append still lands
  in the wrong list.
- *Refuse-and-instruct* satisfies it trivially but has to detect the unsupported
  shapes to refuse on, which is most of the work of doing it properly.

Whatever is chosen, `_PRECOMMIT_LOCAL_BLOCK_RE` must stop hard-coding
`^  - repo: local`, or the refresh path goes blind on every config it just
learned to write correctly.

## Fix sketch (for whichever mechanism wins)

Read the indentation once, re-indent the constant to match:

```python
_REPOS_ITEM_RE = re.compile(r"^(\s*)-\s+repo:", re.MULTILINE)

def _reindent_hook(text: str) -> str:
    """Re-indent PRE_COMMIT_HOOK to the list-item indent `text` already uses."""
    m = _REPOS_ITEM_RE.search(text)
    if m is None:
        return PRE_COMMIT_HOOK          # no existing item to match
    target_indent = m.group(1)
    return textwrap.indent(textwrap.dedent(PRE_COMMIT_HOOK), target_indent)
```

This is a sketch for the *indentation* half only. It does not address the three
shapes on the sibling card (where the splice point, not the indent, is wrong),
which is why the two cards want one combined fix rather than two patches to the
same function.
