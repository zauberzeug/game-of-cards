## 2026-10-17T04:55:00Z — Staleness re-check

Option 3 under `## Decision required` says the engine "already requires
PyYAML". It has not since `d490d6d1` (2026-05-09, "engine: replace pyyaml
with vendored yaml_lite.py parser"), twenty days before this card was
filed. The root `pyproject.toml` declares `dependencies = []`, and an `ast`
walk of `goc/`, `templates/hooks/` included, finds no third-party import.
So Option 3 would not reuse a dependency the engine already has. It would
make this hook the only third-party import in the `goc` package, against
the pure-stdlib contract set by `drop-third-party-runtime-dependencies-from-goc`.
The engine's own YAML reader is the vendored `goc/_vendor/yaml_lite.py`.
The options are left as written. This note only corrects the premise for
whoever decides. Found while closing
`plugin-payload-still-declares-click-and-pyyaml-dependencies-the-engine-dropped`
(`6ef6fba3`).
