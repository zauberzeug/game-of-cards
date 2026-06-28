# Game of Cards Codex plugin

This plugin packages Game of Cards for Codex:

- GoC skills under `skills/`
- lifecycle hooks under `hooks/hooks.json`
- a bundled `goc/` engine mirror, `bin/goc`, and
  `skills/_goc-bootstrap.sh`

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
therefore ships `skills/_goc-bootstrap.sh`, which invokes the bundled engine
through the sibling `bin/goc` wrapper. In this source repo, use
`uv run goc ...`; in plugin-only consumer repos, use:

```bash
<plugin-root>/skills/_goc-bootstrap.sh --help
```

If the plugin root is not obvious from the loaded skill path, find the helper
under Codex's plugin cache:

```bash
find "$HOME/.codex/plugins/cache" -path '*/game-of-cards/*/skills/_goc-bootstrap.sh' -type f -perm -111
```

Install `game-of-cards` with `pipx` or `uv tool` only when using vendored
Codex skills without the plugin payload.
