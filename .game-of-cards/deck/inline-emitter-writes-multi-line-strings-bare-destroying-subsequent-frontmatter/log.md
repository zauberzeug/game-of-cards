## 2026-05-29T23:38:41Z: decision deliberation archived

Archived from the README's `## Decision required` section by `goc decide` before it was replaced with the resolved `## Decision` block — README is the dashboard, log.md is the journal. This preserves the options and recommendation that produced the decision below.

The fix has two credible paths. Both close the defect; they differ in
which layer takes responsibility.

**(a) Refuse multi-line input at the `_yaml_inline` boundary.** Add a
sibling branch alongside the float refusal (engine.py:219-227):

```python
if "\n" in s:
    raise FrontmatterError(
        f"multi-line frontmatter values are not supported by _yaml_inline; "
        "route through emit_frontmatter for literal-block style."
    )
```

`_apply_summary_rewrite` then catches the error and falls back to a
full `emit_frontmatter` re-emit. Pro: enforces the docstring contract
at the function boundary, matches the float-refusal posture, surfaces
every bypassing caller as a loud failure. Con: every existing call site
that might pass a free-form string has to be audited and possibly
wrapped — `worker` rewrites (engine.py:3468), `closed_at`/`status`
(throughout), `human_gate` (engine.py:4359, 4579), and any future
caller.

**(b) Rewire the caller to go through `emit_frontmatter`.** Replace
`_apply_summary_rewrite`'s body with a parse-mutate-re-emit pattern
parallel to `_apply_dod_rewrite` (engine.py:3061-3078):

```python
def _apply_summary_rewrite(card: Card, new_summary: str) -> None:
    readme = card.path / "README.md"
    text = readme.read_text()
    fm, body = parse_frontmatter(text)
    fm["summary"] = new_summary
    readme.write_text(emit_frontmatter(fm, body=body))
```

Pro: `emit_frontmatter` already handles every value shape correctly
(including multi-line via `_emit_block_field`); the fix is local and
mechanical. Con: the broader `_yaml_inline` contract violation remains
latent — any *other* caller that bypasses `emit_frontmatter` keeps the
silent-data-loss footgun.

The two are not mutually exclusive: (b) is the minimal local fix, (a)
is the structural guard that prevents the family from spawning siblings.


## 2026-05-30T13:57:04Z: decision recorded

Both paths: (b) rewire _apply_summary_rewrite to parse->mutate->emit_frontmatter (matching _apply_dod_rewrite) to stop the live data loss locally, PLUS (a) add a multi-line refusal branch in _yaml_inline alongside the float-refusal and a ratchet test asserting no other caller bypasses emit_frontmatter with free-form input — this is a silent data-corruption bug so (b) is needed immediately as the minimal local fix, while (a) is the structural boundary guard that prevents the documented recurring bug family from spawning siblings via any other bypassing caller. Gate decision → none.
