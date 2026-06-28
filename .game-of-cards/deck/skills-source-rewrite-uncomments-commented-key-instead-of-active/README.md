---
title: skills-source-rewrite-uncomments-commented-key-instead-of-active
summary: "`_write_skills_source` uses one `#?`-optional regex plus `count=1`, so it rewrites whichever `skills_source:` line comes first in document order. When a commented documentation example precedes the active key, the comment is un-commented to the new value and the real active setting is left stale — producing two conflicting `skills_source:` keys (ambiguous YAML; the requested mode switch silently fails)."
status: done
stage: null
contribution: medium
created: "2026-06-07T04:58:21Z"
closed_at: "2026-06-07T05:01:38Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero (active key rewritten, no duplicate `skills_source:` key)
  - [x] TDD: a regression test in tests/test_install.py asserts `_write_skills_source` rewrites the active line (not a preceding comment) when both a commented example and an active key are present, and still un-comments a comment-only config
  - [x] MECHANICAL: `_write_skills_source` prefers the active (non-commented) line, falling back to a commented line only when no active line exists; the docstring's "replace the value if a (commented or active) line already exists" promise is honored without creating a duplicate key
---

# `_write_skills_source` un-comments a doc example instead of rewriting the active key

## Location

`goc/install.py:1356-1362` — the rewrite logic inside `_write_skills_source`.

## What's broken

`_write_skills_source` pins the `skills_source:` key in
`.game-of-cards/config.yaml` by treating the file as line-oriented text.
Its docstring promises to *"replace the value if a (commented or active)
line already exists."* The implementation is:

```python
pattern = re.compile(r"^[ \t]*#?[ \t]*skills_source[ \t]*:.*$", re.MULTILINE)
replacement = f"skills_source: {value}"
if pattern.search(text):
    new_text = pattern.sub(lambda _: replacement, text, count=1)
else:
    sep = "" if text.endswith("\n") else "\n"
    new_text = f"{text}{sep}\n{replacement}\n"
```

The `#?` makes the single pattern match **both** a commented line
(`# skills_source: auto`) and an active line (`skills_source: vendored`).
With `count=1`, `pattern.sub` rewrites whichever match appears **first in
document order** — not, as intended, the active line. When a commented
documentation example precedes the active setting, the comment is
un-commented to the new value and the genuine active key is left
untouched. The file then carries **two** active `skills_source:` keys with
conflicting values: a YAML mapping with a duplicate key (ambiguous — last
value wins under PyYAML, an error under stricter loaders), and the mode
switch the caller requested silently does not take effect.

This is a regression introduced by the fix for the sibling card
[`skills-source-rewrite-regex-eats-blank-lines-above-the-key`](../skills-source-rewrite-regex-eats-blank-lines-above-the-key/):
that fix consolidated the comment and active cases into one `#?`-optional
pattern to stop the char-class from eating newlines, but in doing so made
a single `count=1` substitution responsible for picking the right line
out of two candidates — which it cannot do by document order alone.

## Empirical evidence

`uv run python .game-of-cards/deck/skills-source-rewrite-uncomments-commented-key-instead-of-active/reproduce.py`:

```
--- commented doc example above an active key; switch vendored->plugin
  value requested : plugin
  input           : '# skills_source: auto\n\nskills_source: vendored\n'
  output          : 'skills_source: plugin\n\nskills_source: vendored\n'
  expected        : '# skills_source: auto\n\nskills_source: plugin\n'
  active key count : 2 (want exactly 1)
  match           : False
```

The comment became `skills_source: plugin` while the real active line
stayed `skills_source: vendored`: two active keys, requested switch lost.

## Why it matters

`config.yaml` is consumer-owned, hand-edited text. The reachability path
for a two-line state runs through the `Skill(upgrade)` 2-way LLM merge of
the *evolving* `config.yaml` against the upstream template: the upstream
template ships `# skills_source: auto` as a commented example inside the
`skills_source` documentation block (`goc/templates/game_of_cards/config.yaml:82`).
A merge that reintroduces or repositions that documented example above a
consumer's already-active `skills_source:` line leaves the config with
both a commented example and an active key. The very next mode pin —
`_write_skills_source` is called unconditionally on every `goc install`
(`goc/install.py:1439`) and `goc upgrade` (`goc/install.py:1671`) — then
un-comments the example, producing the duplicate key and silently dropping
the requested mode change. A hand edit that uncomments the documentation
line "for reference" while keeping the active setting reaches the same
state.

## Fix

Split the single `#?`-optional pattern into an active-preferred two-step:
match and rewrite the first **active** (non-commented) line if one exists;
otherwise rewrite the first **commented** line (un-commenting it);
otherwise append. This honors the docstring while guaranteeing exactly one
active key.

```python
active_pat = re.compile(r"^[ \t]*skills_source[ \t]*:.*$", re.MULTILINE)
commented_pat = re.compile(r"^[ \t]*#[ \t]*skills_source[ \t]*:.*$", re.MULTILINE)
replacement = f"skills_source: {value}"
if active_pat.search(text):
    new_text = active_pat.sub(lambda _: replacement, text, count=1)
elif commented_pat.search(text):
    new_text = commented_pat.sub(lambda _: replacement, text, count=1)
else:
    sep = "" if text.endswith("\n") else "\n"
    new_text = f"{text}{sep}\n{replacement}\n"
```
