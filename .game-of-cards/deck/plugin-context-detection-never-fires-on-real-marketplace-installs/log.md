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
