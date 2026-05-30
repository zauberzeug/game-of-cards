---
title: pattern-generalization-check-jsonl-per-line-loader-trusts-non-dict-entries
summary: "UNVERIFIED. `goc/templates/hooks/pattern_generalization_check.py` reads the harness's JSONL transcript file line-by-line via `json.loads(line)` and immediately calls `entry.get(...)` in `_extract_tool_names`, `_is_tool_result_only`, `_is_code_mutating`, and the main backward-walk loop without a top-level `isinstance(entry, dict)` guard. A transcript line that parses to a list / scalar / null raises `AttributeError`, the Stop hook exits non-zero, and the pattern-generalization reminder never reaches the agent. Reachability is weak (transcript file is harness-written, not user-editable) so this card is filed unverified pending a falsifying recipe."
status: open
stage: null
contribution: low
created: "2026-05-30T18:02:19Z"
closed_at: null
human_gate: decision
advances:
  - unguarded-loader-callsites-keep-spawning-non-dict-shape-guard-fixes
advanced_by: []
tags: [bug, infra, api-contract, meta-fix, unverified]
definition_of_done: |
  - [ ] TDD: a reproduce.py drops a JSONL transcript file with one line containing `[1,2,3]` (or `null`, or `"oops"`), invokes `_had_code_mutation` against it, and prints whether `AttributeError` escapes. Currently expected: AttributeError fires. After fix: no exception, the line is silently skipped (same semantic as `json.JSONDecodeError`).
  - [ ] PROCESS: decide whether reachability is high enough to warrant a per-callsite guard (Approach B), or whether this site should wait for the meta-fix parent's Approach A (shared `load_mapping_or_warn` helper) to close. Record the decision in log.md.
  - [ ] MECHANICAL: if proceeding now, add a single `if not isinstance(entry, dict): continue` after `json.loads(line)` (line 162 in current tree). Drops the `unverified` tag once the reproduce.py lands.
  - [ ] PROCESS: cross-link to the just-closed sibling `hook-scripts-crash-on-non-dict-stdin-json-with-attributeerror` (which guarded the *whole-payload* stdin parse but not the *per-line* transcript parse) so a cold reader sees the two are distinct callsite shapes.
  - [ ] PROCESS: `uv run goc validate` passes and `uv run python -m unittest discover -s tests` is green.
---

# `pattern_generalization_check` JSONL per-line loader trusts non-dict entries

## Hypothesis (unverified)

`goc/templates/hooks/pattern_generalization_check.py:157-182` walks
the harness's JSONL transcript file backward, parsing each line with
`json.loads`:

```python
for line in reversed(lines):
    line = line.strip()
    if not line:
        continue
    try:
        entry = json.loads(line)
    except json.JSONDecodeError:
        continue

    tool_names = _extract_tool_names(entry)            # line 166

    if tool_names:
        found_assistant = True
        for name in tool_names:
            if _is_code_mutating(name, entry):
                return True
    else:
        msg = entry.get("message", entry)               # line 175
        role = msg.get("role") if isinstance(msg, dict) else entry.get("role")
        ...
```

`json.loads` returns whatever the line parses to. The loop assumes a
dict (`entry.get(...)` at line 175, plus the same shape in
`_extract_tool_names` at line 95, `_is_tool_result_only` at line 118,
and `_is_code_mutating` at line 135). A line that parses to a list,
scalar, or null is valid JSON but raises `AttributeError` on the first
`.get(...)` call — `_extract_tool_names(entry)` at line 166 fires
immediately. The exception escapes `_had_code_mutation`, the Stop
hook exits non-zero, and the pattern-generalization reminder never
reaches the agent.

## Why "unverified"

The hypothesis is real — every cited callsite is in the current tree
and matches the loader-family root-cause shape that the meta-fix
parent
[`unguarded-loader-callsites-keep-spawning-non-dict-shape-guard-fixes`](../unguarded-loader-callsites-keep-spawning-non-dict-shape-guard-fixes/)
catalogues. What's missing is a `reproduce.py` that exhibits the crash
in a realistic flow.

Reachability is weaker than the sibling card
[`claude-settings-nested-hooks-shapes-bypass-the-top-level-isinstance-guard`](../claude-settings-nested-hooks-shapes-bypass-the-top-level-isinstance-guard/):

- The transcript file is written by the Claude Code harness, not by
  the user. A well-behaved harness emits one JSON object per line.
- A malformed line would have to come from (a) a harness bug emitting
  non-dict envelopes, (b) a corrupted/partial flush (truncated bytes
  that parse to a different shape), (c) a user or another tool
  hand-editing the transcript file.

The recently-closed sibling
[`hook-scripts-crash-on-non-dict-stdin-json-with-attributeerror`](../hook-scripts-crash-on-non-dict-stdin-json-with-attributeerror/)
took the same defect family on the *whole-payload stdin parse* of
hook scripts at face value (the harness *is* supposed to emit a
dict, but the guard was added defensively after a crash in the
wild). The per-line transcript loader is one rung less defensible —
but if the bar for the stdin guard was "harness should be trusted
but isn't always," the same bar applies here.

## Falsification recipe

```python
# deck/<title>/reproduce.py
import json, sys, tempfile
from pathlib import Path

def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")

sys.path.insert(0, str(_repo_root()))

from goc.templates.hooks.pattern_generalization_check import _had_code_mutation

with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
    f.write('[1, 2, 3]\n')        # valid JSON, wrong shape
    f.write('null\n')              # valid JSON, wrong shape
    f.write('"oops"\n')            # valid JSON, wrong shape
    path = f.name

try:
    result = _had_code_mutation(path)
    print(f"_had_code_mutation returned {result} (no exception)")
except AttributeError as e:
    print(f"CRASH: AttributeError: {e}")
```

Expected output today: `CRASH: AttributeError: 'list' object has no attribute 'get'`.

## Decision required

Two viable paths:

1. **Wait for the meta-fix parent.** That card asks whether to apply
   a per-callsite `isinstance(_, dict)` guard (Approach B) or to
   route every loader through a shared `load_mapping_or_warn` helper
   (Approach A). This card's fix is a single line either way; just
   not now.
2. **Apply the per-callsite guard now**, drop the `unverified` tag
   once reproduce.py lands. Treat the meta-fix's Approach-A
   consolidation as a later refactor that absorbs this guard.

Both fix the bug. (1) keeps queue noise lower and pressure on the
meta-fix decision; (2) closes the door on this specific symptom
sooner. The decision is the human's; record in log.md.

## Cross-references

- [`unguarded-loader-callsites-keep-spawning-non-dict-shape-guard-fixes`](../unguarded-loader-callsites-keep-spawning-non-dict-shape-guard-fixes/) — meta-fix parent that catalogues this family.
- [`hook-scripts-crash-on-non-dict-stdin-json-with-attributeerror`](../hook-scripts-crash-on-non-dict-stdin-json-with-attributeerror/) — closed sibling that guarded the whole-payload stdin parse; this card is the per-line transcript counterpart.
- [`claude-settings-nested-hooks-shapes-bypass-the-top-level-isinstance-guard`](../claude-settings-nested-hooks-shapes-bypass-the-top-level-isinstance-guard/) — sibling filed in the same audit round, on the nested-JSON layer of `install.py`.
