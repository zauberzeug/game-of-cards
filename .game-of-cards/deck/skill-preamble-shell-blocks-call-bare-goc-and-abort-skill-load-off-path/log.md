# skill-preamble-shell-blocks-call-bare-goc-and-abort-skill-load-off-path — log

## 2026-07-13 — Filed

Filed during a deck hygiene pass after observing the failure live:
`Skill(refine-deck)` errored at load with
`Shell command failed for pattern "!\`goc --tag unverified -v\`": /bin/bash: line 1: goc: command not found`
on a cloud runner in this repo. Surveyed the template tree: six skills
carry bare-`goc` `!` blocks, none invoke `_goc-bootstrap.sh`, and only
`refine-deck`'s validate block is exit-code-guarded. Wired
`advanced_by: bootstrap-error-when-cli-not-on-path` (the closed card
whose DoD guarantee this regresses).

## 2026-07-15 — Fix shape decided: (c) both routing and guard

Chose (c): every goc-invoking `!` fence rewritten to
`b=.claude/skills/_goc-bootstrap.sh; if [ -f $b ]; then sh $b <args>;
else goc <args>; fi 2>&1 || true` (piped fences keep their trailing
`| head -N`; refine-deck's validate fence keeps its `|| echo` recovery
line). Rationale: (a) alone fixes the message but a bootstrap that
exits 127 (fresh clone before pipx install) would still abort the
load; (b) alone leaves the cryptic `command not found` as the only
signal. A file-existence test was preferred over the
`sh ... 2>/dev/null || goc ...` chaining sketched at filing time
because chaining re-runs the command via bare `goc` whenever the
bootstrap-routed run exits non-zero for a real reason (e.g. `goc
validate` finding rot), producing duplicate/confusing output.

Two contracts reconciled along the way:

- `test_install.py`'s "Claude skills stay direct" test banned ANY
  `_goc-bootstrap.sh` mention in Claude skills (plugin bash-policy: no
  executing scripts from a plugin cache dir). The fences reference only
  the cwd-relative vendored copy behind `[ -f ]` — never a plugin-cache
  path — so the test now pins that refined invariant
  (`plugins/cache` banned; every bootstrap mention must be the
  `.claude/skills/` form).
- Hot-path body caps (`test_skill_body_size.py`, 10k) forced the
  shorter `b=...` variable form plus two one-sentence rationale trims
  in audit-deck/refine-deck (9941 / 9997 bytes after).

The OpenClaw porter gained an unwrap step (`BOOTSTRAP_ROUTED_RE`) that
restores the bare `goc <args>` command in ported skills, since OpenClaw
exposes goc as a registered tool, not a shell binary.

## 2026-07-15 — Empirical verification (this repo, bare goc off PATH)

Executed every `!` fence from the regenerated
`.claude/skills/refine-deck/SKILL.md` from the repo root via
`/bin/bash -c` — exactly what the Claude Code loader does; the load
aborts iff a fence exits non-zero. All four exit 0 with real output
(bootstrap routed to `uv run goc`):

```
fence 1: exit=0 first-line='<!-- .game-of-cards/hooks/refine-deck.md'
fence 2: exit=0 first-line='OK  active-card-banner-ignores-worker-filter'
fence 3: exit=0 first-line='ACTIVE: 6 claimed cards outside this open queue: ...'
fence 4: exit=0 first-line='['
```

Contrast with the filing-time failure: the same fence set previously
died at load with `Shell command failed for pattern "!\`goc --tag
unverified -v\`": goc: command not found`. Full suite: 718 tests OK
(including new `tests/test_skill_preamble_blocks.py`, which also runs
every fence in a goc-less temp dir with and without the bootstrap and
asserts exit 0); `sync_plugin_assets.py --check`,
`port_skills_to_openclaw.py --check`, and `goc validate` clean.

## 2026-07-15T00:00:00Z — Closure

- **What changed**: 15 `!` fences across `goc/templates/skills/{audit-deck,next-card,pull-card,refine-deck,retrospective,standup}/SKILL.md` — routed through the vendored bootstrap with bare-`goc` fallback and abort guard; `scripts/port_skills_to_openclaw.py` — unwrap step for ported skills; `tests/test_skill_preamble_blocks.py` — new regression guard; `tests/test_install.py` — refined plugin-policy invariant.
- **Verification**: all 4 regenerated refine-deck fences exit 0 from repo root (bare goc off PATH); capped bodies at 9941 / 9997 bytes (≤10000).
- **Audit**: PASS — no rubric configured; mechanical fix (restores the closed bootstrap-error-when-cli-not-on-path card's "clean install hint instead of cryptic shell error" guarantee at skill-load time).
- **Project impact**: six shipped skills become loadable on every host without `goc` on PATH (dogfood repo, vendored fresh clones); plugin-mode loads unchanged.
- **Tests**: 718 passed / 0 failed.

## Closure verification (2026-07-15T01:05:01Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — all 1 closed
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-07-15 — Closure' present
