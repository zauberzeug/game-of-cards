---
title: codex-skill-frontmatter-normalization-reimplemented-in-install-and-sync
summary: "The Codex SKILL.md frontmatter transform (split off the `---` delimiters, keep name+description, prepend CODEX_GOC_COMMAND_RESOLVER) is reimplemented in THREE places: `goc/install.py:_write_codex_skill`, `scripts/sync_plugin_assets.py:_codex_skill_text`, and a third nested inside `validate_plugin_mirror_parity` in `goc/engine.py` (the copy that SHIPS). All three carry the identical `text.split(\"---\", 2)` truncation bug, but the existing per-site card names only the install copy — so a fix there leaves the other two stale. The duplication is the root cause the repo's other `reimplements-and-keeps-drifting` cards already target; this card extracts one shared normalizer."
status: open
stage: null
contribution: medium
created: "2026-06-22T14:23:23Z"
closed_at: null
human_gate: decision
advances: []
advanced_by:
  - a-third-copy-of-the-codex-skill-transform-lives-inside-goc-validate
tags: [infra, api-contract]
definition_of_done: |
  - [ ] PROCESS: human picks the consolidation approach in `## Decision required` (single canonical text-producing helper in `goc/install.py` reused by both call sites / shared helper in a new module / leave duplicated with a parity test). Recorded inline + in log.md.
  - [ ] MECHANICAL: the chosen approach lands — after it, the `---`-split + name/description + resolver assembly exists in exactly one function, and `scripts/sync_plugin_assets.py` calls it rather than re-deriving it. `goc/install.py:_write_codex_skill` writes what that helper returns.
  - [ ] TDD: a regression test asserts `goc install --agents codex` and `scripts/sync_plugin_assets.py` produce byte-identical Codex SKILL.md for the same template (the parity the duplication currently leaves unguarded).
  - [ ] PROCESS: cross-link [write-codex-skill-truncates-frontmatter-when-description-contains-three-dashes](../write-codex-skill-truncates-frontmatter-when-description-contains-three-dashes/) — once the transform is single-sourced, that card's fix closes both sites at once. Note in both bodies which card owns the truncation fix vs. the consolidation.
  - [ ] MECHANICAL: `uv run goc validate` clean; `python scripts/sync_plugin_assets.py --check` passes; `uv run python -m unittest discover -s tests` green; plugin mirrors re-synced if `install.py` changed.
---

# Codex skill frontmatter normalization is reimplemented in `install.py` and `sync_plugin_assets.py`

## Location

Three independent implementations of the same Codex SKILL.md transform:

- `goc/install.py:1153-1178` — `_write_codex_skill`:

  ```python
  def _write_codex_skill(src: Path, dst: Path, *, skill_name: str) -> None:
      text = src.read_text()
      if not text.startswith("---\n"):
          shutil.copy2(src, dst)
          return
      try:
          _, frontmatter, body = text.split("---", 2)
      except ValueError:
          shutil.copy2(src, dst)
          return
      name = _frontmatter_value(frontmatter, "name") or skill_name
      description = _frontmatter_value(frontmatter, "description")
      codex_frontmatter = "\n".join(
          (
              "---",
              f"name: {name}",
              f"description: {json.dumps(description, ensure_ascii=False)}",
              "---",
          )
      )
      dst.parent.mkdir(parents=True, exist_ok=True)
      dst.write_text(codex_frontmatter + CODEX_GOC_COMMAND_RESOLVER + body)
  ```

- `scripts/sync_plugin_assets.py:350-368` — `_codex_skill_text`:

  ```python
  def _codex_skill_text(src: Path, *, skill_name: str) -> str:
      text = src.read_text()
      if not text.startswith("---\n"):
          return text
      try:
          _, frontmatter, body = text.split("---", 2)
      except ValueError:
          return text
      name = _frontmatter_value(frontmatter, "name") or skill_name
      description = _frontmatter_value(frontmatter, "description")
      codex_frontmatter = "\n".join(
          (
              "---",
              f"name: {name}",
              f"description: {json.dumps(description, ensure_ascii=False)}",
              "---",
          )
      )
      return codex_frontmatter + CODEX_GOC_COMMAND_RESOLVER + body
  ```

- `goc/engine.py` — a third copy nested inside `validate_plugin_mirror_parity`,
  identical to the sync script's:

  ```python
      def _codex_skill_text(src: Path, *, skill_name: str) -> str:
          text = src.read_text()
          if not text.startswith("---\n"):
              return text
          ...
          return codex_frontmatter + CODEX_GOC_COMMAND_RESOLVER + body
  ```

The sync script already imports `CODEX_GOC_COMMAND_RESOLVER` and
`_frontmatter_value` from `goc.install` (sync_plugin_assets.py:38-43), and the
engine imports the same two constants (engine.py:1661-1665) — both share the
*constants* and re-derive the *transform*.

The third site was found by
[a-third-copy-of-the-codex-skill-transform-lives-inside-goc-validate](../a-third-copy-of-the-codex-skill-transform-lives-inside-goc-validate/)
(done), which measured what the split already cost: two hardening fixes to the
surrounding mirror walk reached the install and sync copies and not the engine
one, leaving the guard that ships to consumers the weakest of the three. That
card restored the lockstep and left
`tests/test_codex_skill_transform_lockstep.py` behind as a guard — a
consolidation that merges only two of the three sites will not turn that test
red, so scope it to all three.

## What's broken

The three functions are byte-for-byte the same logic; the only difference is
that one writes to a path and the other two return a string. This is the same
"N copies of one transform, kept in sync by hand" shape the repo already
files as a defect — see the closed/open `reimplements-and-keeps-drifting`
family (`yaml-lite-quote-scanners-reimplement-the-same-state-machine-and-keep-drifting`,
`frontmatter-emitter-quote-trigger-reenumerates-parser-shapes-and-keeps-drifting`,
`sync-mechanisms-reimplement-orphan-pruning-and-drift-detection-and-keep-drifting`).

The drift cost is concrete and already incurred: both copies carry the
identical `text.split("---", 2)` truncation bug (a `description` containing
the substring `---` truncates the frontmatter — see
[write-codex-skill-truncates-frontmatter-when-description-contains-three-dashes](../write-codex-skill-truncates-frontmatter-when-description-contains-three-dashes/)).
That card cites and scopes only the `install.py` site (its DoD names
`_sync_skill_tree`, the install entry point). When that card's fix lands, the
`install.py` copy is corrected and the `sync_plugin_assets.py` and `engine.py`
copies silently keep the bug — and `_check_codex_skill_tree` compares the synced output
against `_codex_skill_text`'s own (still-buggy) output, so CI cannot see the
skew. The two emitters must agree for the dogfood mirror to match a real
`goc install --agents codex`; nothing currently enforces that agreement.

## Why it matters

`scripts/sync_plugin_assets.py` regenerates `.codex/skills/` and
`codex-plugin/skills/` on every commit, and CI's `--check` mode is the only
guard that the committed Codex mirrors match what `goc install --agents codex`
would write. That guard is built on the *assumption* that `_codex_skill_text`
applies the same transform as `_write_codex_skill`. Today that holds only
because a human kept the two copies identical; the moment one is edited (e.g.
to fix the truncation bug, or to change the resolver block, or to keep a new
frontmatter key for Codex) and the other isn't, the dogfood mirror diverges
from real installs and `--check` validates the divergence as correct. The
reachability is direct: any future edit to one copy reaches the bug.

## Decision required

The fix direction (single-source the transform) is dictated by the repo's
existing convention against reimplementation, but *where* the canonical
helper lives and how the writer reuses it is a design pick:

1. **Canonical text helper in `goc/install.py`.** Add
   `_codex_skill_text(src, *, skill_name) -> str` to `goc/install.py` (the
   source of truth that ships in the wheel); `_write_codex_skill` becomes a
   thin `dst.write_text(_codex_skill_text(...))`, and
   `scripts/sync_plugin_assets.py` imports it the same way it already imports
   `_frontmatter_value`. `validate_plugin_mirror_parity` drops its nested copy
   and imports it too, the same way it already imports the constants. Smallest
   change; one function, three callers.
2. **Shared helper in a new small module** imported by both `install.py` and
   the script. Cleaner separation but adds a module the wheel must ship.
3. **Leave duplicated, add a parity test** asserting the three functions
   produce identical output for every shipped skill. Cheapest to land — and
   partly already done, since
   `tests/test_codex_skill_transform_lockstep.py` is exactly that test — but it
   does not retire the family: the next edit can still desync between commits,
   and the guard only catches it after the fact.

Recommended: option 1 (matches how the sync script already depends on
`goc.install`; retires the duplication at the source). Whichever is chosen, it
must cover all three sites — a merge of install and sync alone leaves the
shipped engine copy standing, which is the exact failure the third-copy card
measured. The truncation fix should then be made *once* in the shared helper,
and the sibling card updated to point at it.
