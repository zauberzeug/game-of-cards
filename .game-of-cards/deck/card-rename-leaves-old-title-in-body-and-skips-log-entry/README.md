---
title: card-rename-leaves-old-title-in-body-and-skips-log-entry
summary: "`goc move` rewrites only the moved card's frontmatter `title` and other cards' `advances`/`advanced_by` list fields. It does not rewrite the moved card's own `# {title}` H1 (which `goc new` always scaffolds), does not rewrite prose mentions or relative-link references to the old slug in any body, and writes no `log.md` entry recording the rename. The audit trail of a slug change is lost; bodies silently carry stale slugs."
status: open
stage: null
contribution: medium
created: 2026-05-06
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] reproduce.py exits zero (defect no longer fires)
  - [ ] `goc move` rewrites the moved card's H1 heading from `# {old_title}` to `# {new_title}` (the heading scaffolded by `goc new` at engine.py:1768)
  - [ ] `goc move` rewrites prose mentions of `old_title` in the moved card's body and in other cards' bodies — at minimum, relative-link references of the form `[<old_title>](../<old_title>/)` and `deck/<old_title>/` path mentions
  - [ ] `goc move` appends a dated rename entry to the moved card's `log.md` (e.g. `## YYYY-MM-DD: renamed from <old_title>`), matching the structured-log convention used by `decide` and `attest`
  - [ ] Any restriction (e.g. only rewriting links/paths, not arbitrary prose) is documented in the `move` docstring so the contract is clear
---

# card-rename-leaves-old-title-in-body-and-skips-log-entry

## Location

- `goc/engine.py:1857-1907` (the entire `move` command)
- `goc/engine.py:1888-1890` — only frontmatter `title` is rewritten on the moved card
- `goc/engine.py:1891-1906` — only `advances`/`advanced_by` lists are rewritten on other cards
- `goc/engine.py:1768` — `goc new` scaffolds bodies with `# {title}` H1 (the stale heading after rename)
- `goc/engine.py:1943-1951` — `decide` writes a structured `log.md` entry; `move` has no equivalent
- `goc/engine.py:1649-1653` — `attest` writes a structured `log.md` entry; `move` has no equivalent

## What's broken

`goc move`'s docstring promises:

```python
def move(old_title, new_title, allow_jargon):
    """Rename a title and rewrite known cross-references."""
```

But "known cross-references" is narrower than the docstring implies. The implementation is:

```python
text = (dst / "README.md").read_text()
text = mutate_frontmatter_field(text, "title", new_title)
(dst / "README.md").write_text(text)
for t in load_all_cards():
    if t.title == new_title:
        continue
    readme = t.path / "README.md"
    original = readme.read_text()
    fm_data, body = parse_frontmatter(original)
    if not fm_data:
        continue
    changed = False
    for f in (*LIST_REL_FIELDS,):
        cur = fm_data.get(f) or []
        if isinstance(cur, list) and old_title in cur:
            fm_data[f] = [new_title if s == old_title else s for s in cur]
            changed = True
    if changed:
        readme.write_text(emit_frontmatter(fm_data, body=body))
click.echo(f"{old_title} → {new_title}")
```

Three concrete defects:

1. **Stale H1 heading on the moved card.** `goc new` scaffolds every body with `# {title}` (engine.py:1768). After `goc move foo bar`, `bar/README.md` still has `# foo` as its first heading.

2. **Stale slug in other cards' bodies.** Cross-links between cards take the form `[<title>](../<title>/)` (per `Skill(create-card)` Step 5: "Cross-link other cards as `[<title>](../<title>/)`."). And path-style references `deck/<title>/...` appear in many existing card bodies (e.g. README references in disproved write-ups). `move` never opens any other card's body — only its frontmatter. So all such references silently rot.

3. **No log entry on the rename.** `decide` (engine.py:1943-1951) and `attest` (engine.py:1649-1653) both append structured dated blocks to `log.md` so the per-card audit ledger preserves the action. `move` writes nothing — neither to the moved card's log.md nor to the cards it edited frontmatter on. The audit trail of a slug change disappears unless a human happens to add a manual note. This is also the action for which an audit entry matters most: every old reference to the old slug in git history, external doc, or PR thread is now lookup-broken, so the log is the only on-deck way to find the rename.

## Empirical evidence

`uv run python .game-of-cards/deck/card-rename-leaves-old-title-in-body-and-skips-log-entry/reproduce.py`:

```
--- after `goc move alpha-card alpha-card-renamed` ---
  moved card H1 still says `# alpha-card` (stale)?      True
  moved card log.md has no rename entry?                  True
  beta-card body still links to ../alpha-card/ (stale)?  True

--- moved README.md (head) ---
...
# alpha-card

(write the design doc here)

--- moved log.md ---
''

--- beta-card body (tail) ---
References [alpha-card](../alpha-card/) for prior art.

defects observed: 3 / 3
```

Exit code: 1 (will flip to 0 once `goc move` rewrites the H1, writes a rename log entry, and updates the cross-link).

## Why it matters

Renames are exactly the operation where stale references hurt — every old reference now points at a non-existent slug, and `goc validate` doesn't grep prose. The deck's stated principle (per `Skill(finish-card)`: "log.md is the append-only round/phase narrative") is silently violated for a structural state change. The `improve-deck` skill (templates/skills/improve-deck/SKILL.md) even greps `log.md` for migration-style entries — a convention `move` doesn't participate in.

## Fix (sketch — do NOT apply now)

1. After `mutate_frontmatter_field(text, "title", new_title)` on the moved card, also run a body-side substitution that:
   - Replaces the first H1 `# {old_title}` → `# {new_title}` (most reliable scaffold-aligned shape).
   - Optionally rewrites `[<old_title>](../<old_title>/)` and `deck/<old_title>/` path references — these are the two structurally recognizable forms.
2. Extend the per-other-card pass to also rewrite the same two structurally recognizable body forms (links/paths only — leave free prose alone, document that scope in the docstring).
3. Append `## YYYY-MM-DD: renamed from <old_title>` to the moved card's `log.md`, following the same pattern as `decide`.
4. Update the `move` docstring to spell out the contract: which surfaces are rewritten and which are not.
