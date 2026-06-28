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
