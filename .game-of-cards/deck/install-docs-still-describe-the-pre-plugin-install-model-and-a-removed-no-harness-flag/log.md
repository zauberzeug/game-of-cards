## 2026-10-03T04:55:00Z — Hypothesis verified

Claimed from the ready queue. In scratch repos, `goc install --no-harness`
exits 2 (`unrecognized arguments`). `goc install --agents claude` writes
`CLAUDE.md` (an `@AGENTS.md` import) and `skills_source: plugin`, with no
`.claude/` directory and no `SKILL.md`. Neither escape in the falsification
recipe fired, so the `unverified` tag comes off.

For reference, each mode the pages could describe:

- `--agents claude --local-skills` vendors 16 skill dirs plus
  `_goc-bootstrap.sh`, 3 hook scripts and `.claude/settings.json`, and pins
  `vendored`.
- `--agents codex` vendors 16 skills into `.codex/skills/`.
- A plain `goc install` in a repo with an `AGENTS.md` auto-detects Codex and
  vendors `.codex/skills/`. That is why the fixed pages say a plain install
  writes nothing into `.claude/skills/` rather than "writes no skills".

`reproduce.py` exits 1 on the pre-fix pages with six contradicted claims (see
the README § Evidence).

Two findings came out of the reading:

- `.github/workflows/pages.yml` embeds a second, stale `llms.txt`, which
  `site/llms.txt` overwrites at build time. Already tracked as
  `pages-workflow-embeds-stale-llms-txt-kept-off-the-site-only-by-copy-order`.
- `goc install --help` says `--local-skills` is the "Default for Codex (no
  plugin yet)", and the `_should_use_local_skills` docstring says the same,
  though `codex-plugin/` ships. To be filed and fixed through after this
  closure.

## 2026-10-03T05:12:59Z — Closure

- **What changed**:
  - `ABOUT.md` § "Agent harnesses": `--agents claude` writes `CLAUDE.md` and
    no skills or hooks. A new `--agents claude --local-skills` bullet lists
    what vendoring writes. `--no-harness` is gone from the bullets and the
    detection sentence. OpenCode is routed to
    `goc install --agents claude --local-skills`.
  - `README.md` Generic CLI bullet: plain `goc install` suffices for running
    `goc` by hand. OpenCode and custom runners get the `--local-skills`
    invocation.
  - `goc.md`: the skill-count parenthetical names the vendoring invocation,
    and § "Install into a repo" gains a per-harness list of what is written.
  - `site/llms.txt` § "Install (other agent runtimes / CI)": same OpenCode
    sentence.
  - `tests/test_guidance_accuracy.py`: `test_claude_skill_count_matches_payload`
    pins only the count, scoped to the Claude plugin section.
  - New guard `tests/test_install_doc_claims.py` (2 tests, 4 checks): every
    documented install/upgrade flag must be in the verb's `--help` usage;
    harness bullets are checked against a scratch install; OpenCode routes
    must vendor `.claude/skills/`; goc.md's count must equal what its
    invocation vendors.
  - The edge to `doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them`
    is wired, with a table row, the count sentence and a log entry there.
- **Verification**:
  - `reproduce.py` exits 1 on the pre-fix tree (f27e415e), with six
    contradicted claims, and exits 0 on the fix (16 claims checked).
  - Pointed at the pre-fix tree, the new live test fails with the same six
    contradictions plus the one-hook-script-per-template clause. Fed the
    pre-fix wording, the fixture test sees all four checks fire.
  - A scratch-copy mutation that flips `_should_use_local_skills` back to
    vendoring turns the guard red on the "no skills or hooks" bullets in
    `ABOUT.md` and `goc.md`.
- **Audit**: no rubric configured; mechanical fix. (The new guard follows this
  repo's doc-accuracy convention of checking a doc claim by running it
  against the engine rather than restating it.)
- **Project impact**: a scripted install copied from `ABOUT.md` no longer
  exits 2. OpenCode users who follow any install page now get skill files.
  The goc.md guard no longer protects a false clause.
- **Tests**: 1217 passed / 0 failed (`uv run python -m unittest discover -s
  tests`). `goc validate`, `sync_plugin_assets.py --check`,
  `port_skills_to_openclaw.py --check`, `check_card_language.py` and
  `check_card_frontmatter_yaml.py` are all clean.

## Closure verification (2026-10-03T05:13:02Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-10-03 — Closure' present
