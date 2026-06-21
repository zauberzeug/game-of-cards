# Log

## 2026-06-21 — filed and fixed through (pull-card, queue empty → audit-deck)

Surfaced during a pull-card run where the ready queue was empty (all 113
open cards gated `decision`/`session`, or carrying an indefinite
`waiting_on` overlay). Audit-deck hunters swept `goc/install.py`,
`goc/templates/hooks/*.py`, and `scripts/*.py`; this was the
top-ranked, fully-undocumented finding.

**Root cause.** The `upgrade` skill (`goc/templates/skills/upgrade/`)
was added 2026-05-30 (`f76dace`); `openclaw-plugin/openclaw.plugin.json`'s
hand-maintained `skills` array was last edited 2026-05-10 (`417fbd9`),
before the skill existed. The porter ships every source skill, so
`openclaw-plugin/skills/upgrade/SKILL.md` exists, but the manifest never
registered it. Neither `port_skills_to_openclaw.py --check` nor the CI
parity test catches it — both compare ported SKILL.md *content* only.

**Empirical evidence (before fix):**

```
ported skill dirs (16): ... standup, upgrade
manifest skills (15): ... scan-deck, standup
ported but NOT registered in manifest: {'upgrade'}
manifest description claims: 15 deck skills (actual ported: 16)
DEFECT CONFIRMED          # exit=1
```

**Fix applied:**
1. Added `"skills/upgrade"` to the `skills` array in
   `openclaw-plugin/openclaw.plugin.json`.
2. Corrected the description from "15 deck skills" to "16 deck skills".
3. Added `OpenClawManifestSkillRegistrationTest` to
   `tests/test_plugin_mirror_parity.py` — asserts the manifest `skills`
   set equals the ported skill-dir set (both directions) and that the
   description count matches the ported count. Lives in a test, not a
   `ci.yml` step, because the bot's `GITHUB_TOKEN` cannot edit workflow
   files (same rationale as the existing porter drift guard).

**Empirical evidence (after fix):**

```
ported skill dirs (16): ... standup, upgrade
manifest skills (16): ... standup, upgrade
ported but NOT registered in manifest: {}
registered but NOT ported: {}
manifest description claims: 16 deck skills (actual ported: 16)
OK — manifest in sync     # exit=0
```

Full regression suite `OK`; `port_skills_to_openclaw.py --check`,
`sync_plugin_assets.py --check`, and `goc validate` all green.
