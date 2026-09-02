## Supporting evidence 2026-09-02 — the same sentence also under-specifies *which* files

Surfaced by an audit pass (empty ready queue) while auditing a different
surface. Independent of this card's `HEAD~1..HEAD` scope defect, and worth
fixing in the same edit because it lives in the same sentence.

`AGENTS.md:61-82` enumerates **eight** rewritten version surfaces — the five
plugin manifests, `goc/__init__.py`, and "the two dogfood self-host surfaces
(`.game-of-cards/deck/.goc-version`, `AGENTS.md`'s `<!-- BEGIN GOC vX.Y.Z -->`
marker)" — then says the tripwire "fails the build on any human commit that
touches those six files", calling out exactly one exclusion: "(`AGENTS.md` is
NOT in the tripwire's tracked set — humans edit its non-marker content
freely.)"

Eight surfaces minus the one stated exclusion is seven, not six. The
unstated eighth is `.game-of-cards/deck/.goc-version`. Verified against the
implementation — `.github/workflows/release.yml:279` tracks exactly six paths:

```
tracked='goc/__init__.py openclaw-plugin/package.json openclaw-plugin/package-lock.json claude-plugin/.claude-plugin/plugin.json codex-plugin/.codex-plugin/plugin.json .claude-plugin/marketplace.json'
```

So the count "six" is right and the antecedent is wrong: a reader following
the parenthetical concludes `.goc-version` is guarded by the tripwire when it
is not. The design intent looks coherent — the tripwire guards
*publish-channel* literals, and **both** dogfood self-host surfaces are
outside it — the doc just states only one of the two exclusions.

No protection gap follows: `tests/test_version_surfaces.py::test_self_hosted_generated_surfaces_match_package_version`
asserts `.goc-version` against the `__version__` literal, so a human commit
editing it alone turns CI red via the regression suite rather than the
tripwire. The defect is which guard the doc credits, not whether one exists.

Recorded here rather than filed separately: whoever rewrites this sentence to
settle this card's scope question should state both dogfood exclusions at the
same time.
