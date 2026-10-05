---
title: codex-install-guidance-predates-the-codex-plugin-and-its-bundled-engine
summary: "The Codex plugin shipped on 2026-05-18 and gained a bundled goc helper on 2026-06-09, but seven guidance sites never caught up: the game-of-cards.com home page and PERSONAS.md list three delivery channels without Codex, `goc install --help` and a docstring say Codex has no plugin yet, kickoff names no codex-kickoff complement, and goc.md and site/llms.txt tell plugin users to pipx-install a CLI the plugin already bundles. The follow-up the closed claude-install-defaults-to-plugin-path promised for the day the plugin shipped, revisiting the Codex install default, was never filed, so every Codex install still vendors skills on that false premise. No guard derives the channel set from the plugin manifests, so only the surfaces the two plugin commits touched moved."
status: open
stage: null
contribution: high
created: "2026-10-05T01:25:32Z"
closed_at: null
human_gate: none
advances:
  - doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them
advanced_by: []
tags: [bug, documentation, api-contract]
definition_of_done: |
  - [ ] TDD: reproduce.py exits 0 — every surface names the Codex plugin, none says Codex has no plugin, and every Codex install section names the bundled helper
  - [ ] MECHANICAL: `site/index.html` § Install paths gains a Codex plugin bullet and states the channel count `README.md` § Install paths states; `PERSONAS.md` § Runtime channel names the Codex plugin
  - [ ] MECHANICAL: `LOCAL_SKILLS_HELP` and the `_should_use_local_skills` docstring (`goc/install.py`) state the shipped rule — every Codex install vendors `.codex/skills/` and no flag turns that off — without the "no plugin yet" premise
  - [ ] MECHANICAL: `goc.md` § Codex plugin and `site/llms.txt` § Install (Codex) send a plugin-only user to `<plugin-root>/skills/_goc-bootstrap.sh`, as `codex-plugin/README.md` and `Skill(codex-kickoff)` do, and keep `pipx` / `uv tool` for vendored skills without the plugin; `goc.md` drops the claim that skill instructions assume `goc` is callable
  - [ ] MECHANICAL: `Skill(kickoff)` Stage 6's host-complement example names `codex-kickoff`
  - [ ] TDD: a guard in `tests/` derives the channel set from the plugin manifests in the tree and fails when a surface that enumerates delivery channels (`README.md`, `site/index.html`, `PERSONAS.md`, `site/llms.txt`) omits one or states another count, or when a doc or help string says a host whose payload ships has no plugin; fed the pre-fix text, it fires
  - [ ] PROCESS: the Codex install-default follow-up that `claude-install-defaults-to-plugin-path` promised is filed as its own card, cross-linked with `codex-only-install-pins-skills-source-to-plugin-skipping-parity-check` and `codex-install-from-plugin-payload-vendors-skills-and-crashes-on-omitted-templates-skills`, and both closed cards that promised a filing carry a post-close pointer to it
  - [ ] PROCESS: this card's row in the umbrella's instance table names its guard and closure date
  - [ ] MECHANICAL: mirrors re-synced (`python scripts/sync_plugin_assets.py --check` green), OpenClaw skills re-ported (`python3 scripts/port_skills_to_openclaw.py --check` green), `uv run goc validate` and `uv run python -m unittest discover -s tests` pass
---

# Codex install guidance predates the Codex plugin and its bundled engine

The Codex plugin shipped on 2026-05-18 (`f1bd886c`;
[publish-codex-plugin](../publish-codex-plugin/) closed the same day). On
2026-06-09 (`eaed2d24`) it gained `skills/_goc-bootstrap.sh`, a helper that runs
the bundled engine, and every Codex skill gained a `## Codex GoC Command` block
that resolves `goc` through it. Each commit updated the surfaces it had in view —
`README.md` plus new Codex sections in `goc.md` and `site/llms.txt` in the
first; `codex-plugin/README.md` and the Codex skills in the second — and
nothing else. Seven sites still describe the product as it was before one of
those dates, and the card that was to revisit the Codex install default once
the plugin shipped was never filed.

## Location

| # | Site | Written | Stale since | Stale claim |
|---|---|---|---|---|
| 1 | `site/index.html:140-163` — the game-of-cards.com home page | 2026-05-11 | 2026-05-18 | "three first-class delivery channels", three bullets, no Codex |
| 2 | `PERSONAS.md:86` | 2026-05-14 | 2026-05-18 | Runtime channel: Claude Code, OpenClaw, generic CLI |
| 3 | `goc/install.py:1746` — `LOCAL_SKILLS_HELP`, printed by `goc install --help` | 2026-05-07 | 2026-05-18 | "Default for Codex (no plugin yet)" |
| 4 | `goc/install.py:602` — `_should_use_local_skills` docstring | 2026-05-07 | 2026-05-18 | "Codex always uses vendored layout (no plugin yet)." |
| 5 | `goc/templates/skills/kickoff/SKILL.md:222-223` | 2026-05-09 | 2026-05-18 | complement example names `claude-kickoff` and OpenClaw's, not `codex-kickoff` |
| 6 | `goc.md:212` — § Codex plugin › Hooks and CLI behavior | 2026-05-18 | 2026-06-09 | "skill instructions still assume `goc` is callable"; pipx if `goc` is missing |
| 7 | `site/llms.txt:69-72` — § Install (Codex) | 2026-05-18 | 2026-06-09 | pipx if `goc` is missing |

Dates are `git blame` / `git log -S` on each line. Sites 3-5 ship to every
consumer: the engine is mirrored into all three plugin payloads, and the kickoff
skill into four skill trees plus the OpenClaw port. Sites 1, 6 and 7 are served
by the website — `pages.yml` copies `site/` to `/` and renders `goc.md` at
`/goc/`.

## What's broken

### The channel set (sites 1, 2)

`README.md:41` — the install section, which the website also serves raw at
`/index.md`:

> GoC ships through four first-class delivery channels — pick whichever matches
> the agent runtime you already use. All four drive the same engine and deck.

followed by a `**Codex plugin**` bullet at `README.md:44`. `site/index.html:141-142`,
the HTML page at `/`:

> GoC ships through three first-class delivery channels. All three drive the
> same engine and the same deck — pick whichever matches the agent runtime you
> already use.

followed by Claude Code, OpenClaw and Generic CLI bullets, the last "for other
agent runtimes, CI, or no agent" — which is where it sends a Codex user. `f1bd886c`
made exactly this edit to `README.md` (three → four, plus the bullet) and left
`site/index.html` alone. `PERSONAS.md:86` carries the same three-channel list:

> **Runtime channel.** Claude Code (via plugin or pipx), OpenClaw (via ClawHub
> plugin), or the generic `goc` CLI from PyPI for any other agent runtime, CI, or
> no agent at all.

### "No plugin yet" (sites 3, 4)

`goc install --help`:

> --local-skills  Vendor skills, hooks, and settings entries into source
> control. Default for Codex (no plugin yet); opt-in for Claude. …

and the rule behind it, `goc/install.py:599-605`:

```python
def _should_use_local_skills(agent: str, *, local_skills: bool) -> bool:
    """True if this agent should use the vendored skills layout (vs the plugin path).

    Codex always uses vendored layout (no plugin yet).
    Claude defaults to the plugin path; --local-skills opts in to vendored.
    """
    return agent != "claude" or local_skills
```

Both were true on 2026-05-07. Since 2026-05-18 the shipped `Skill(codex-kickoff)`
opens its install stage with "The Game of Cards Codex plugin is published from
this repository's marketplace file" (`goc/templates/skills/codex-kickoff/SKILL.md:35`).
The help text is wrong a second way: the function returns `True` for Codex
whatever the flag says, so "Default for Codex" names a default nothing can opt
out of.

### The kickoff hand-off (site 5)

`goc/templates/skills/kickoff/SKILL.md:222-223`: "If the host has its own
kickoff complement (Claude Code ships `claude-kickoff`, OpenClaw ships its own
equivalent when present), invite the user to run it now". `codex-kickoff` landed
in `f1bd886c` and is listed at line 8 of the same file; the Stage 6 example was
not revisited. Low stakes alone — `codex-kickoff`'s description auto-invokes
after kickoff — but it is the same miss, in a shipped skill.

### The pipx advice (sites 6, 7)

`goc.md:212`:

> Codex does not currently document plugin `bin/` auto-PATH behavior. The plugin
> ships `bin/goc` and the bundled engine for plugin-aware launchers, but skill
> instructions still assume `goc` is callable in the project environment. In this
> source repo, use `uv run goc ...`; in consumer repos, install the CLI with
> `pipx install game-of-cards` or `uv tool install game-of-cards` if bare `goc`
> is missing.

`site/llms.txt:69-72` says the same in two sentences. `eaed2d24` rewrote exactly
this paragraph in `codex-plugin/README.md:27-44`:

> … The plugin therefore ships `skills/_goc-bootstrap.sh`, which invokes the
> bundled engine through the sibling `bin/goc` wrapper. In this source repo, use
> `uv run goc ...`; in plugin-only consumer repos, use:
> `<plugin-root>/skills/_goc-bootstrap.sh --help` … Install `game-of-cards` with
> `pipx` or `uv tool` only when using vendored Codex skills without the plugin
> payload.

`Skill(codex-kickoff)` Stage 2 agrees: "Do **not** create a global
`~/.local/bin/goc` shim — the engine is already bundled" (`:91`), with pipx kept
for "when using vendored Codex skills without the plugin payload" (`:134-137`).
`goc.md`'s middle clause is false too: `CODEX_GOC_COMMAND_RESOLVER`
(`goc/install.py:1407`) writes a `## Codex GoC Command` block into every Codex
skill, vendored or plugin — 16 of 16 in `codex-plugin/skills/`, and in the
`.codex/skills/` a scratch Codex install writes.

### The follow-up that was never filed

Site 3's parenthetical comes from the closed
[claude-install-defaults-to-plugin-path](../claude-install-defaults-to-plugin-path/).
Its DoD (`README.md:24`) kept Codex vendored because "Codex has no plugin yet —
`publish-codex-plugin` is still session-gated. When that ships, a follow-up card
flips the Codex default analogously", and its notes (`README.md:96`) name that
card: "when `publish-codex-plugin` ships, file a follow-up
`codex-install-defaults-to-plugin-path` card." `publish-codex-plugin` closed
2026-05-18T05:33:03Z. No such card exists, so the help text still describes the
interim state as the current one.

A second filing was dropped on the same fact. The closed
[install-docs-still-describe-the-pre-plugin-install-model-and-a-removed-no-harness-flag](../install-docs-still-describe-the-pre-plugin-install-model-and-a-removed-no-harness-flag/)
found site 3 on 2026-10-03. Its README (`:119`) says "Filed separately (see
`log.md`)"; its log (`:27-30`) says "To be filed and fixed through after this
closure." Nothing was filed.

## Empirical evidence

`uv run python .game-of-cards/deck/codex-install-guidance-predates-the-codex-plugin-and-its-bundled-engine/reproduce.py`
— read-only; it derives the channel set from the three plugin manifests plus
the PyPI package, then reads each surface:

```
tree: 4 delivery channels -> Claude Code plugin, Codex plugin, OpenClaw plugin, Generic CLI (PyPI)
tree: codex-plugin ships codex-plugin/skills/_goc-bootstrap.sh: True; 16/16 Codex plugin skills carry the '## Codex GoC Command' resolver

ok:   README.md:41 four channels, Codex plugin listed
ok:   site/llms.txt:39 has an Install (Codex) section
ok:   codex-plugin/README.md:8 sends plugin users to the bundled helper; pipx 'only when using vendored Codex skills without the plugin payload'

FAIL: site/index.html:141 (game-of-cards.com home page): says 'three' channels, lists 3 bullets, names Codex: False  (tree ships four)
FAIL: PERSONAS.md:86 'Runtime channel' lists Claude Code, OpenClaw and the generic CLI; no Codex
FAIL: `goc install --help`, --local-skills: 'Default for Codex (no plugin yet); opt-in for Claude.'
FAIL: goc/install.py:602 _should_use_local_skills docstring: 'Codex always uses vendored layout (no plugin yet).'
info: _should_use_local_skills('codex', local_skills=False) -> True: Codex is vendored on every install, so 'Default for Codex' names a default with no opt-out
FAIL: goc/templates/skills/kickoff/SKILL.md:222 complement example names claude-kickoff and OpenClaw's, not codex-kickoff: 'If the host has its own kickoff complement (Claude Code ships `claude-kickoff`, OpenClaw ships its own equivalent when present)'

FAIL: goc.md:212 § Codex plugin never names _goc-bootstrap.sh; it says 'skill instructions still assume `goc` is callable' (16/16 skills carry a resolver) and sends plugin users to `pipx install game-of-cards`
FAIL: site/llms.txt:69 § Install (Codex) never names _goc-bootstrap.sh; tells plugin users: 'If bare `goc` is not available in a consumer repo, install the CLI with `pipx install game-of-cards`'

info: publish-codex-plugin status=done closed_at=2026-05-18T05:33:03Z
info: claude-install-defaults-to-plugin-path promised a `codex-install-defaults-to-plugin-path` follow-up for that moment; card dir exists: False

RESULT: 7 stale Codex claim(s)
```

Exit 1. Run by hand during the audit: a plain `goc install` in a scratch repo
holding only an `AGENTS.md` auto-detects Codex and writes 16 skill directories
plus `_goc-bootstrap.sh` into `.codex/skills/` — the vendoring site 3 explains
with "no plugin yet".

## Why it matters

- **The home page is the front door.** `README.md`'s "Try it" prompt has the
  agent "look at game-of-cards.com". A Codex user who lands there sees three
  channels and a Generic CLI bullet for "other agent runtimes", and takes the
  pipx route instead of the plugin that ships skills, hooks and the engine
  together. The raw README the same site serves at `/index.md` says the
  opposite.
- **`llms.txt` is followed literally.** It is the recipe `README.md` tells an
  LLM to fetch and follow. In a plugin-only install bare `goc` is not on PATH —
  Codex does not put plugin `bin/` there (`codex-kickoff/SKILL.md:82-84`) — so an
  agent following § Install (Codex) always ends up running
  `pipx install game-of-cards`. That adds a second engine
  whose version tracks PyPI rather than the plugin the skills came from — the
  global install `codex-plugin/README.md` reserves for vendored skills without
  the plugin.
- **`--help` is the flag's contract.** "No plugin yet" tells a Codex user there
  is nothing to install, and "Default for Codex" promises an opt-out that does
  not exist.
- **The dropped follow-up is a deck failure, not just a doc one.** The deck is
  the record of what was decided. Twice a closed card said a follow-up would be
  filed, and neither was. Every Codex install still vendors all 16 skills on a
  premise that has been false for twenty weeks. Meanwhile the open
  Codex install questions — whether `skills_source: plugin` should mean "Claude
  plugin specifically" on
  [codex-only-install-pins-skills-source-to-plugin-skipping-parity-check](../codex-only-install-pins-skills-source-to-plugin-skipping-parity-check/),
  and what a Codex install run from the plugin engine should do on
  [codex-install-from-plugin-payload-vendors-skills-and-crashes-on-omitted-templates-skills](../codex-install-from-plugin-payload-vendors-skills-and-crashes-on-omitted-templates-skills/)
  — sit parked without the plan that was recorded for this moment.

## Root cause

Both plugin commits updated the surfaces their authors had open. Nothing derives
"which delivery channels ship" or "how a Codex plugin user runs `goc`" from the
tree, so every other restatement went stale without a signal.
`tests/test_llms_txt_install_channels.py` already pins `site/llms.txt` against
`README.md`, `ABOUT.md`, `goc.md` and `site/index.html` — for the ClawHub
install command only. The channel set itself is unguarded.

This is an instance of
[doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them](../doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them/),
of its forward-looking-promise shape seen from the far side: "no plugin yet" is
a promise that was kept, and outlived its fulfilment by twenty weeks. It is
also a datum against that card's Option D (require a card slug on every such
claim so the promise has an owner): this one had owners — `publish-codex-plugin`
and a named follow-up — and closing the owner revisited nothing.

## Fix

Not applied here — this card files the defect.

1. **Sites 1, 2.** `site/index.html:140-163`: add a Codex plugin `<li>` matching
   `README.md:44` and change "three … All three" to the README's count.
   `PERSONAS.md:86`: name the Codex plugin in the Runtime channel bullet.
2. **Sites 3, 4.** `goc/install.py:1744-1749` and `:599-605`: describe what the
   code does — every Codex install vendors `.codex/skills/`; `--local-skills` is
   the opt-in for Claude — with no "no plugin yet" premise. The engine mirrors
   follow through `scripts/sync_plugin_assets.py`. If the follow-up in step 5
   changes the Codex default, the text changes with it; until then it states
   the current rule.
3. **Sites 6, 7.** `goc.md:212` and `site/llms.txt:69-72`: replace the paragraph
   with the `codex-plugin/README.md:27-44` version — the bundled helper for
   plugin-only repos, pipx / uv tool only for vendored skills without the plugin,
   `uv run goc` in this source repo — and drop "skill instructions still assume
   `goc` is callable".
4. **Site 5.** `goc/templates/skills/kickoff/SKILL.md:222-223`: name
   `codex-kickoff` in the example, or point at the line-8 list instead of
   re-enumerating it. Re-sync the mirrors and re-run
   `scripts/port_skills_to_openclaw.py`.
5. **The follow-up.** File the card `claude-install-defaults-to-plugin-path`
   promised: should Codex installs defer to the plugin the way Claude installs
   do? It is not mechanical — Codex plugin hooks are opt-in, Codex does not put
   plugin `bin/` on PATH, and the two open cards above already pull on the same
   rule — so it gets its own card and its own gate. Cross-link it with both, and
   add post-close pointers to it on the two closed cards that promised it.
6. **Guard.** A test that builds the channel set from
   `claude-plugin/.claude-plugin/plugin.json`, `codex-plugin/.codex-plugin/plugin.json`
   and `openclaw-plugin/openclaw.plugin.json` plus the PyPI package, then checks
   that every surface enumerating channels (`README.md` § Install paths,
   `site/index.html` `#install`, `PERSONAS.md` Runtime channel, the
   `site/llms.txt` `## Install (…)` headings) names each host and states the
   right count, and that no doc or help string pairs a shipped host with "no
   plugin". Per the umbrella's rule that a guard's pattern holds only the value
   it derives, the count word is computed, not written into the regex. The
   bootstrap claim can share the file: while `codex-plugin/skills/_goc-bootstrap.sh`
   exists, every section that tells a Codex plugin user how to run `goc` names
   it. Feed the pre-fix text to prove each check fires.

## Not in scope

- Whether Codex installs should stop vendoring — step 5 files it; the decision
  belongs on that card.
- Why a plain `goc install` picks Codex at all in a repo with an `AGENTS.md`:
  [install-auto-detects-codex-from-the-shared-agents-md-briefing-file](../install-auto-detects-codex-from-the-shared-agents-md-briefing-file/).
- `PERSONAS.md:74-76`, on the same page: under what GoC "doesn't fully ship
  yet" it lists "Multi-human + multi-agent claim metadata" and says
  [design-claim-protocol-with-branch-and-author-metadata](../design-claim-protocol-with-branch-and-author-metadata/)
  "covers this". That card closed 2026-05-09, having shipped the
  `worker: {who, where}` field and the opt-in `workflow.claim_push`. Same shape,
  different fact. It is recorded on the umbrella's log rather than filed here;
  the edit to `PERSONAS.md` in step 1 is the cheap moment to correct it too.

Surfaced by the audit-deck pass of 2026-10-05: the filing agent's own sweep of
the public doc surfaces, after a deck-card link check of `PERSONAS.md` led to
its channel bullet.
