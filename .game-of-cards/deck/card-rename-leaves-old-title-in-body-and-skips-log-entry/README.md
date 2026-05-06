---
title: card-rename-leaves-old-title-in-body-and-skips-log-entry
summary: "`goc move` rewrites only the moved card's frontmatter `title` and other cards' `advances`/`advanced_by` list fields. Every other slug reference in the repo silently rots: the moved card's own `# {title}` H1, prose / link references in other cards' bodies, log.md mentions across the deck, and slug references in AGENTS.md / CLAUDE.md / docs / website / scripts. The right model is repo-wide: enumerate every text file under the repo, rewrite known structural references (heading, link, deck-path), and write a dated `## renamed from <old>` log entry. No log.md entry records the rename either — `decide` and `attest` write structured log entries; `move` does not."
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
  - [ ] `goc move` performs a repo-wide pass (text files only; binaries skipped; `.git/` skipped; `.gitignore`-respecting via `git ls-files`) and rewrites every occurrence of `old_title` in: card bodies (including this card's own body), every `log.md`, AGENTS.md, CLAUDE.md, docs/, site/, README.md, and any other tracked text file
  - [ ] The rewrite pass is conservative — it rewrites the bare-slug, the `[<old>](../<old>/)` link form, and `deck/<old>/` path form. Other token boundaries (slug as substring of a longer word) are left alone. The exact match rules are documented in the `move` docstring
  - [ ] `goc move` appends a dated rename entry to the moved card's `log.md` (e.g. `## YYYY-MM-DD: renamed from <old_title>`), matching the structured-log convention used by `decide` and `attest`
  - [ ] `goc move --dry-run` prints the list of file:line sites that would be rewritten, so the user can review before committing (renames are rare, getting a chance to inspect is cheap insurance)
  - [ ] Outside-repo references (commit messages, GitHub PRs, external docs) are explicitly out of scope and called out in the docstring
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

The narrow framing is "card body references stay stale", but the right framing is **`goc move` ignores every text-file surface in the repo except the two it explicitly opens**. The defects compound:

1. **Stale H1 heading on the moved card.** `goc new` scaffolds every body with `# {title}` (engine.py:1768). After `goc move foo bar`, `bar/README.md` still has `# foo` as its first heading.

2. **Stale slugs in other cards' bodies.** Cross-links between cards take the form `[<title>](../<title>/)` (per `Skill(create-card)` Step 5: "Cross-link other cards as `[<title>](../<title>/)`."). Path-style references `deck/<title>/...` and bare-slug citations appear in many existing card bodies (e.g. disproved write-ups, decision rationale, supersede notes). `move` never opens any other card's body — only its frontmatter.

3. **Stale slugs in `log.md` files.** Every closed card's `log.md` may quote slugs in attestation/decision blocks. `move` doesn't touch any `log.md` — not the moved card's own, not any other card's. The audit trail rots silently.

4. **Stale slugs in AGENTS.md / CLAUDE.md / docs / website / scripts.** Slugs appear in plenty of non-deck surfaces:
   - The hand-written part of `AGENTS.md` / `CLAUDE.md` may discuss specific cards by slug.
   - `docs/` and `site/` (project website) reference cards by slug in marketing/readme copy.
   - Skill bodies under `goc/templates/skills/<verb>/SKILL.md` cite cards as examples.
   - GitHub workflows / scripts may grep for specific card titles.
   `move` ignores all of these. The user's intuition is right: this should be a **repo-wide grep + rewrite**, scoped via `git ls-files` so `.gitignore` is respected and `.git/` is skipped, with sane match rules (the three structural forms above plus the bare slug).

5. **No log entry on the rename.** `decide` (engine.py:1943-1951) and `attest` (engine.py:1649-1653) both append structured dated blocks to `log.md` so the per-card audit ledger preserves the action. `move` writes nothing. This is also the action for which an audit entry matters most: every reference to the old slug in git history, external doc, or PR thread is now lookup-broken, so the log is the only on-deck way to find the rename.

### Why repo-wide, not just `deck/`

The narrow alternative — "rewrite references inside `deck/` only" — leaves AGENTS.md, the website, and docs broken. Renames are rare; the right tool is `git ls-files` (or `git grep -l`), filter to text files, run the substitution. Performance is irrelevant; correctness is the issue. The match must be conservative: only rewrite the bare-slug token (with word-boundary anchoring), the `[old](../old/)` markdown-link form, and the `deck/old/` path form. Don't try to rewrite the slug as a substring of unrelated identifiers.

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

1. **Replace the deck-only rewrite loop with a repo-wide pass.** Use `git ls-files -z` (cwd = `REPO_ROOT`) to enumerate tracked text files. Filter binaries (e.g. by `\0` or git's `--text` heuristic). For each file:
   - Rewrite `# {old_title}` H1 → `# {new_title}` (only when the slug is the literal H1).
   - Rewrite `[{old_title}](../{old_title}/)` markdown-link form → new equivalent.
   - Rewrite `deck/{old_title}/` and `.game-of-cards/deck/{old_title}/` path forms.
   - Rewrite bare-slug occurrences using word-boundary anchoring (`\b{old}\b`), so `old-title-extended` is not matched by `old-title`.
2. Keep the existing frontmatter pass for `advances` / `advanced_by` (it already works).
3. Append `## YYYY-MM-DD: renamed from <old_title>` to the moved card's `log.md`, following the same shape as `decide` (engine.py:1943-1951).
4. Add a `--dry-run` mode that prints `file:line: <preview>` for every site that would be rewritten, so the user can review before committing.
5. Update the `move` docstring to spell out the contract:
   - Which match rules are applied (the four shapes above).
   - That the rewrite is scoped to tracked text files (`.gitignore`-respecting).
   - That outside-repo references — commit messages, GitHub PR titles, external docs — are out of scope.

Optional: also auto-stage and auto-commit the rewrite (via `_git_auto_commit`) once the change set is non-trivial, mirroring the pattern from `status` / `advance` / `decide`.
