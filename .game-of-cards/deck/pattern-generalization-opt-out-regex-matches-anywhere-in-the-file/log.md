
## 2026-10-14T05:03:56Z — Same over-match, now in the opt-in direction

The hook became opt-in after this card was filed, so the check is now
`_enabled` (`goc/templates/hooks/pattern_generalization_check.py:223-240`),
not `_opted_out`. It still uses the same unanchored
`re.search(r"pattern_generalization_check\s*:\s*(\S+)", ...)`, so the
over-match now runs the other way: a stray `true` turns the hook on. Measured
on 2026-10-14 with a config holding a commented-out
`# pattern_generalization_check: true` line above the live
`pattern_generalization_check: false`: `_enabled` returns `True`, so every
code-mutating turn is blocked even though the live setting is off. The
README's opt-out framing is stale on this point.

Input for the decision below: the same file now carries a structural reader
for another config key, `_config_shares_the_deck` (added by
`python-hooks-ignore-git-worktree-shared-deck-resolution`). It reads one key
under its parent block, skips comment lines, and is pinned to yaml_lite's
reading by an engine-oracle test. That is a third option between anchoring the
regex and a full YAML parse.
