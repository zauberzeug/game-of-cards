---
title: unguarded-loader-callsites-keep-spawning-non-dict-shape-guard-fixes
summary: "Every `json.loads` / `yaml.safe_load` callsite that goes on to call dict methods on the result without an `isinstance(_, dict)` guard will crash with a raw `AttributeError` when the input is valid-but-wrong-shape (`null`, list, scalar). Two closed sibling cards have already patched specific callsites — `parse_frontmatter` (YAML frontmatter) and `_merge_claude_settings` / `_strip_goc_settings_entries` (JSON settings) — and three more unguarded callsites are still on disk (`load_deck_config`, `_resolve_deck_dir`'s config-probe, the canonical-tags fenced-YAML loader). The family will keep spawning per-site guard fixes until either the loaders reject the wrong shape at the source or every caller routes through a shared shape-coercing helper."
status: open
stage: null
contribution: medium
created: "2026-05-30T17:23:20Z"
closed_at: null
human_gate: decision
advances: []
advanced_by:
  - claude-settings-json-that-parses-to-a-non-dict-crashes-install-with-attributeerror
  - frontmatter-that-parses-to-a-list-or-scalar-crashes-loaders-with-a-raw-attributeerror
  - claude-settings-nested-hooks-shapes-bypass-the-top-level-isinstance-guard
  - pattern-generalization-check-jsonl-per-line-loader-trusts-non-dict-entries
  - claude-settings-group-hooks-list-and-items-bypass-nested-isinstance-guards
tags: [bug, api-contract, meta-fix, infra]
definition_of_done: |
  - [ ] PROCESS: pick one of approach A (shared `load_mapping_or_warn` helper that wraps json.loads / yaml.safe_load and routes every user-editable load through it), B (per-callsite `isinstance(_, dict)` guard at each remaining site), or C (status-quo per-site whack-a-mole). Record the decision in log.md with the rationale. See `## Decision required` below.
  - [ ] MECHANICAL: implement the chosen approach. For A: introduce the helper in `goc/engine.py` (or a shared `goc/_loaders.py`); migrate every documented user-editable callsite through it; a regression test asserts no `yaml.safe_load(...) or {}` or `json.loads(...)` pattern remains unguarded outside the helper for the enumerated callsites. For B: add `isinstance(_, dict)` guards mirroring the closed-sibling shape at `load_deck_config` (engine.py:3842), `_resolve_deck_dir`'s config-probe (engine.py:89), and the canonical-tags fenced-YAML loader (engine.py:467). For C: file the three outstanding instances as separate cards and walk away.
  - [ ] TDD: a reproduce.py builds a tmp repo with `.game-of-cards/config.yaml` containing `null` (one shape) and `[]` (another shape), then runs a code path that calls `load_deck_config()` (e.g. `goc done` or `goc attest`) — currently crashes with `AttributeError`; after the fix, the load surfaces a coherent warning and the command continues or fails with a clean error.
  - [ ] TDD: regression tests covering each enumerated callsite against each non-dict shape (`null`, `[]`, `"string"`, `42`), asserting no `AttributeError` escapes.
  - [ ] PROCESS: cross-link the two closed siblings via `advanced_by` (already wired) so a cold reader sees the family this card retires. If approach A is chosen, also add the helper to `Skill(card-schema)` or `AGENTS.md` as the canonical loader pattern for new user-editable config files.
  - [ ] PROCESS: `uv run goc validate` passes and `uv run python -m unittest discover -s tests` is green.
---

# Unguarded loader callsites keep spawning non-dict shape guard fixes

## The family (closed siblings — same root cause)

Both closed cards added an `isinstance(_, dict)` guard to a specific
loader callsite where the parsed payload is then treated as a mapping:

1. [`frontmatter-that-parses-to-a-list-or-scalar-crashes-loaders-with-a-raw-attributeerror`](../frontmatter-that-parses-to-a-list-or-scalar-crashes-loaders-with-a-raw-attributeerror/)
   — `parse_frontmatter` in `engine.py:161` now raises a clean
   `FrontmatterError` when the YAML between the `---` delimiters
   parses to a non-mapping (was: `AttributeError` on `fm.get(...)`
   inside `load_card`).
2. [`claude-settings-json-that-parses-to-a-non-dict-crashes-install-with-attributeerror`](../claude-settings-json-that-parses-to-a-non-dict-crashes-install-with-attributeerror/)
   — `_merge_claude_settings` (`install.py:567`) and
   `_strip_goc_settings_entries` (`install.py:596`) now backup-and-warn
   / warn-and-return when `.claude/settings.json` is valid JSON of a
   non-dict shape (`null`, list, string, number). Was:
   `AttributeError` on `settings.setdefault(...)` / `settings.get(...)`.

Same root cause both times: a loader returns "valid but wrong shape",
the caller blindly calls a dict method, the result is a raw Python
traceback with no recovery path for the user.

3. [`claude-settings-nested-hooks-shapes-bypass-the-top-level-isinstance-guard`](../claude-settings-nested-hooks-shapes-bypass-the-top-level-isinstance-guard/)
   — same `_merge_claude_settings` / `_strip_goc_settings_entries` pair,
   one layer deeper: `hooks` and `hooks[event]` now also carry
   `isinstance(_, dict)` / `isinstance(_, list)` guards. Closed
   2026-05-30 under Approach B (per-callsite guard, consistent with
   precedent #2).

## Outstanding unguarded callsites

A `grep -n "json.loads\|yaml.safe_load" goc/*.py` against the current
tree surfaces three more user-editable-input callsites with the same
shape:

### 1. `load_deck_config` — `goc/engine.py:3842-3847`

```python
def load_deck_config() -> dict:
    if GAME_OF_CARDS_CONFIG_FILE.exists():
        return yaml.safe_load(GAME_OF_CARDS_CONFIG_FILE.read_text()) or {}
    if LEGACY_DECK_CONFIG_FILE.exists():
        return yaml.safe_load(LEGACY_DECK_CONFIG_FILE.read_text()) or {}
    return {"layer_2_project_dod": [], "layer_3_goc_dod": []}
```

The `or {}` only handles `None`. A `.game-of-cards/config.yaml` whose
top-level YAML is a list (`- foo`), a string (`hello`), or a number
(`42`) returns that shape unchanged. Downstream callers (e.g.
`attest_card` in `engine.py`) then do
`config.get("layer_2_project_dod", [])` and crash with
`AttributeError: 'list' object has no attribute 'get'`.

**Reachability**: `.game-of-cards/config.yaml` is a user-editable file.
The header comment in the install template invites the user to delete
sections; deleting all of them and leaving a blank file is fine, but
leaving any non-mapping content (a stray top-level list, a YAML-lite
scalar at the root) crashes `goc done` / `goc attest`.

### 2. `_resolve_deck_dir`'s config-probe — `goc/engine.py:86-93`

```python
config_path = common_root / ".game-of-cards" / "config.yaml"
if config_path.exists():
    try:
        cfg = yaml.safe_load(config_path.read_text()) or {}
        if (cfg.get("workflow") or {}).get("worktree_deck") == "shared":
            return common_root
    except Exception:
        pass
return cwd
```

The bare `except Exception: pass` swallows the `AttributeError` —
so the crash is invisible, but the worktree-deck-shared check is
*silently broken* whenever `config.yaml` parses to a non-dict. The
user's `worktree_deck: shared` setting fails to take effect with no
warning printed. This is the inverse failure mode of #1: not a
crash, but silent misbehavior. Both are bugs in the same shape.

### 3. Canonical-tags fenced-YAML loader — `goc/engine.py:466-471`

```python
for match in _FENCED_YAML.finditer(extension_file.read_text()):
    block = yaml.safe_load(match.group(1)) or {}
    value = block.get("canonical_tags") or []
    if not isinstance(value, list):
        continue
    out.update(value)
```

The downstream `value` field is guarded (`isinstance(value, list)`),
but `block` itself isn't. A fenced YAML block whose content parses to
a list at the root (a user-authoring mistake — easy to do, since YAML
list-of-strings is the obvious "give me my tags" shape) crashes
`block.get(...)`.

**Reachability**: `.game-of-cards/canonical-tags.md` is user-editable.
The skill that documents it (`Skill(card-schema)`) shows the fenced
block contract, but a user reading the README without that context
might author the block as a bare list — same defect class, same
crash.

### Possibly more

A full sweep should also re-check `goc/install.py:312` (manifest load
— input is package data, not user-editable, so probably fine but worth
verifying) and any `json.load(sys.stdin)` hook entrypoints (input is
the harness's JSON envelope, trusted).

## Why it matters

The two closed siblings already cost two fix cycles, each with their
own reproduce.py, regression test, and review. The three outstanding
callsites are the same pattern with the same fix shape; each will
eventually surface as a user-reported `AttributeError` traceback and
spawn its own card. The audit-deck meta-fix rule says: four instances
of one shape is a deliberate decision — file a meta-fix and decide
whether to keep playing whack-a-mole or close the family at the
source.

The closely-related sibling
[`bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes`](../bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes/)
files the same kind of meta-fix decision for *list-typed* YAML
frontmatter fields where consumers iterate the bare string
character-by-character. That card and this one are structurally
identical (loader returns valid-but-wrong-shape, consumer crashes /
misbehaves) but operate on different shape contracts (dict-at-root
here vs. list-typed-field there). The two could be jointly resolved
by a single "load discipline" decision, or kept separate — the
decision section below names that explicitly.

## Decision required

Pick one of three approaches and record the choice + rationale in
`log.md`:

### Approach A — shared `load_mapping_or_warn(path, *, loader=yaml.safe_load)` helper

Introduce a single helper in `goc/engine.py` (or a new
`goc/_loaders.py` shared with `install.py`) that:

1. Reads the file's bytes.
2. Calls the underlying loader.
3. If the result is `None`: returns `{}` silently (matches the
   existing `or {}` semantic).
4. If the result is a dict: returns it.
5. If the result is any other shape: warns on stderr naming the file
   and the actual `type().__name__`, then returns `{}` (engine-level
   defensive default) or raises a typed exception (caller decides).

Migrate `load_deck_config`, the `_resolve_deck_dir` config-probe, the
canonical-tags fenced-YAML loader, and the install.py settings
loaders (already fixed inline, but the helper would dedupe) through
the helper.

**Pros**: closes the family at the source; one regression test
covers every callsite; future user-editable-config additions get the
guard for free. Symmetric with the
`bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes`
meta-fix if it also picks a centralized-helper approach.

**Cons**: introduces an abstraction across two modules; the helper
must accept both `yaml.safe_load` and `json.loads` (each with their
own exception classes) cleanly; install.py's settings loader has a
backup-and-warn side effect that the helper would need to model or
the callsite keeps inline.

### Approach B — per-callsite `isinstance(_, dict)` guard

Add a guard mirroring the closed-sibling shape at each remaining
callsite. Three sites, three two-line patches, three regression
tests.

**Pros**: minimal blast radius; each fix is mechanically obvious;
exactly the shape the closed siblings used, so the team already
knows the pattern.

**Cons**: doesn't close the family at the source — a future
user-editable-config addition that forgets the guard reintroduces
the bug. Each site needs its own regression test.

### Approach C — status quo, accept the whack-a-mole

File the three outstanding callsites as separate cards and let
`pull-card` work them one at a time. The meta-fix lens stays in
the deck as a record-axis artefact but doesn't drive action.

**Pros**: zero design work; same pattern the team has been applying.

**Cons**: the family is now five fixes deep across two domains
(YAML / JSON) and will continue to recur. The cost of recurrence is
borne by the user who first hits the new crash, not the team that
could close it preemptively.

### Recommendation context (not a binding pick)

Approach **A** is the closure that the audit-deck meta-fix rule
asks for. Approach **B** is the safe minimum that closes the
currently-known sites without restructuring. **C** has no defenders
on the team principles axis but is the cheapest in the short run.
The decision is the human's call — record it in `log.md`.

## Cross-references

- [`frontmatter-that-parses-to-a-list-or-scalar-crashes-loaders-with-a-raw-attributeerror`](../frontmatter-that-parses-to-a-list-or-scalar-crashes-loaders-with-a-raw-attributeerror/) — closed precedent #1 (YAML frontmatter).
- [`claude-settings-json-that-parses-to-a-non-dict-crashes-install-with-attributeerror`](../claude-settings-json-that-parses-to-a-non-dict-crashes-install-with-attributeerror/) — closed precedent #2 (JSON settings).
- [`bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes`](../bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes/) — structurally identical meta-fix decision for list-typed fields. Joint resolution worth considering.
- [`install-overwrites-malformed-claude-settings-json-instead-of-merging`](../install-overwrites-malformed-claude-settings-json-instead-of-merging/) — the JSONDecodeError-side precursor to closed precedent #2.
