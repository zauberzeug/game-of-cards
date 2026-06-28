# Log

## 2026-06-25 — filed (audit)

Surfaced during a pull-card audit pass (ready queue empty). Confirmed
via `reproduce.py`: a pristine, never-user-edited `config.yaml` reports
`preserved` in the upgrade divergence report because `goc install`
mutates the `skills_source:` key after copying the template, so the
file is never byte-identical to its template. The `upgrade` skill
treats every `evolving` + `preserved` file as authored divergence and
drives an interactive 2-way LLM reconcile — so every consumer's first
`goc upgrade` eats a needless reconcile prompt for config.yaml that can
flip the engine-managed key.

Filed at `human_gate: decision`: the plan and the divergence report
share `_classify_user_owned_file`, and `tests/test_upgrade_preserves_
user_owned_content.py:229-232` explicitly asserts `preserved` as the
intended *plan-level* label for config.yaml. Disambiguating
engine-managed divergence from authored divergence has multiple
credible mechanisms (normalize-before-compare, strip-managed-line,
split plan-vs-report classification, or add an `engine-managed`
status) — see `## Decision required` in README.
