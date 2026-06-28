---
title: upgrade-divergence-report-marks-pristine-config-as-authored-divergence
summary: "On a consumer's first `goc upgrade`, a never-user-edited config.yaml is classified `preserved` (authored divergence) in the divergence report, because `goc install` itself rewrites the `skills_source:` key after copying the template, so the file can never be byte-identical to the template. The `upgrade` skill treats every `evolving` + `preserved` file as authored divergence and drives an interactive 2-way LLM reconcile — so every consumer eats a needless reconcile prompt for config.yaml that can flip the engine-managed key."
status: open
stage: null
contribution: medium
created: "2026-06-25T14:30:42Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract, infra]
definition_of_done: |
  - [ ] PROCESS: decision recorded below (which disambiguation mechanism) with rationale in log.md
  - [ ] TDD: reproduce.py exits zero today; after the fix, a pristine (install-mutated, never-user-edited) config.yaml reports `unchanged` in the divergence report — update reproduce.py to assert the post-fix status and that it still exits zero as the regression guard
  - [ ] TDD: a config.yaml with a *real* user edit (beyond skills_source) still reports `preserved`
  - [ ] TDD: the existing plan-level contract in tests/test_upgrade_preserves_user_owned_content.py is reconciled with the chosen mechanism (either it still asserts `preserved` at the plan level with the report diverging, or it is updated — whichever the decision picks)
  - [ ] MECHANICAL: `uv run python -m unittest discover -s tests` and `uv run goc validate` pass
---

# upgrade-divergence-report-marks-pristine-config-as-authored-divergence

## Location

- `goc/install.py:987-999` — `_classify_user_owned_file` (raw byte compare).
- `goc/install.py:1545` and `goc/install.py:1780` — `goc install` calls
  `_write_skills_source(target, ...)` immediately after copying the
  template config.
- `goc/install.py:1439-1469` — `_write_skills_source` rewrites the
  `skills_source:` line.
- `goc/templates/game_of_cards/config.yaml:82` — ships
  `# skills_source: auto` (commented).
- `goc/templates/skills/upgrade/SKILL.md:55-57` — the consumer that
  reconciles every `evolving` + `preserved` file.

## What's broken

`_classify_user_owned_file` decides `unchanged` vs `preserved` purely
by byte-equality against the shipped template:

```python
def _classify_user_owned_file(template: Path, dest: Path) -> str:
    """...Returns one of: `create` ..., `unchanged` (byte-identical),
    or `preserved` (diverged — never overwrite on upgrade)."""
    if not dest.exists():
        return "create"
    try:
        return "unchanged" if dest.read_bytes() == template.read_bytes() else "preserved"
    except OSError:
        return "preserved"
```

But `goc install` *itself* mutates `config.yaml` right after copying it
— `_write_skills_source` rewrites the template's commented
`# skills_source: auto` into an active `skills_source: plugin` (or
`vendored`). So a freshly-installed, never-user-touched `config.yaml`
can **never** be byte-equal to the template, and always classifies
`preserved`.

The divergence-report consumer treats `preserved` as authored
divergence. From `goc/templates/skills/upgrade/SKILL.md:55-57`:

> **For each `evolving` file with `status: preserved`** — read the
> local file ... AND the shipped template ... Drive a 2-way reconcile:

and the reconcile escalates to the human via `AskUserQuestion`. So on
**every consumer's first `goc upgrade`**, the skill performs an LLM
2-way reconcile of `config.yaml` (`skills_source: plugin`) against the
template (`# skills_source: auto`) even though the user changed
nothing. The reconcile can re-comment or flip the GoC-managed
`skills_source` key the engine just set.

The conflation is that one classifier (`_classify_user_owned_file`)
feeds two consumers with different meanings of `preserved`:

- the **plan** uses it as "do not overwrite" (correct — the engine must
  never clobber config.yaml), and
- the **divergence report → upgrade skill** uses it as "the user
  authored a divergence, reconcile it" (wrong for an install-mutated
  pristine file).

## Empirical evidence

`reproduce.py` simulates a pristine install (copy template + engine's
own `_write_skills_source`) with zero user edits, then classifies:

```
template skills_source line: '# skills_source: auto'
installed skills_source line: 'skills_source: plugin'
byte-identical to template: False
divergence-report status: preserved

ownership='evolving' -> upgrade skill drives LLM reconcile: True

DEFECT CONFIRMED: a pristine config.yaml (no user edits) is
reported as `preserved` (authored divergence) and would
trigger a needless interactive reconcile on first upgrade.
```

`README.md` (also `evolving`, but NOT mutated by install) correctly
reports `unchanged` on a pristine upgrade — only config.yaml is
affected, confirming the cause is install's own write, not a general
classifier bug.

## Why it matters

The reachability path is the shipping install→upgrade flow with no
unusual input: `goc install [--claude|--codex|--local-skills]` writes
`skills_source: <value>` into config.yaml (`install.py:1545`/`:1780`),
then on the consumer's next `goc upgrade` the engine emits the
divergence report (`status: preserved` for config.yaml), and
`Skill(upgrade)` reads it and runs an interactive 2-way reconcile.
This is not a hypothetical edge case — it fires for *every* consumer
who installs and later upgrades. The user-visible symptom is an
`AskUserQuestion` reconcile prompt for a file they never touched, and
a reconcile pass that diffs the live `skills_source` against the
template's commented placeholder and may flip the engine-managed key.

Related closed work touched the same `_write_skills_source` mechanics
([write-skills-source-strips-crlf-line-endings-from-config-yaml](../write-skills-source-strips-crlf-line-endings-from-config-yaml/))
but none addressed the divergence-report *classification*.

## Decision required

The fix needs a human pick because the plan and the divergence report
share one classifier (`_classify_user_owned_file`), and an existing
test (`tests/test_upgrade_preserves_user_owned_content.py:229-232`)
explicitly asserts and documents `preserved` as the *intended*
plan-level label for config.yaml:

```python
# config.yaml is preserved because install's _write_skills_source
# diverges it from the shipped template (skills_source: plugin gets
# added). The plan must surface that as `preserved`, not `sync`.
self.assertEqual("preserved", actions[".game-of-cards/config.yaml"])
```

So the plan must keep treating config.yaml as never-overwrite; only the
*report → reconcile* path is wrong. Candidate mechanisms:

- **Option A — normalize before comparison.** When classifying
  config.yaml, compare the destination against a template copy run
  through `_write_skills_source` with the destination's current
  `skills_source` value. A config differing from the template *only*
  in the engine-managed key then reports `unchanged`; a real user edit
  still reports `preserved`. Single-site, but the plan label changes
  too (so the cited test must be updated — the plan never overwrites
  evolving files regardless of label, so this is safe behaviorally).

- **Option B — strip the engine-managed line from the comparison.**
  Compare destination-minus-`skills_source` against
  template-minus-`skills_source`. Simpler than A but assumes the only
  engine-managed key is `skills_source` (a coupling that future
  managed keys would silently break unless extended).

- **Option C — split plan classification from report classification.**
  Keep the plan label `preserved` (satisfying the existing test as-is)
  but compute the divergence-report `status` for evolving files with a
  normalize-aware comparison, so only the report (and thus the reconcile
  trigger) changes. Preserves the documented plan contract verbatim at
  the cost of two classification paths.

- **Option D — add an `engine-managed` status** distinct from
  `unchanged`/`preserved`, surfaced in the report so the upgrade skill
  skips reconcile for it. Most explicit; widens the report schema and
  the upgrade skill's branch logic.

Recommendation leans A or C (A is the smallest single-site change but
edits the test's asserted label; C preserves the test verbatim but
forks classification). Do NOT apply until the mechanism is chosen.

## Fix

Per the chosen option above. In all cases, the regression guard is:
a pristine (install-mutated) config.yaml reports `unchanged` in the
divergence report, while a config with an authored edit beyond
`skills_source` still reports `preserved`.
