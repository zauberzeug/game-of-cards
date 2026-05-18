# Game of Cards Codex plugin

This plugin packages Game of Cards for Codex:

- GoC skills under `skills/`
- lifecycle hooks under `hooks/hooks.json`
- a bundled `goc/` engine mirror plus `bin/goc`

Install from this repository's marketplace:

```bash
codex plugin marketplace add zauberzeug/game-of-cards
```

Then open `/plugins`, choose the `Game of Cards` marketplace source, and
install `game-of-cards`.

Plugin hooks are opt-in in the current Codex runtime. To enable the active-card
reminder, prompt router, and pattern-generalization hook, add:

```toml
[features]
plugin_hooks = true
```

Codex does not currently document plugin `bin/` auto-PATH behavior. The plugin
ships `bin/goc` and a bundled engine for plugin-aware launchers, but GoC skills
still expect `goc` to be callable in the project environment. In this source
repo, use `uv run goc ...`; in consumer repos, install `game-of-cards` with
`pipx` or `uv tool` if bare `goc` is not available.
