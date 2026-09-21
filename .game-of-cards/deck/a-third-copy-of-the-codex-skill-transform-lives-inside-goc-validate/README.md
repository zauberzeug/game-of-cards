---
title: a-third-copy-of-the-codex-skill-transform-lives-inside-goc-validate
summary: "The Codex SKILL.md normalization has three independent implementations, not the two the open consolidation card enumerates: `goc/install.py:1367` (the writer), `scripts/sync_plugin_assets.py:350` (the mirror generator), and a third nested inside `validate_plugin_mirror_parity` at `goc/engine.py:1780`. The third is also the one that missed two hardening fixes the other copies carry — it compares mirror siblings with `read_text()` where the sync script deliberately uses `read_bytes()` so newline skew stays CI-detectable, and it skips `dst_item.is_dir()` where the sync script flags empty orphan directories. The weaker of the two guards was the one that ships to consumers. Confirmed by `reproduce.py`; the engine now matches the sync check on both points, and `tests/test_codex_skill_transform_lockstep.py` pins all three copies to each other so the next hardening fix cannot reach two of three again. The duplication itself stays open on the consolidation card."
status: done
stage: null
contribution: medium
created: "2026-09-21T01:23:36Z"
closed_at: "2026-09-21T05:19:26Z"
human_gate: none
advances:
  - codex-skill-frontmatter-normalization-reimplemented-in-install-and-sync
advanced_by: []
tags: [infra, api-contract, meta-fix]
definition_of_done: |
  - [x] EMPIRICAL: the falsification recipe below is run and its verdict recorded in `log.md` either way — a CRLF sibling and an empty orphan subdirectory under `codex-plugin/skills/<skill>/`, with both guards' verdicts reported side by side.
  - [x] TDD: if the lag is confirmed, `reproduce.py` exits zero once `validate_plugin_mirror_parity` reports the same drift `scripts/sync_plugin_assets.py --check` reports, having exited 1 before the fix; the `unverified` tag is dropped at that point.
  - [x] MECHANICAL: the engine's mirror comparison at `goc/engine.py:1818-1826` compares siblings by bytes, and the orphan walk at `:1841-1842` stops skipping every directory so an empty orphan is reported.
  - [x] PROCESS: [codex-skill-frontmatter-normalization-reimplemented-in-install-and-sync](../codex-skill-frontmatter-normalization-reimplemented-in-install-and-sync/) is amended to enumerate three sites, not two — otherwise its consolidation leaves the engine copy standing.
  - [x] TDD: whichever consolidation lands, a guard asserts the copies stay in lockstep, so the next hardening fix cannot reach two of three again.
  - [x] PROCESS: `uv run goc validate` passes and `uv run python -m unittest discover -s tests` is green.
worker: {who: "claude[bot]", where: main}
---

# A third copy of the Codex skill transform lives inside `goc validate`

**Confirmed.** `reproduce.py` in this directory builds a throwaway
`REPO_ROOT`-shaped tree, plants a CRLF sibling and an empty orphan subdirectory
in `codex-plugin/skills/`, and runs both guards over it. Before the fix the
engine returned nothing for `codex-plugin/skills` while the sync check named
both paths — the reading the card was filed on, verified. It now exits zero.

## Finding

The Codex `SKILL.md` normalization exists in three independent implementations:

- `goc/install.py:1367` — `def _codex_skill_text(src, *, skill_name) -> str | None`, the writer.
- `scripts/sync_plugin_assets.py:350` — `def _codex_skill_text(src, *, skill_name) -> str`, the mirror generator.
- `goc/engine.py:1780` — `    def _codex_skill_text(src, *, skill_name) -> str`, nested inside `validate_plugin_mirror_parity`.

[codex-skill-frontmatter-normalization-reimplemented-in-install-and-sync](../codex-skill-frontmatter-normalization-reimplemented-in-install-and-sync/)
(open, `human_gate: decision`) named the first two and not the third, so a
consolidation that followed its scope would have merged two copies and left a
third behind. Its `## Location` section now enumerates all three.

The third copy is also the one that missed two hardening fixes the sync script
carries. Its sibling comparison used `read_text()`, which applies
universal-newline translation, so a CRLF mirror copy read identical to its LF
source:

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

against `scripts/sync_plugin_assets.py`, where the byte comparison is
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

The same split showed in the orphan walk. The engine dropped every directory
before testing it:

```python
        for dst_item in sorted(dst.rglob("*")):
            if "__pycache__" in dst_item.parts or dst_item.is_dir():
                continue
```

while `scripts/sync_plugin_assets.py` reports an orphan directory that is
empty. git masks empty directories, so nothing else would have caught one.

## What changed

`_validate_codex_skill_mirror` in `goc/engine.py` now matches the sync check on
both points: non-`SKILL.md` siblings are compared with `read_bytes()`, and the
destination walk tests directories instead of skipping them, reporting an
orphan that is empty (a non-empty orphan still surfaces through its own files,
so it is not double-counted). `SKILL.md` stays a text comparison — that is what
the sync check does too, and the goal here is lockstep, not a third policy.

`tests/test_codex_skill_transform_lockstep.py` is the guard. It pins the two
directly-callable copies to each other over a corpus of awkward frontmatter
shapes plus every shipped template, and pins the engine's nested third copy by
behaviour: a mirror written by the real `_write_codex_skill` is drift-free to
both readers, an untransformed one is drift to both, and the CRLF sibling and
empty orphan dir are drift to both. The assertions are about output, not about
how many functions produce it, so the guard keeps holding after the
consolidation card lands.

## Falsification recipe

Implemented as `reproduce.py` beside this README:

1. Build a temp tree shaped like `REPO_ROOT` with one eligible skill mirrored
   into `codex-plugin/skills/`.
2. Rewrite one non-`SKILL.md` sibling in the mirror with CRLF line endings.
3. Create an empty subdirectory in the mirror that has no source counterpart.
4. Run `engine.validate_plugin_mirror_parity()` and
   `scripts/sync_plugin_assets.py`'s check for the same tree.

Verdict recorded in `log.md`: before the fix the engine reported `[]` for
`codex-plugin/skills` while the sync check named both paths; after, both name
both.

## Why it matters

`goc validate` is the guard that ships; `scripts/sync_plugin_assets.py` is
repo-local and runs in this repo's CI only. The weaker of the two was the one
consumers got, so a consuming repo that vendors a Codex payload had no check
for the class of drift this repo considers CI-worthy. The duplication is the
root cause and the lag was its first visible cost: three copies, and a
hardening fix that reached two. The lag is closed; the duplication is still
open on the consolidation card.
