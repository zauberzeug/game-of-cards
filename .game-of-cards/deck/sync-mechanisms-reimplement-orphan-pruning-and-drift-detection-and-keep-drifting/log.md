## 2026-06-22 — audit evidence: porter drift report under-lists orphan-dir contents

An audit-deck sweep (queue-empty pull-card session) surfaced another
drift-check imperfection in this same family, recorded here as evidence
for the eventual decision rather than as a separate instance card (the
meta-fix supersedes per-instance filing for this family).

`scripts/port_skills_to_openclaw.py:279` builds the orphan portion of
the drift report as:

```python
drifted.extend(orphan / "SKILL.md" for orphan in _orphaned_ported_dirs(expected))
```

It lists only `<orphan>/SKILL.md`, but the write path removes the whole
directory (`scripts/port_skills_to_openclaw.py:360`,
`shutil.rmtree(orphan)`) — every sibling asset included. So for an
orphaned ported dir that carries siblings (e.g. `card-schema/` with its
`schema.yaml`), `--check` under-reports which files a re-port will
delete.

Empirical probe (orphan dir with `SKILL.md` + `schema.yaml`,
`drifted_skills()` vs. what `rmtree` would remove):

```
drift --check REPORTS for this orphan: ['openclaw-plugin/skills/<orphan>/SKILL.md']
sync rmtree WOULD REMOVE:              ['openclaw-plugin/skills/<orphan>/SKILL.md',
                                        'openclaw-plugin/skills/<orphan>/schema.yaml']
asymmetry (removed but not reported):  ['openclaw-plugin/skills/<orphan>/schema.yaml']
```

This is *milder* than the four wired instance cards: the orphan dir is
still detected (`drifted_skills()` returns non-empty → `--check` exits 1
→ CI red), so no stale payload ships silently. The gap is purely in the
*reported path list* completeness — a reader of `--check` output sees
only `SKILL.md` and may not realize re-porting also deletes the
siblings.

Relevance to the decision: it is one more case where the drift-check
half of the prune/drift-check contract diverges from what the prune half
actually does — exactly the divergence Option B's "shared test contract"
("for every sync mechanism … `--check` flags one while it lingers")
should pin down. Whatever shape the eventual contract takes, it should
assert the drift report enumerates *every* path the prune would remove,
not just the marker file. No code change made in this session (the gate
is `decision`).

## 2026-11-02T01:02:06Z — Parked instance: drift detection is blind to file modes

This is another case of "the drift check passes clean on a real drift", in `scripts/sync_plugin_assets.py`. It has not been filed as a child card yet, because the run that found it filed one new card.

- **Hypothesis**: both the sync and its `--check` compare content only, at `scripts/sync_plugin_assets.py:343` (`_sync_file`) and `:545` (check path), each `if not dst.exists() or not filecmp.cmp(src, dst, shallow=False):`.
  - A mirror whose executable bit was lost is reported in sync.
  - It is never repaired either: `shutil.copy2` (`:345`), which would carry the mode, runs only when the content differs.
  - The mirrored `_goc-bootstrap.sh` copies are tracked `100755`. The Codex resolver at `goc/install.py:1443` and `goc/templates/skills/codex-kickoff/SKILL.md:115` locates the installed helper with `find ... -type f -perm -111`, so a committed mode loss leaves that `find` with nothing to return.
- **Observed by the surfacing agent** (scratch clone): after `chmod -x codex-plugin/skills/_goc-bootstrap.sh`, `python scripts/sync_plugin_assets.py --check` printed OK and exited 0. A plain sync left the bit off, and `git diff --summary` showed `mode change 100755 => 100644`.
- **Falsification recipe**: in a scratch clone, `chmod -x` any `100755` mirror and run `--check`. It should report drift (exit 1), and a sync should restore the mode. A test can plant the drift the same way.
- **Surfaced by**: an `audit-deck` hunter agent (general-purpose), 2026-11-02.
