---
title: a-third-copy-of-the-codex-skill-transform-lives-inside-goc-validate
summary: "The Codex SKILL.md normalization has three independent implementations, not the two the open consolidation card enumerates: `goc/install.py:1367` (the writer), `scripts/sync_plugin_assets.py:350` (the mirror generator), and a third nested inside `validate_plugin_mirror_parity` at `goc/engine.py:1780`. The third is also the one that missed two hardening fixes the other copies carry — it compares mirror siblings with `read_text()` where the sync script deliberately uses `read_bytes()` so newline skew stays CI-detectable, and it skips `dst_item.is_dir()` where the sync script flags empty orphan directories. The weaker of the two guards is the one that ships to consumers. Parked unverified: citations read and confirmed, no reproduce.py built this round."
status: open
stage: null
contribution: medium
created: "2026-09-21T01:23:36Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [infra, api-contract, meta-fix, unverified]
definition_of_done: |
  - [ ] EMPIRICAL: the falsification recipe below is run and its verdict recorded in `log.md` either way — a CRLF sibling and an empty orphan subdirectory under `codex-plugin/skills/<skill>/`, with both guards' verdicts reported side by side.
  - [ ] TDD: if the lag is confirmed, `reproduce.py` exits zero once `validate_plugin_mirror_parity` reports the same drift `scripts/sync_plugin_assets.py --check` reports, having exited 1 before the fix; the `unverified` tag is dropped at that point.
  - [ ] MECHANICAL: the engine's mirror comparison at `goc/engine.py:1818-1826` compares siblings by bytes, and the orphan walk at `:1841-1842` stops skipping every directory so an empty orphan is reported.
  - [ ] PROCESS: [codex-skill-frontmatter-normalization-reimplemented-in-install-and-sync](../codex-skill-frontmatter-normalization-reimplemented-in-install-and-sync/) is amended to enumerate three sites, not two — otherwise its consolidation leaves the engine copy standing.
  - [ ] TDD: whichever consolidation lands, a guard asserts the copies stay in lockstep, so the next hardening fix cannot reach two of three again.
  - [ ] PROCESS: `uv run goc validate` passes and `uv run python -m unittest discover -s tests` is green.
---

# A third copy of the Codex skill transform lives inside `goc validate`

**Parked `unverified`.** The cited code was read and confirmed in this repo; no
`reproduce.py` was built this round. Surfaced by a hunter agent during an
`Skill(audit-deck)` round, which reported reproductions of its own (below) —
those are second-hand here and have not been re-run.

## Hypothesis

The Codex `SKILL.md` normalization exists in three independent implementations:

- `goc/install.py:1367` — `def _codex_skill_text(src, *, skill_name) -> str | None`, the writer.
- `scripts/sync_plugin_assets.py:350` — `def _codex_skill_text(src, *, skill_name) -> str`, the mirror generator.
- `goc/engine.py:1780` — `    def _codex_skill_text(src, *, skill_name) -> str`, nested inside `validate_plugin_mirror_parity`.

[codex-skill-frontmatter-normalization-reimplemented-in-install-and-sync](../codex-skill-frontmatter-normalization-reimplemented-in-install-and-sync/)
(open) names the first two and not the third, so a consolidation that follows
its scope would merge two copies and leave a third behind.

The third copy is also the one that missed two hardening fixes the sync script
carries. Its sibling comparison, `goc/engine.py:1818-1826`:

```python
            expected = (
                _codex_skill_text(src_item, skill_name=rel.parts[0])
                if src_item.name == "SKILL.md"
                else src_item.read_text()
            )
            if not dst_item.exists():
                diffs.append(f"{rel.as_posix()} (missing)")
            elif dst_item.read_text() != expected:
```

against `scripts/sync_plugin_assets.py:447-451`, where the byte comparison is
deliberate and commented:

```python
        else:
            # Siblings compared by bytes so install-vs-mirror newline skew is
            # CI-detectable (matching the byte-exact sync above).
            if not dst_item.exists() or dst_item.read_bytes() != src_item.read_bytes():
```

That comment is the closure of
[codex-skill-sibling-sync-uses-text-copy-diverging-from-byte-exact-install](../codex-skill-sibling-sync-uses-text-copy-diverging-from-byte-exact-install/)
(done), whose Location section cites `sync_plugin_assets.py` only — the engine
copy was never in scope, so the fix reached one of the two readers.

The same split shows in the orphan walk. `goc/engine.py:1841-1842` drops every
directory:

```python
        for dst_item in sorted(dst.rglob("*")):
            if "__pycache__" in dst_item.parts or dst_item.is_dir():
                continue
```

while `scripts/sync_plugin_assets.py:458-466` explicitly reports an orphan
directory that is empty.

## Why deferred

The round's budget went to two confirmed defects. This one needs a temp
`codex-plugin/skills/` tree and two mutations to turn a reading into a verdict,
and its blast radius is genuinely narrower than the other two — both guards run
in this repo's CI, so the skew is caught today by the stronger one.

## Falsification recipe

1. Build a temp tree shaped like `REPO_ROOT` with one eligible skill mirrored
   into `codex-plugin/skills/`.
2. Rewrite one non-`SKILL.md` sibling in the mirror with CRLF line endings.
3. Create an empty subdirectory in the mirror that has no source counterpart.
4. Run `engine.validate_plugin_mirror_parity()` and
   `scripts/sync_plugin_assets.py`'s check for the same tree.

If the two agree, both report the sibling and the orphan directory. If the lag
is real, the engine returns `[]` for `codex-plugin/skills` in both cases while
the sync check names the paths.

## Why it would matter

`goc validate` is the guard that ships; `scripts/sync_plugin_assets.py` is
repo-local and runs in this repo's CI only. If the weaker of the two is the one
consumers get, a consuming repo that vendors a Codex payload has no check for
the class of drift this repo considers CI-worthy. The duplication is the root
cause and the lag is its first visible cost: three copies, and a hardening fix
that reached two.
