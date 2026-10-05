## 2026-10-05T01:25:32Z — Filed

Filed by an audit-deck pass. The lead was a link check of the deck cards
`PERSONAS.md` cites, which led to its Runtime channel bullet. That bullet omits
Codex, and so does the home page, while `README.md` lists Codex as the fourth
channel. The sweep that followed found the other five sites in the README's
Location table and the two follow-up filings that never happened.
`reproduce.py` exits 1 with seven stale claims.

Dedup: no card names the channel count, `no plugin yet`, the `Runtime channel`
bullet, or the Codex sections of `goc.md` / `site/llms.txt`. The closed
`cli-reference-plugin-sections-describe-a-payload-goc-no-longer-ships` swept
`goc.md`'s Claude Code and OpenClaw sections, not its Codex section. The closed
`install-docs-still-describe-the-pre-plugin-install-model-and-a-removed-no-harness-flag`
found site 3 and promised a card, which was never filed. The audit commit
`e6701c20` listed "site/index.html omits the Codex channel" among unfiled
lower-ranked observations, so the gap was seen once and dropped. No `disproved`
card touches these strings.

Gate none: sites 1-7 are fixed by what the tree already ships. The one real
decision, whether Codex installs should defer to the plugin, is split out into
the follow-up the DoD files rather than taken here.
