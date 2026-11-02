## 2026-10-15T04:37:29Z — The vendored-to-plugin cleanup no longer depends on this detection

[plugin-engine-cleanup-leaves-every-goc-skill-dir-its-prompt-promises-to-remove](../plugin-engine-cleanup-leaves-every-goc-skill-dir-its-prompt-promises-to-remove/)
needed the bundled engine to know GoC's skill names. It gets them from
`_goc_skill_names` in `goc/install.py`, which reads the payload's own flat
`skills/` tree whenever `templates/skills/` is absent. The check looks at
that tree, not at `_is_plugin_context()`.
`tests/test_install.py` stages the engine under a
`plugins/cache/mkt/game-of-cards/0.0.28/` root and confirms the cleanup
there. That is the layout where this card's detection returns False.
Whichever mechanism this card picks, that site needs no change. It is one
working instance of option 1's capability probe, limited to a read that
only gates deletions the user has confirmed. The `--local-skills` refusal and
the OpenClaw no-harness default still depend on the detection, unchanged.

## 2026-11-02T01:02:06Z — Parked consumer: `goc install` tells the agent to install the plugin it is running from

This is another consumer that needs this card's detection. It is recorded here, not filed, because the run that found it filed one new card, and because this card's decision sets what that consumer can consult.

- **Hypothesis**: `goc/install.py:1962-1967` prints `GoC plugin: to enable skills and hooks, ask the user to confirm then run:` followed by `_PLUGIN_INSTALL_CMDS` (`/plugin marketplace add ...` / `/plugin install ...`). The condition is only `"claude" in agents`, Claude not vendored, and `_detect_claude_code()`. `_is_plugin_context()` is never consulted, so an install run *by* the plugin's own `bin/goc` still asks the user to install that plugin. That contradicts `goc/templates/skills/claude-kickoff/SKILL.md:59-61`: "Skip this stage if Claude Code's plugin runtime already exposes the GoC skill set in this session".
- **Observed by the surfacing agent**: `claude-plugin/bin/goc install` with `CLAUDECODE=1` in a scratch repo printed the hint.
- **Dependency on this card**: consulting `_is_plugin_context()` there would only help in this source tree. On a real marketplace install it returns False (this card's finding), so the hint stays wrong until this card's detection mechanism is decided.
- **Falsification recipe**: run the plugin wrapper's `install` with `CLAUDECODE=1` in a scratch repo, from both the source-tree payload and a `<mkt>/game-of-cards/<version>/` copy. Once fixed, neither prints the `/plugin install` hint.
- **Surfaced by**: an `audit-deck` hunter agent (general-purpose), 2026-11-02.
