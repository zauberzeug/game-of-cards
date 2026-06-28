## 2026-06-25: closed (done)

Surfaced during a pull-card audit (ready queue empty — every open
`human_gate: none` card carried a `waiting_on` overlay). Fixed through
in the same session.

**Defect:** the `create-card` and `deck` skill descriptions advertised
a "reproduce.py stub" as a `goc new` scaffold deliverable, but
`_cmd_new` (`engine.py:4905`) writes only `README.md` + `log.md`.
reproduce.py is hand-authored in create-card Step 6.

**Fix:** reworded both source-of-truth templates
(`goc/templates/skills/create-card/SKILL.md:3`,
`goc/templates/skills/deck/SKILL.md:248`) to frame reproduce.py as a
manual authoring step. Re-synced the five plugin mirrors via
`scripts/sync_plugin_assets.py` and `scripts/port_skills_to_openclaw.py`.

**Regression guard:** `tests/test_guidance_accuracy.py` gains
`CreateCardScaffoldClaimAccuracyTest` — one test asserts no skill
description advertises a "reproduce.py stub", a second pins the actual
`goc new` file-set contract (`README.md` + `log.md`).

**Verification:** reproduce.py exits 0 (was 1); `uv run goc validate`
clean; 593 tests pass; both sync `--check` and port `--check` clean.
