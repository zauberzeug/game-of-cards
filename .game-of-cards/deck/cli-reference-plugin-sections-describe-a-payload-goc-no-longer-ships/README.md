---
title: cli-reference-plugin-sections-describe-a-payload-goc-no-longer-ships
summary: "FIXED. The plugin sections of `goc.md` described the pre-0.0.6 payload on seven counts: skills/hooks as symlinks into `goc/templates/`, 11 Claude skills, 13 OpenClaw skills with `kickoff` omitted, two hooks instead of three, a mandatory \"install the goc CLI first\" prerequisite, and an unguarded `_goc-bootstrap.sh` injection awaiting a `${CLAUDE_SKILL_DIR}` rewrite. The symlink claim was the costly one — it told contributors that editing `claude-plugin/skills/` edits the template. All seven rewritten; six derive-from-the-tree guards added to `tests/test_guidance_accuracy.py`."
status: done
stage: null
contribution: high
created: "2026-07-26T07:34:46Z"
closed_at: "2026-07-26T07:44:39Z"
human_gate: none
advances: []
advanced_by: []
tags: [documentation, infra]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero — all seven claims agree with the tree.
  - [x] TDD: `tests/test_guidance_accuracy.py` gains a plugin-reference accuracy
    class that DERIVES both skill counts from the live directories (so the
    numbers cannot rot again) and fails on the symlink claim, the
    prior-CLI-install prerequisite, and the `${CLAUDE_SKILL_DIR}` promise.
    Verified non-vacuous: all six guards fail against the pre-fix `goc.md`.
  - [x] MECHANICAL: `goc.md`'s symlink sentence replaced with the real-file
    byte-mirror contract plus the "edit the template, not the mirror" rule.
  - [x] MECHANICAL: Claude `### Prerequisites` rewritten to Python 3.10+ only,
    and the resolved `### Known limitation: dynamic skill content` section
    removed.
  - [x] MECHANICAL: both skill counts corrected; the "kickoff is deferred" and
    "then independently maintained" parentheticals replaced with the re-port +
    `--check` drift-guard model.
  - [x] MECHANICAL: `uv run python -m unittest discover -s tests` passes and
    `uv run goc validate` is clean.
worker: {who: "claude[bot]", where: main}
---

# `goc.md`'s plugin sections describe a payload GoC no longer ships

The command-level reference (`goc.md`) documents the Claude Code, Codex and
OpenClaw plugin payloads. Its Claude section was written when the payload was
symlinks into `goc/templates/` and shelled to a separately-installed `goc`
binary; its OpenClaw section was written before the port grew past 13 skills.
Neither was revisited when those facts changed. **Seven** distinct claims
contradicted both `AGENTS.md` and the tree they describe.

**FIXED** — all seven claims rewritten in `goc.md`; six derive-from-the-tree
guards added to `tests/test_guidance_accuracy.py`. See `## Fix applied`.

## Location

`goc.md` — `## Claude Code plugin` and `## OpenClaw plugin`.

## What was broken

Every `goc.md:NNN` citation below is a **pre-fix** line number (the file as of
`aa3905c5`); the rewrite shifted them.

**1. Payload assets are called symlinks (`goc.md:93`).**

> Skills and hook scripts are **symlinks** into `goc/templates/`, so the plugin
> and the repo-local harness always share the same source. No third copy exists.

`AGENTS.md:264` says the exact opposite, and says why:

> Because Claude Code's marketplace install only extracts the
> `source: ./claude-plugin` subtree, those assets must be **real files** (not
> symlinks pointing outside the subtree, which silently disappear on consumer
> install). They are byte-for-byte copies of the source-of-truth files

`1df38953 fix: ship plugin skills + hooks as real files for marketplace install`
(2026-05-07) flipped the two hook scripts from mode `120000` to `100644`;
`git log --diff-filter=T -- claude-plugin/` shows that as the only type change.
There are zero symlinks under `claude-plugin/skills/` or `claude-plugin/hooks/`
today.

**2. Claude skill count is 11 (`goc.md:89`).**

> - **11 GoC skills** (same as `goc install --agents claude`) — auto-discoverable
>   by Claude Code when the plugin is loaded.

`claude-plugin/skills/` holds 16 directories. (The parenthetical is still
correct — a vendored `goc install --agents claude` writes the same 16.)

**3–4. OpenClaw ships 13 skills and defers `kickoff` (`goc.md:215`).**

> - **13 GoC skills** as workspace-tier `SKILL.md` directories that OpenClaw
>   auto-discovers, ported from `goc/templates/skills/` once via
>   `scripts/port_skills_to_openclaw.py` and then independently maintained (the
>   `kickoff` skill is deferred to host-specific kickoff complements).

`openclaw-plugin/skills/` holds 16 directories and `openclaw-plugin/skills/kickoff/`
is one of them — `b30853e6` (2026-05-09) split the Claude-specific UX out of the
generic `kickoff` skill and ported both. `openclaw-plugin/openclaw.plugin.json`
already says "16 deck skills" and lists 16 entries in its `skills` array, so
`goc.md` is the lone outlier. The parenthetical also mis-states the porting
model as "then independently maintained": `AGENTS.md:370` describes a
deterministic re-port with a `--check` drift guard enforced by
`tests/test_plugin_mirror_parity.py`.

**5. A prior `goc` CLI install is a prerequisite (`goc.md:95–103`).**

> ### Prerequisites
>
> The plugin shells to the `goc` CLI; install it first:
>
> ```bash
> uv tool install game-of-cards   # or: pipx install game-of-cards
> ```

`AGENTS.md:389` — "Plugin runs goc from a vendored engine — Python 3.10+ is the
only host prerequisite" — and `claude-plugin/bin/goc` proves it:

```bash
exec env PYTHONPATH="${PLUGIN_ROOT}:${PYTHONPATH:-}" "$PYTHON" -m goc.cli "$@"
```

`claude-plugin/goc/engine.py` is vendored in the payload. `26bfce00 feat: bundle
goc engine inside Claude Code plugin payload` (2026-05-08) closed
[bundle-goc-engine-inside-plugin-payload](../bundle-goc-engine-inside-plugin-payload/);
the OpenClaw section absorbed the correction ("The only host prerequisite is
`python3` (3.10+) on PATH", `goc.md:222`) but the Claude section did not.

**6. The bootstrap injection is unguarded and awaits a `${CLAUDE_SKILL_DIR}` fix
(`goc.md:156–164`).**

> Skills use `` !`.claude/skills/_goc-bootstrap.sh` `` inline shell injections for
> dynamic context (queue listings, card details). When used via the plugin without
> a repo-local harness, that path does not exist and the injection produces an
> error message instead of card data.
> […]
> A future release will fix the bootstrap path to use `${CLAUDE_SKILL_DIR}` so the
> plugin is fully self-contained.

Both halves are stale. Every one of the 15 bootstrap fences across
`goc/templates/skills/` already carries the `[ -f ]` guard with a bare-`goc`
fallback, e.g. `goc/templates/skills/pull-card/SKILL.md:30`:

```
!`b=.claude/skills/_goc-bootstrap.sh; if [ -f $b ]; then sh $b --ready -v; else goc --ready -v; fi 2>&1 | head -22`
```

`tests/test_skill_preamble_blocks.py` pins that contract and states the resolved
design — "falling back to bare `goc` for plugin-mode loads where the plugin's
`bin/` is on PATH". The promised `${CLAUDE_SKILL_DIR}` rewrite was never the fix
taken: the string appears nowhere in the repo outside this `goc.md` paragraph.
The manual workaround the section prescribes ("Copy `_goc-bootstrap.sh` from the
plugin's skills to `.claude/skills/_goc-bootstrap.sh`") is not even performable —
`claude-plugin/skills/_goc-bootstrap.sh` does not exist, because the bootstrap is
sourced from `goc/templates/bootstrap/`, not `goc/templates/skills/`
(`AGENTS.md:251`).

**7. The provides list names two hooks; the payload registers three
(`goc.md:90–91`, pre-fix).**

Surfaced while editing the section. `claude-plugin/hooks/hooks.json` registers
`SessionStart`, `UserPromptSubmit` **and** `Stop` (→
`hooks/pattern_generalization_check.py`), but the "What the plugin provides"
list stopped at the first two — so the pattern-generalization self-assessment,
one of the three behaviours a consumer actually gets, was undocumented on this
surface.

## Empirical evidence

`uv run python .game-of-cards/deck/cli-reference-plugin-sections-describe-a-payload-goc-no-longer-ships/reproduce.py`:

```
[FAIL] claim 1 — plugin payload assets are symlinks
       goc.md asserts symlinks: True; actual symlinks under claude-plugin/{skills,hooks}: 0 []
[FAIL] claim 2 — Claude plugin skill count
       goc.md claims 11; claude-plugin/skills/ has 16
[FAIL] claim 3 — OpenClaw plugin skill count
       goc.md claims 13; openclaw-plugin/skills/ has 16
[FAIL] claim 4 — OpenClaw port defers the kickoff skill
       goc.md says kickoff is deferred: True; openclaw-plugin/skills/kickoff exists: True
[FAIL] claim 5 — Claude plugin requires a separate goc CLI install
       goc.md demands a prior CLI install: True; bin/goc runs the bundled engine: True; claude-plugin/goc/engine.py vendored: True
[FAIL] claim 6 — bootstrap injection is unguarded, awaiting a CLAUDE_SKILL_DIR fix
       goc.md promises a CLAUDE_SKILL_DIR rewrite: True; CLAUDE_SKILL_DIR used in any shipped skill: False; bootstrap fences: 15, unguarded: 0

6 stale claim(s) in goc.md: [...]
```

Exit code 1. (Claim 7 was added to `reproduce.py` after the rewrite, so it does
not appear in the pre-fix run above; the regression guard below covers it and
fails on the pre-fix text — see `## Fix applied`.)

**After the fix**, the same command prints `[ok]` for all seven and exits 0:

```
[ok] claim 1 — plugin payload assets are symlinks
       goc.md asserts symlinks: False; actual symlinks under claude-plugin/{skills,hooks}: 0 []
[ok] claim 2 — Claude plugin skill count
       goc.md claims 16; claude-plugin/skills/ has 16
[ok] claim 3 — OpenClaw plugin skill count
       goc.md claims 16; openclaw-plugin/skills/ has 16
[ok] claim 4 — OpenClaw port defers the kickoff skill
       goc.md says kickoff is deferred: False; openclaw-plugin/skills/kickoff exists: True
[ok] claim 5 — Claude plugin requires a separate goc CLI install
       goc.md demands a prior CLI install: False; bin/goc runs the bundled engine: True; claude-plugin/goc/engine.py vendored: True
[ok] claim 6 — bootstrap injection is unguarded, awaiting a CLAUDE_SKILL_DIR fix
       goc.md promises a CLAUDE_SKILL_DIR rewrite: False; CLAUDE_SKILL_DIR used in any shipped skill: False; bootstrap fences: 15, unguarded: 0
[ok] claim 7 — Claude plugin provides list names every registered hook
       hooks.json registers ['SessionStart', 'Stop', 'UserPromptSubmit']; not named in the provides list: []

goc.md plugin sections agree with the shipped payload.
```

## Why it matters

`goc.md` is the reference a contributor reaches for before touching the plugin
payloads — it is linked from `README.md` and shipped on the website. Each stale
claim has a distinct cost:

- **The symlink claim actively misdirects edits.** A contributor who believes
  `claude-plugin/skills/deck/SKILL.md` is a symlink into `goc/templates/` will
  edit the mirror and expect the template to change. It does not; the next
  `pre-commit` run silently overwrites the edit from the template, and the work
  is lost with no error. The whole reason `AGENTS.md` shouts **"Do not edit
  `claude-plugin/` or `codex-plugin/` directly"** is that this file says the
  opposite. `.gitattributes` marking those trees `linguist-generated=true`
  is further evidence the symlink model is gone.
- **The prerequisite claim costs consumers an install they don't need** and
  contradicts the plugin's own manifest description ("Bundles the goc CLI;
  requires Python 3.10+ on host PATH") plus `claude-plugin/README.md`.
- **The "known limitation" section sends readers to a workaround that cannot be
  followed** (the file it says to copy is not in the plugin payload) for a
  problem that no longer exists.
- **Both skill counts understate the payload** — a reader auditing whether the
  plugin shipped everything gets the wrong floor.

This is not the missing-guard family tracked by
[single-source-pattern-check-reminder-across-host-ports](../single-source-pattern-check-reminder-across-host-ports/)
— `goc.md` is a single authored doc surface with no mirror, so it is a
straight in-place correction, not a single-sourcing problem.

## Fix applied

Every claim rewritten in `goc.md` to the state `AGENTS.md` already documents:

1. **Symlink sentence → real-file/byte-mirror contract**, with the reason
   (marketplace install extracts only the `./claude-plugin` subtree) and a bolded
   **"Edit the template, never the mirror."** paragraph naming the
   `sync-plugin-assets` pre-commit hook and the CI `--check` tripwire.
2. **Claude skill count 11 → 16.**
3. **OpenClaw skill count 13 → 16**; the "`kickoff` skill is deferred"
   parenthetical replaced with the real exclusion (`claude-kickoff` and
   `codex-kickoff`, verified by set-differencing the template and port dirs), and
   "then independently maintained" replaced with the deterministic re-port +
   `--check` drift-guard model.
4. **Claude `### Prerequisites` rewritten** to "Python 3.10+ on PATH — nothing
   else", explaining `bin/goc`, the `PYTHONPATH` hand-off, and Claude Code's
   `bin/` PATH-prepend. It also records why no minimum-version check is needed
   (engine and skills ship in one payload) and that a separate install is
   optional-but-required-for-`--local-skills`.
5. **`### Known limitation: dynamic skill content` deleted** — resolved. The one
   durable fact moved into Prerequisites: fences route through the bootstrap
   wrapper when present and fall back to bare `goc` (the plugin's `bin/goc`)
   otherwise, so live queue views *do* render in plugin mode. Cites
   `tests/test_skill_preamble_blocks.py` for the exit-zero contract.
6. **`Stop` hook and the bundled engine added to the provides list** (claim 7).

Regression guard: `GocMdPluginReferenceAccuracyTest` in
`tests/test_guidance_accuracy.py` — the existing home for doc-claim tripwires.
Six tests, each **deriving** truth from the tree rather than restating it, so the
numbers cannot rot again (the same technique
`test_all_engine_verbs_listed_in_architecture_section` uses to derive verbs from
the argparse parser):

| Test | Derives from |
|---|---|
| `test_no_doc_calls_payload_assets_symlinks` | live `is_symlink()` walk of `claude-plugin/{skills,hooks}` |
| `test_claude_skill_count_matches_payload` | `claude-plugin/skills/` dir count |
| `test_openclaw_skill_count_matches_payload` | `openclaw-plugin/skills/` dir count + `kickoff/` presence |
| `test_claude_prerequisites_do_not_demand_a_separate_cli_install` | `bin/goc` contents + vendored `goc/engine.py` |
| `test_no_doc_promises_an_unimplemented_skill_dir_bootstrap_rewrite` | `CLAUDE_SKILL_DIR` usage across shipped `SKILL.md` files |
| `test_claude_provides_list_names_every_registered_hook` | `claude-plugin/hooks/hooks.json` event keys |

Verified non-vacuous: pointing the module's `GOC_MD` at the pre-fix `goc.md`
(`git show aa3905c5:goc.md`) fails all six; against the fixed file all six pass.

`uv run python -m unittest discover -s tests` → 771 tests, OK.
`uv run goc validate` → exit 0. `scripts/sync_plugin_assets.py --check` and
`scripts/port_skills_to_openclaw.py --check` → both clean (no template or mirror
was touched; `goc.md` is a root doc with no mirror).

Checked for the same claims on sibling doc surfaces (`README.md`, `ABOUT.md`,
`CONTRIBUTING.md`, `PERSONAS.md`, `DECK_LOCATION.md`, `site/`, and the three
plugin `README.md`s): none repeat them, so no sibling card is warranted. The
website serves `goc.md` itself at `/goc/`, so the fix propagates on the next
Pages build.
