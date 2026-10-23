## 2026-10-07T04:40:00Z — Filed

Filed while closing
`codex-install-guidance-predates-the-codex-plugin-and-its-bundled-engine`,
whose DoD asked for the follow-up that `claude-install-defaults-to-plugin-path`
promised when `publish-codex-plugin` shipped. A second closed card,
`install-docs-still-describe-the-pre-plugin-install-model-and-a-removed-no-harness-flag`,
also promised it. Both closed cards now carry a post-close pointer here.

The gate is decision because the default is a policy call between credible
options (A/B/C in the body), not a mechanical edit. The two parked Codex install
cards are cross-linked in the body with no edge: this card governs them, and a
governing decision gets a shared tag and no edge.

Dedup: no card named `codex-install-defaults-to-plugin-path` existed; only the
two promising cards and the filing card mention the name.

## 2026-10-23 — Option A's cost amended from a confirmed sibling

A pull-card run confirmed
`codex-only-install-pins-skills-source-to-plugin-skipping-parity-check` with a
reproducer. Codex-only, mixed `claude,codex` and codex-only `--local-skills`
installs all pin `skills_source: plugin`, and `goc validate` then skips the
vendored `.codex/skills/` tree. Option A's cost line said only "the duplicate
skill tree", so it was extended in place: as shipped, A also leaves that tree
unchecked, and making A deliberate includes the sibling's Option A (a
Claude-only key, with the Codex tree always checked). That card is parked at
`decision` with Options A (Claude-only) and B (per-host). Its B is what this
card's options B and C would need. No change to this card's options or
recommendation.

## 2026-10-23 — Connected to a root decision card

Filed `goc-never-records-which-agent-harnesses-it-installed-or-in-which-mode`
as the governing decision over this card, the codex-only parity card and
`goc-upgrade-drops-plugin-mode-claude-in-dual-claude-codex-installs`. All
three ask, from different sides, whether install state should be recorded.
A root pointer was added under the options, with no edge. This card's options
and recommendation are unchanged.
