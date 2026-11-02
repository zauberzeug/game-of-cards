## 2026-11-02T01:02:06Z — Parked sibling: `scripts/set_cadence.py` validates a normalized spec and writes the raw one

Same shape as this card in a different module: a newline gets past validation and lands in a written file. It has not been filed separately, because the run that found it filed one new card. Recorded here so the decision on this card can weigh whether the "validate exactly what you write" rule should hold beyond `title_pattern`.

- **Hypothesis**: `interval_to_cron` matches `_SPEC_RE` (`scripts/set_cadence.py:67`, `\s*` between every part) against `spec.strip().lower()` (`:96`). `retune` then hands the *raw* `spec` to `_cadence_comment` (`:176`), which interpolates it into `f"    # cadence: {label} every {spec} (minute offset ..."` (`:155`).
  - A spec carrying a line break, such as `"3h\n+1"`, still parses as `3h+1`.
  - The break splits the managed comment line, leaving a non-comment line inside the workflow's `on.schedule` block.
  - `retune` reports `changed=True`, and a later clean retune does not repair it: `_CADENCE_RE.subn` (`:194`) rewrites only the `# cadence:` line.
- **Observed by the surfacing agent** (on a copy of `pull-card.yml`): `retune` accepted `'3h\n+1'` and wrote cron `'13 1-23/3 * * *'`. PyYAML then raised `ScannerError` on the file, and still did after a follow-up `--pull 24h+4`. A trailing `"1w\n"` gave `ParserError`.
- **Falsification recipe**: run `retune(tmp_repo, "pull", "3h\n+1")` against a copy of `.github/workflows/pull-card.yml`, then `yaml.safe_load` it. Once fixed, the spec is refused, or the comment is built from the normalized spec, and the file stays loadable.
- **Reach**: the script is repo-local (it backs the repo-only `tune-cadence` skill) and the trigger is a line break inside one CLI argument. The impact, though, is a workflow file GitHub can no longer parse, so its scheduled runs stop.
- **Surfaced by**: an `audit-deck` hunter agent (general-purpose), 2026-11-02.
