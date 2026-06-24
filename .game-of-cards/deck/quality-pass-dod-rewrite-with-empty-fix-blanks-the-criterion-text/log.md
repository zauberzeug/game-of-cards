# Log

## 2026-06-24 — filed and fixed (fix-through)

Surfaced during a pull-card audit round (queue had no ready cards).

**Defect:** `_apply_dod_rewrite` (engine.py) applied any accepted verdict
issue carrying an `idx` + `fix` key, with no check that `fix` was
non-empty. An empty/whitespace `fix` produced `new_text == ""`, which
failed the `- [` prefix test and was rewritten to the literal
`"- [ ] "` — silently destroying the targeted DoD criterion's text,
contradicting the function's own "Other items preserved verbatim"
docstring.

**Fix:** guard the `fix_by_idx` comprehension with `issue["fix"].strip()`
so an empty/whitespace `fix` is treated as "no rewrite offered" and the
original line is preserved verbatim — the same outcome as the existing
`fixless` (no-`fix`-key) path the renderer already distinguishes.

**Semantics chosen — preserve original, not skip-with-error.** The
function's contract is per-item replacement with everything else kept
verbatim; an empty rewrite naturally means "leave this item alone."
Erroring or rejecting the whole verdict would be inconsistent with the
per-item design, so the non-destructive preserve-original behavior is
the determinate (gate-free) resolution.

**Evidence:** `reproduce.py` exits 1 before the fix (criterion blanked
to `- [ ] `), 0 after (criterion preserved). New regression test
`tests/test_dod_rewrite_empty_fix.py` (empty fix, whitespace fix, and
mixed empty+non-empty in one call). Full suite: 562 tests OK;
`goc validate` clean. Plugin `goc/` mirrors re-synced.
