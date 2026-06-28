## 2026-06-28T02:30:00Z — Closure

- **What changed**: `goc/_vendor/yaml_lite.py:35` — `_INT_RE` tightened from `^-?\d+$` to the canonical decimal-integer form `^-?(0|[1-9][0-9]*)$`, so leading-zero runs (`00`, `007`, `008`, `0123`) fall through to the string branch instead of being `int()`-stripped.
- **Verification**: reproduce.py exits 0 — `008`→`'008'`, `0123`→`'0123'`, `00`→`'00'` (str); `0`/`42`/`-5` still ints; `worker: 008` now yields `_worker_who == '008'`.
- **Audit**: PASS — no principle touched, mechanical fix (parser faithfulness to YAML 1.2 / PyYAML's resolver; no project-specific rubric configured).
- **Project impact**: n/a
- **Tests**: 634 passed / 0 failed / 0 xfailed (full `unittest` suite). Plugin mirrors re-synced (claude/codex/openclaw `goc/_vendor/yaml_lite.py`).
- **Bundled with**: n/a

Found and fixed-through during an empty-queue `pull-card` audit pass (no `human_gate: none` open card was pullable — all three gate-none cards carry active `waiting_on` overlays).

## Closure verification (2026-06-28T02:14:29Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-06-28 — Closure' present
