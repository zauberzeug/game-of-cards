---
title: goc-upgrade-cannot-repair-a-damaged-install-at-the-same-version
summary: "goc upgrade returns 'already at goc X — nothing to do' whenever .goc-version matches the installed engine, so a repo whose vendored skills, .game-of-cards stubs, pre-commit stanza, or AGENTS.md marker block were deleted or corrupted is never re-synced. goc install in that repo exits 1 telling the user to run `goc upgrade` to re-sync templates, so goc's own printed remedy is a no-op. The short-circuit is a hand-maintained allowlist of pending_* signals and four repairs added since are not on it."
status: active
stage: null
contribution: high
created: "2026-08-31T01:19:28Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, api-contract, meta-fix]
definition_of_done: |
  - [ ] TDD: reproduce.py exits 0 — bare `goc upgrade` on a same-version repo
        restores the vendored skill dir, the absent `.game-of-cards/` stub, the
        absent `.pre-commit-config.yaml` stanza and the destroyed AGENTS.md
        marker block (it exits 1 today with 4/4 skipped)
  - [ ] TDD: the "already at goc X — nothing to do" no-op and its exact message
        are preserved for a pristine, already-current repo — no spurious writes,
        no spurious commit churn (carried over from the predecessor card's DoD)
  - [ ] TDD: the guard is derived from the upgrade write plan, not from a
        hand-listed `pending_*` allowlist — a test adds a synthetic pending write
        that no `pending_*` predicate names and asserts the short-circuit does not
        fire, so the next repair added to `upgrade()` cannot silently rejoin the
        skipped set
  - [ ] TDD: regression test asserts `goc upgrade --dry-run` and the real run
        agree on whether there is work (today the preview prints an 18-write plan
        where the real run prints "nothing to do")
  - [ ] TDD: `_plan_upgrade_writes` reports an absent `.pre-commit-config.yaml`
        as a pending append, closing the half of the pre-commit case the
        predecessor card's `_precommit_refresh_pending` does not cover
  - [ ] EMPIRICAL: `goc upgrade` on a repo with a *diverged* user-owned stub still
        preserves it (the fix must not reopen
        `goc-upgrade-overwrites-authored-game-of-cards-content-stubs-and-hooks`);
        verdict recorded in log.md either way
  - [ ] MECHANICAL: the closed instance card
        `goc-upgrade-same-version-short-circuit-skips-the-pre-commit-glob-migration`
        gets a forward pointer to this root card
  - [ ] PROCESS: full regression suite and `uv run goc validate` stay green;
        plugin mirrors re-synced
worker: {who: "claude[bot]", where: main}
---

# goc-upgrade-cannot-repair-a-damaged-install-at-the-same-version

## Location

- `goc/install.py:1802-1813` — `upgrade()`'s same-version short-circuit.
- `goc/install.py:1791-1800` — the three `pending_*` signals that are
  allowed to defeat it.
- `goc/install.py:1858`, `:1860`, `:1867`, `:1871` — the four re-sync
  steps that live *after* the `return` and have no `pending_*` signal.
- `goc/install.py:1590` — `install()`'s refusal that points the user at
  `goc upgrade`.

## What's broken

`upgrade()` decides "there is nothing to do" from the version sentinel
plus a hand-maintained allowlist of pending work:

```python
# goc/install.py:1791
pending_cleanup = needs_vendored_cleanup and not dry_run
pending_briefing_migration = bool(legacy_briefings_to_strip) and not dry_run
pending_precommit_refresh = (
    _precommit_refresh_pending(target / ".pre-commit-config.yaml") and not dry_run
)

if (
    existing == __version__
    and not dry_run
    and not agents_explicit
    and not pending_cleanup
    and not keep_local_skills
    and not pending_briefing_migration
    and not pending_precommit_refresh
    and briefing_target is None
):
    print(f"already at goc {__version__} — nothing to do.")
    return
```

Every re-sync step is below that `return`, and only three of them have a
signal on the allowlist. The four that do not:

| Skipped step | What it repairs | Signal on the allowlist? |
|---|---|---|
| `_sync_agent_harness` (`:1858`) | vendored `.claude/skills/`, `.claude/hooks/`, `.claude/settings.json` entries | no |
| `_sync_game_of_cards_config` (`:1860`) | absent `.game-of-cards/` content stubs and `hooks/*.md` | no |
| `_sync_methodology_blocks` (`:1867`) | the goc-owned `AGENTS.md` / `CLAUDE.md` marker block | no |
| `_append_precommit_hook` (`:1871`) | an **absent** `.pre-commit-config.yaml` stanza | only the *drifted-stanza* case (`_precommit_refresh_pending` compares an existing stanza; it returns `False` when there is none) |

The guard therefore reports "nothing to do" for work that is plainly
pending. Three shipped documents say that work happens:

- `goc/templates/game_of_cards/README.md:66` — installed into every
  consuming repo as `.game-of-cards/README.md`:

  > | **goc-owned (managed elsewhere)** | the marker-bounded block in
  > `AGENTS.md` / `CLAUDE.md` | regenerated wholesale on every upgrade
  > (the contract is "do not edit between the markers") |

  It is not regenerated on *this* upgrade, and the sentence is the only
  thing that makes "do not edit between the markers" a safe contract —
  it is what promises the block comes back.

- `goc/templates/game_of_cards/README.md:64` — the user-owned row:
  `absent → scaffold blank stub`. An absent stub is not scaffolded.

- `goc.md:72-78`, `## Upgrade an install`: "After upgrading the
  machine-wide `goc` command, refresh generated files in a repo:
  `goc upgrade`". The engine's own help string agrees
  (`goc/cli.py:85`, `goc/install.py:1720`): "Re-sync skill templates,
  AGENTS.md, and CLAUDE.md sections from the installed package version."

And goc's own CLI closes the loop into a dead end — `install()` refuses
and names `upgrade` as the remedy (`goc/install.py:1590`):

```
already installed (.game-of-cards/deck/.goc-version → 0.0.27.post1.dev355)
Run `goc upgrade` to re-sync templates.
```

There is no `--force` / `--refresh` flag. The only way to make the
re-sync run is to pass `--agents <harness>`, `--briefing-target ...` or
`--keep-local-skills` — each documented as something else entirely
(`--agents` is "for scripted installs, pass the harness explicitly",
`goc.md:52`). Nothing tells a user that an unrelated flag is the repair
path, and nothing in `goc --help` hints that the bare form is a no-op.

## Empirical evidence

`uv run python .game-of-cards/deck/goc-upgrade-cannot-repair-a-damaged-install-at-the-same-version/reproduce.py`

```
[setup] goc install --agents claude --local-skills -> exit 0

[damage] deleted one vendored skill dir, one project-state stub and
         .pre-commit-config.yaml; blanked the AGENTS.md marker block
  after damage:
    BROKEN  vendored skill dir .claude/skills/deck/
    BROKEN  project-state stub .game-of-cards/canonical-tags.md
    BROKEN  pre-commit stanza .pre-commit-config.yaml
    BROKEN  AGENTS.md goc-owned marker block

[step 1] goc install       -> exit 1
           already installed (.game-of-cards/deck/.goc-version → 0.0.27.post1.dev355)
           Run `goc upgrade` to re-sync templates.

[step 2] goc upgrade       -> exit 0
           already at goc 0.0.27.post1.dev355 — nothing to do.
  after bare upgrade:
    BROKEN  vendored skill dir .claude/skills/deck/
    BROKEN  project-state stub .game-of-cards/canonical-tags.md
    BROKEN  pre-commit stanza .pre-commit-config.yaml
    BROKEN  AGENTS.md goc-owned marker block

[step 3] goc upgrade --agents claude -> exit 0
  after upgrade --agents claude:
    OK      vendored skill dir .claude/skills/deck/
    OK      project-state stub .game-of-cards/canonical-tags.md
    OK      pre-commit stanza .pre-commit-config.yaml
    OK      AGENTS.md goc-owned marker block

repairs skipped by bare `goc upgrade`: 4/4
repairs performed once the guard is defeated: 4/4

DEFECT PRESENT: bare `goc upgrade` exits 0 with 'nothing to do' while 4 repair(s) it is documented to perform stay undone; the same run with an unrelated `--agents` flag performs all of them.
```

Step 3 is the control: the work is available and cheap, the guard just
refuses to look. `reproduce.py` exits 1 today.

## Why it matters — reachability

The damaged state is reached without anyone doing anything exotic:

1. **Editing between the markers.** The contract line exists because
   people do it; the same line promises `goc upgrade` puts the block
   back. On any repo whose `.goc-version` already matches, it does not.
   A merge conflict resolved by keeping "ours" produces the same shape.
2. **Plugin-delivered engines make same-version the normal case.** The
   Claude/Codex/OpenClaw payloads bundle the engine, so a consumer's
   `goc` and their `.goc-version` agree for the entire life of a release
   — every `goc upgrade` between releases takes the short-circuit. There
   is no window in which the repair runs.
3. **A partially-applied install — no user error required.**
   `install()` writes `.goc-version` *fourth of nine* steps
   (`goc/install.py:1610`), ahead of `_sync_game_of_cards_config`
   (`:1612`), `_write_skills_source` (`:1616`),
   `_sync_methodology_blocks` (`:1619`) and `_append_precommit_hook`
   (`:1621`). Interrupt the install any time after the sentinel lands
   (Ctrl-C, a full disk, a killed CI step, a crash in one of the later
   syncs) and the repo reports "current" while missing the stubs, the
   marker block and the pre-commit stanza. Re-running `goc install`
   refuses and points at `goc upgrade`, which no-ops. `goc validate`
   does not check any of the four surfaces either, so nothing reports
   the gap — the repo is permanently half-installed by first-party
   commands alone.
4. **A tidy-up commit.** Deleting `.pre-commit-config.yaml` (or a skill
   dir that "looked generated") is a normal thing to try; the documented
   undo is `goc upgrade`.

The user-visible symptom in cases 1 and 3 is the worst kind: an agent
session in a repo whose `AGENTS.md` GoC block is gone silently stops
following the methodology, and the command whose whole job is to restore
it prints success.

## This is the family, not an instance

`goc-upgrade-same-version-short-circuit-skips-the-pre-commit-glob-migration`
(done, 2026-06-29) is the same defect at one call site: the guard
returned before `_append_precommit_hook`, so a stale glob was never
migrated. It was fixed by *adding a fourth term to the allowlist*
(`pending_precommit_refresh`) and its own body names the shape:

> The guard already carves out *specific* pending work that must run
> even at the same version (`pending_cleanup`,
> `pending_briefing_migration`), but a stale pre-commit glob is not one
> of those signals, so the migration is skipped.

That fix is per-site by construction: every repair added to `upgrade()`
must remember to register a `pending_*` predicate, and the register is
in a different part of the function from the work. Four have not
registered — including the *absent-stanza* half of the very file the
predecessor card was about. Filing a fifth instance card would repeat
the pattern, so this is filed as the meta-fix.

Same shape as this repo's other "X re-enumerates Y and keeps drifting"
roots — [dry-run-plan-reenumerates-executor-conditionals-and-keeps-drifting](../dry-run-plan-reenumerates-executor-conditionals-and-keeps-drifting/),
[frontmatter-emitter-quote-trigger-reenumerates-parser-shapes-and-keeps-drifting](../frontmatter-emitter-quote-trigger-reenumerates-parser-shapes-and-keeps-drifting/) —
and it is the mirror image of the first: there the *preview* re-lists
the executor's conditionals, here the *executor's own no-op guard*
re-lists its own steps.

Related, not duplicates:

- [goc-upgrade-same-version-short-circuit-skips-the-pre-commit-glob-migration](../goc-upgrade-same-version-short-circuit-skips-the-pre-commit-glob-migration/)
  (done) — instance one, fixed by extending the allowlist.
- [goc-upgrade-silently-downgrades-newer-install-without-guard-or-warning](../goc-upgrade-silently-downgrades-newer-install-without-guard-or-warning/)
  (open) — the *other* branch of the same version comparison; a fix here
  touches the same guard and should be reconciled with it.
- [goc-upgrade-overwrites-authored-game-of-cards-content-stubs-and-hooks](../goc-upgrade-overwrites-authored-game-of-cards-content-stubs-and-hooks/)
  — the opposite failure (overwriting authored content). The fix below
  must not reopen it: `_sync_game_of_cards_config` already preserves
  diverged user-owned files, so making it *run* is safe.
- [dry-run-plan-promises-full-install-that-the-real-run-refuses-as-already-installed](../dry-run-plan-promises-full-install-that-the-real-run-refuses-as-already-installed/)
  (done) — the install-side preview/executor split.

## Secondary observation (same guard)

`and not dry_run` (`goc/install.py:1804`) means `goc upgrade --dry-run`
*never* takes the short-circuit: on a pristine, already-current repo it
prints `goc upgrade would sync X → X` plus an 18-write plan, while the
real run prints `already at goc X — nothing to do` and writes nothing.
That is a preview/executor divergence of the kind
[dry-run-plan-reenumerates-executor-conditionals-and-keeps-drifting](../dry-run-plan-reenumerates-executor-conditionals-and-keeps-drifting/)
catalogues. A plan-derived guard (below) collapses both problems into
one: the preview and the no-op decision would read the same computation.

## Decision (rubric-derived)

Filed at `human_gate: none`. The mechanism is not a taste call — this
repo has already settled the same question twice, in the same direction,
and the fix follows from those precedents rather than needing a fresh
pick:

- **Principle: derive, do not re-enumerate.** `frontmatter-emitter-...-keeps-drifting`
  replaced a hand-listed character set with one derived from the spec;
  `repair-edges-dry-run-overstates-fixable-edges-that-apply-refuses`
  replaced two hand-mirrored passes with one shared classifier. AGENTS.md
  states the rule for the mirrors ("The hook list is derived from
  `templates/hooks/*.py` at install time … The event mapping is not
  derived — it stays explicit") and the repo treats every *non*-derived
  registry as a known liability.
- **Applied here:** `upgrade()` already computes a full write plan for
  `--dry-run` (`_plan_upgrade_writes`, `goc/install.py:910`) whose
  ownership-aware actions distinguish `create` / `unchanged` /
  `preserved` / `sync`. That is exactly the "is anything pending?"
  question the allowlist is guessing at. Compute it unconditionally and
  short-circuit only when the plan contains no effecting action, with
  the existing `pending_*` signals folded in as extra terms for the
  non-write work (the cleanup prompt, the briefing strip).

So: **replace the version-equality allowlist with a plan-derived guard.**
The "already at goc X — nothing to do" message and its no-op stay for a
genuinely pristine repo (a hard requirement carried over from the
predecessor card's DoD); it just stops firing when there is real work.
A later reader who disagrees can still raise the gate and pick the
cheaper alternative — an explicit `goc upgrade --force` — but that one
only helps users who already know the install is damaged, which is the
case the symptom hides.

## Fix (do not apply here)

1. In `upgrade()` (`goc/install.py:1791-1813`), compute
   `_plan_upgrade_writes(...)` before the guard and derive a
   `plan_has_effect` predicate from it (any action that is not
   `unchanged` / `preserved`), plus a check that `_sync_methodology_blocks`
   would change the briefing file. Replace the three `pending_*` terms
   with `not plan_has_effect` **and** keep `pending_cleanup` /
   `pending_briefing_migration` for the non-write work the plan does not
   model.
2. Make `_plan_upgrade_writes` model `_append_precommit_hook`'s
   absent-stanza case, so a deleted `.pre-commit-config.yaml` shows up as
   `append` rather than being invisible to both the plan and the guard.
3. Drop `and not dry_run` from the guard once the plan drives it, so
   `--dry-run` and the real run report the same verdict on a pristine
   repo.
4. Regression tests: one per skipped surface (harness, stub, marker
   block, absent pre-commit stanza) asserting bare `goc upgrade` repairs
   it at the same version, plus the preserved no-op test for a pristine
   repo, plus a parity test that `--dry-run` and the real run agree on
   whether there is work.
