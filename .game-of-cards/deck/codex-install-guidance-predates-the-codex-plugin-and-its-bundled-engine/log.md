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

## 2026-10-07T04:48:00Z — Resumed and fixed

Resumed the stale claim from 2026-10-05. That pull-card run edited files but
died before committing, and the 2026-10-06 run stopped on an API spend limit
before it started. Runs are serialized, so no other session held the claim.

- `27db384e`: the home page and `PERSONAS.md` name the Codex plugin; the home
  page says four channels. `LOCAL_SKILLS_HELP` and the
  `_should_use_local_skills` docstring drop "no plugin yet" and state the
  shipped rule. `goc.md` § Codex plugin and `site/llms.txt` § Install (Codex)
  send plugin-only users to `<plugin-root>/skills/_goc-bootstrap.sh` and keep
  pipx / uv tool for vendored skills without the plugin. `goc.md` no longer
  says skills assume `goc` is callable. Kickoff Stage 6 names `codex-kickoff`.
  Mirrors re-synced, OpenClaw skills re-ported.
- `0f2f8455`: `tests/test_delivery_channel_surfaces.py` derives the channel set
  from the plugin manifests plus the PyPI package. Copied into a worktree at
  `f510cbe1`, it fails all three tree checks with the seven stale sites. Its
  pre-fix-excerpt tests pass on the fixed tree.
- `4d5caec1`: filed `codex-install-defaults-to-plugin-path`, gate decision,
  with options A/B/C. It is cross-linked with the two parked Codex install
  cards by body pointers and no edge, since it is a governing decision.
  `claude-install-defaults-to-plugin-path` and
  `install-docs-still-describe-the-pre-plugin-install-model-and-a-removed-no-harness-flag`
  carry `## Post-close follow-up` pointers to it.
- The umbrella's instance row names the guard and the 2026-10-07 closure.

`reproduce.py` exits 0. Not done: the `PERSONAS.md:74-76` claim-metadata
staleness in § Not in scope stays recorded on the umbrella's log, because it is
outside this DoD.

## 2026-10-07T04:52:00Z — Closure

- **What changed**: `site/index.html` and `PERSONAS.md` name the Codex plugin
  (home page: four channels). `goc/install.py` `LOCAL_SKILLS_HELP` and the
  `_should_use_local_skills` docstring state the shipped Codex rule without
  "no plugin yet". `goc.md` § Codex plugin and `site/llms.txt` § Install (Codex)
  route plugin-only users to `skills/_goc-bootstrap.sh`. Kickoff Stage 6 names
  `codex-kickoff`. New guard: `tests/test_delivery_channel_surfaces.py`.
- **Verification**: `reproduce.py` exits 0 ("every surface agrees with the
  shipped Codex plugin"). The new guard fails all three tree checks on the
  pre-fix tree `f510cbe1`, with the seven stale sites, and its 9 tests pass on
  the fixed tree. `sync_plugin_assets.py --check` and
  `port_skills_to_openclaw.py --check` are green, and `goc validate` exits 0.
- **Audit**: no rubric configured; mechanical fix
- **Project impact**: n/a
- **Tests**: 1239 passed / 0 failed / 0 xfailed (`uv run python -m unittest discover -s tests`)
- **Filed**: `codex-install-defaults-to-plugin-path` (gate decision), the
  Codex install-default follow-up two closed cards promised. Both now carry
  post-close pointers to it.

## Closure verification (2026-10-07T04:39:31Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 9/9 ticked
- [x] log-md-closure-entry — '## 2026-10-07 — Closure' present
