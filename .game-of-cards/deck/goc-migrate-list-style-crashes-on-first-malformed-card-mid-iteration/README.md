---
title: goc-migrate-list-style-crashes-on-first-malformed-card-mid-iteration
summary: "`goc migrate-list-style` calls `parse_frontmatter` without a `FrontmatterError` net, so a single card with an unterminated `---` opener or invalid YAML aborts the bulk rewrite mid-deck with a Python traceback. Three sibling deck-walkers (`load_all_cards`, `_cmd_show`, `load_card_or_exit`) already catch and continue/diagnose — `_cmd_migrate_list_style` is the outlier."
status: active
stage: null
contribution: medium
created: "2026-05-29T17:53:48Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, meta-fix]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero — a two-card deck (one valid card needing list-style migration, one card with `---` opener and no closer) runs `goc migrate-list-style` cleanly: the broken card surfaces a `WARNING: <slug>: …` on stderr, the valid card is rewritten, exit code is 0.
  - [ ] TDD: same reproducer under `--dry-run` likewise surfaces a stderr warning and reports the valid card in the "would rewrite" list (no traceback).
  - [ ] MECHANICAL: `_cmd_migrate_list_style` in `goc/engine.py` wraps `parse_frontmatter(original)` in a `try/except FrontmatterError` net that mirrors `load_all_cards` at engine.py:625-631 — emit `WARNING: <card_dir.name>: <exc>` to stderr and `continue`.
  - [ ] PROCESS: sibling sweep — grep for every other direct `parse_frontmatter(` call site in `goc/engine.py` and confirm each is either inside the four already-netted sites (`load_card` → `load_all_cards`, `_cmd_show`, `load_card_or_exit`, `validate_deck_directories`) or in a context where the raise is the documented contract. File a follow-up card per unnetted site discovered.
  - [ ] PROCESS: `uv run python -m unittest discover -s tests` stays green.
worker: {who: "claude[bot]", where: main}
---

# `goc migrate-list-style` crashes on the first malformed card mid-iteration

## Location

`goc/engine.py:4792-4812` — `_cmd_migrate_list_style`, the implementation of
`goc migrate-list-style`.

## What's broken

`_cmd_migrate_list_style` walks `DECK_DIR` and calls `parse_frontmatter`
directly on every `README.md`, with no exception net:

```python
# goc/engine.py:4799-4812
changed: list[str] = []
for card_dir in sorted(DECK_DIR.iterdir()):
    readme = card_dir / "README.md"
    if not readme.exists():
        continue
    original = readme.read_text()
    fm, body = parse_frontmatter(original)   # ← uncaught FrontmatterError
    if not fm:
        continue
    rewritten = emit_frontmatter(fm, body=body)
    if rewritten != original:
        changed.append(card_dir.name)
        if not dry_run:
            readme.write_text(rewritten)
```

`parse_frontmatter` is documented (engine.py:144-173) to raise
`FrontmatterError` on three concrete shapes: opener present with no closer,
YAML parse error inside frontmatter, frontmatter parses to a non-mapping.

The three sibling deck-walkers in the same file all handle this:

```python
# goc/engine.py:625-631 (load_all_cards — bulk-load for queue/board)
try:
    t = load_card(sub)
except FrontmatterError as exc:
    # Don't let one broken card blank the whole queue — surface a
    # warning per card and skip. `goc validate` reports authoritatively.
    print(f"WARNING: {sub.name}: {exc}", file=sys.stderr)
    continue
```

```python
# goc/engine.py:4696-4699 (_cmd_show)
try:
    parse_frontmatter(text)
except FrontmatterError as exc:
    print(f"WARNING: {title}: {exc}", file=sys.stderr)
```

```python
# goc/engine.py:835-839 (validate_deck_directories)
except FrontmatterError as exc:
    errors.append(f"{sub.name}: {exc}")
    continue
```

`_cmd_migrate_list_style` is the lone bulk verb without the net. A single
malformed card (one Windows-line-ending card, one mid-hand-edit card, one
card whose YAML accidentally contains an unquoted `[`) aborts the entire
migration with a Python traceback. Cards before the failing one have
already been rewritten on disk; cards after are never touched. The
`--dry-run` preview path has the identical crash because it reaches
`parse_frontmatter` first.

## Empirical evidence

`uv run python .game-of-cards/deck/goc-migrate-list-style-crashes-on-first-malformed-card-mid-iteration/reproduce.py`
on a clean checkout — builds a tempdir deck with one valid card + one card
with `---` opener and no closer, then runs the verb twice:

```text
== goc migrate-list-style --dry-run ==
exit code: 1
stderr tail:
    File "/.../goc/engine.py", line 4805, in _cmd_migrate_list_style
      fm, body = parse_frontmatter(original)
    File "/.../goc/engine.py", line 156, in parse_frontmatter
      raise FrontmatterError(
  goc.engine.FrontmatterError: frontmatter unterminated: opening '---' at line 1 has no matching closing '---' delimiter

== goc migrate-list-style ==
exit code: 1
stderr tail:
  (identical traceback)

defect fires (FrontmatterError reached stderr): True
both runs exit zero: False
```

Both runs crash with exit code 1 and the same `FrontmatterError` traceback;
the valid card is never inspected.

## Why it matters

Reachability: the offending input is produced by ordinary hand editing of a
card body. The `cards-with-windows-line-endings-vanish-from-the-deck-as-unterminated`
card (open, engine.py family) already documents one concrete way a card on
disk reaches an unterminated-opener state. Any consumer who edits cards in
a Windows-aware editor and then runs `goc migrate-list-style` to convert
inline-flow lists to block-style (the documented one-shot migration from
the `migrate-list-style` plumbing) will hit this — partway through the
deck, with an unspecified subset already rewritten.

This is a **meta-fix** family: every direct `parse_frontmatter(...)` call
site is a candidate for the same net. The four already-netted sites
(`load_card`, `_cmd_show`, `load_card_or_exit`, `validate_deck_directories`)
prove the convention; `_cmd_migrate_list_style` is the regression. The DoD's
PROCESS sweep item makes the next reader audit the remaining call sites
rather than assuming this is a one-off.

## Fix

Wrap the `parse_frontmatter` call in the same try/except shape `load_all_cards`
uses:

```python
# goc/engine.py:4805 — replace
original = readme.read_text()
try:
    fm, body = parse_frontmatter(original)
except FrontmatterError as exc:
    print(f"WARNING: {card_dir.name}: {exc}", file=sys.stderr)
    continue
if not fm:
    continue
```

No new dependency, no behavior change for valid cards. Broken cards are
diagnosed authoritatively by `goc validate`, which is the existing contract
all three sibling sites delegate to.
