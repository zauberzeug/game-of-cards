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

## 2026-11-09T01:00:07Z — Related finding (audit-deck): the tripwire also fires on edits that change no version

Parked here, not filed separately: audit-deck files one new card per run, and this is the same tripwire step. Any choice under `## Decision required` changes how often it fires.

- **Defect:** `release.yml:279-280` compares file *names* (`git diff --name-only HEAD~1 HEAD -- $tracked`), not the version values. So a HEAD commit that edits any of the six tracked files for another reason is refused with "ERROR: HEAD modifies version literals … Revert the literal edits and re-dispatch." Examples: a description in `plugin.json` / `marketplace.json`, a dependency in `package.json`, a docstring in `goc/__init__.py`.
- **Contradicted text:** `release.yml:255` ("release commit must not edit version literals"), `release.yml:112-113`, and `CONTRIBUTING.md:151-152` ("A commit that touches a version literal trips an in-job tripwire"). `AGENTS.md:77-79` says "touches those six files", which matches the code, so the docs also disagree with each other.
- **Evidence (audit-deck hunter agent, re-checked on the main thread):** the step body, extracted verbatim and run in a /tmp clone at real commit `7743a2ac` (claude[bot]; description-only edits to `.claude-plugin/marketplace.json` and `claude-plugin/.claude-plugin/plugin.json`), exits 1 with the error above. On current main it prints OK.
- **Bearing on the decision:** Option 1 (deepen the range back to the last release) would make this worse. Every routine manifest edit since the last release would then block the release. A fix that compares `"version"` / `__version__` values would close this false positive and could carry a deeper range without that cost.
- **Not yet done:** no `reproduce.py`. Recipe: build a synthetic repo, run the extracted step on a description-only HEAD edit (expect exit 0 after a fix) and on a version-bump control (expect exit 1). Exit 2 if the control stops tripping.
