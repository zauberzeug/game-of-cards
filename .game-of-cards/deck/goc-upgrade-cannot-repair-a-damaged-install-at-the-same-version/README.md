---
title: goc-upgrade-cannot-repair-a-damaged-install-at-the-same-version
summary: "goc upgrade returned 'already at goc X — nothing to do' whenever .goc-version matched the installed engine, so a repo whose vendored skills, .game-of-cards stubs, pre-commit stanza, or AGENTS.md marker block were deleted was never re-synced — while goc install in that repo exited 1 naming `goc upgrade` as the remedy. The short-circuit was a hand-maintained allowlist of pending_* signals that four later repairs never joined. Fixed by deriving the verdict from the upgrade write plan, with each write's action supplied by its own executor in probe mode, so the preview and the real run agree and a new repair is covered the moment it is planned."
status: done
stage: null
contribution: high
created: "2026-08-31T01:19:28Z"
closed_at: "2026-09-01T04:52:07Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, api-contract, meta-fix]
definition_of_done: |
  - [x] TDD: reproduce.py exits 0 — bare `goc upgrade` on a same-version repo
        restores the vendored skill dir, the absent `.game-of-cards/` stub, the
        absent `.pre-commit-config.yaml` stanza and the destroyed AGENTS.md
        marker block (it exits 1 today with 4/4 skipped)
  - [x] TDD: the "already at goc X — nothing to do" no-op and its exact message
        are preserved for a pristine, already-current repo — no spurious writes,
        no spurious commit churn (carried over from the predecessor card's DoD)
  - [x] TDD: the guard is derived from the upgrade write plan, not from a
        hand-listed `pending_*` allowlist — a test adds a synthetic pending write
        that no `pending_*` predicate names and asserts the short-circuit does not
        fire, so the next repair added to `upgrade()` cannot silently rejoin the
        skipped set
  - [x] TDD: regression test asserts `goc upgrade --dry-run` and the real run
        agree on whether there is work (today the preview prints an 18-write plan
        where the real run prints "nothing to do")
  - [x] TDD: `_plan_upgrade_writes` reports an absent `.pre-commit-config.yaml`
        as a pending append, closing the half of the pre-commit case the
        predecessor card's `_precommit_refresh_pending` does not cover
  - [x] EMPIRICAL: `goc upgrade` on a repo with a *diverged* user-owned stub still
        preserves it (the fix must not reopen
        `goc-upgrade-overwrites-authored-game-of-cards-content-stubs-and-hooks`);
        verdict recorded in log.md either way
  - [x] MECHANICAL: the closed instance card
        `goc-upgrade-same-version-short-circuit-skips-the-pre-commit-glob-migration`
        gets a forward pointer to this root card
  - [x] PROCESS: full regression suite and `uv run goc validate` stay green;
        plugin mirrors re-synced
worker: {who: "claude[bot]", where: main}
---

# goc-upgrade-cannot-repair-a-damaged-install-at-the-same-version

## Location

Post-fix line numbers; the pre-fix code is quoted in the sections below.

- `goc/install.py:1965` — `upgrade()` computes `_plan_upgrade_writes` before
  deciding anything.
- `goc/install.py:1981` — `plan_has_effect`, the derived verdict that replaced
  the `pending_*` allowlist.
- `goc/install.py:1019` — `_upgrade_write_action`, which labels each planned
  write by asking its own executor.
- `goc/install.py:220` — `_commit_text`, the shared write-or-report primitive
  every text-editing executor now routes through.
- `goc/install.py:108` — `_NO_OP_ACTIONS`, the two actions that mean "touches
  nothing".
- `goc/install.py:1764` — `install()`'s refusal that names `goc upgrade` as the
  remedy. It is now a true remedy.

## What was broken

`upgrade()` decided "there is nothing to do" from the version sentinel plus a
hand-maintained allowlist of pending work:

```python
# goc/install.py:1791 (pre-fix)
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

Every re-sync step lived below that `return`, and only three of them had a
signal on the allowlist. The four that did not:

| Skipped step | What it repairs | Signal on the allowlist? |
|---|---|---|
| `_sync_agent_harness` | vendored `.claude/skills/`, `.claude/hooks/`, `.claude/settings.json` entries | no |
| `_sync_game_of_cards_config` | absent `.game-of-cards/` content stubs and `hooks/*.md` | no |
| `_sync_methodology_blocks` | the goc-owned `AGENTS.md` / `CLAUDE.md` marker block | no |
| `_append_precommit_hook` | an **absent** `.pre-commit-config.yaml` stanza | only the *drifted-stanza* case (`_precommit_refresh_pending` compared an existing stanza; it returned `False` when there was none) |

The guard therefore reported "nothing to do" for work that was plainly
pending. Three shipped documents say that work happens:

- `goc/templates/game_of_cards/README.md:66` — installed into every
  consuming repo as `.game-of-cards/README.md`:

  > | **goc-owned (managed elsewhere)** | the marker-bounded block in
  > `AGENTS.md` / `CLAUDE.md` | regenerated wholesale on every upgrade
  > (the contract is "do not edit between the markers") |

  It was not regenerated on *that* upgrade, and the sentence is the only
  thing that makes "do not edit between the markers" a safe contract —
  it is what promises the block comes back.

- `goc/templates/game_of_cards/README.md:64` — the user-owned row:
  `absent → scaffold blank stub`. An absent stub was not scaffolded.

- `goc.md:72-78`, `## Upgrade an install`: "After upgrading the
  machine-wide `goc` command, refresh generated files in a repo:
  `goc upgrade`". The engine's own help string agrees: "Re-sync skill
  templates, AGENTS.md, and CLAUDE.md sections from the installed package
  version."

And goc's own CLI closed the loop into a dead end — `install()` refuses and
names `upgrade` as the remedy:

```
already installed (.game-of-cards/deck/.goc-version → 0.0.27.post1.dev355)
Run `goc upgrade` to re-sync templates.
```

There was no `--force` / `--refresh` flag. The only way to make the re-sync run
was to pass `--agents <harness>`, `--briefing-target ...` or
`--keep-local-skills` — each documented as something else entirely (`--agents`
is "for scripted installs, pass the harness explicitly", `goc.md:52`). Nothing
told a user that an unrelated flag was the repair path, and nothing in
`goc --help` hinted that the bare form was a no-op.

## Empirical evidence

`uv run python .game-of-cards/deck/goc-upgrade-cannot-repair-a-damaged-install-at-the-same-version/reproduce.py`

Before the fix (exit 1):

```
[step 2] goc upgrade       -> exit 0
           already at goc 0.0.27.post1.dev355 — nothing to do.
  after bare upgrade:
    BROKEN  vendored skill dir .claude/skills/deck/
    BROKEN  project-state stub .game-of-cards/canonical-tags.md
    BROKEN  pre-commit stanza .pre-commit-config.yaml
    BROKEN  AGENTS.md goc-owned marker block

repairs skipped by bare `goc upgrade`: 4/4
repairs performed once the guard is defeated: 4/4

DEFECT PRESENT: bare `goc upgrade` exits 0 with 'nothing to do' while 4 repair(s) it is documented to perform stay undone; the same run with an unrelated `--agents` flag performs all of them.
```

Step 3 was the control: the work was available and cheap, the guard just
refused to look.

After the fix (exit 0):

```
[step 2] goc upgrade       -> exit 0
           goc upgrade complete for agents: claude — 0.0.27.post1.dev358 → 0.0.27.post1.dev358.
  after bare upgrade:
    OK      vendored skill dir .claude/skills/deck/
    OK      project-state stub .game-of-cards/canonical-tags.md
    OK      pre-commit stanza .pre-commit-config.yaml
    OK      AGENTS.md goc-owned marker block

repairs skipped by bare `goc upgrade`: 0/4
repairs performed once the guard is defeated: 4/4

DEFECT ABSENT: bare `goc upgrade` re-synced every damaged surface.
```

## Why it matters — reachability

The damaged state is reached without anyone doing anything exotic:

1. **Editing between the markers.** The contract line exists because
   people do it; the same line promises `goc upgrade` puts the block
   back. On any repo whose `.goc-version` already matched, it did not.
   A merge conflict resolved by keeping "ours" produces the same shape.
2. **Plugin-delivered engines make same-version the normal case.** The
   Claude/Codex/OpenClaw payloads bundle the engine, so a consumer's
   `goc` and their `.goc-version` agree for the entire life of a release
   — every `goc upgrade` between releases took the short-circuit. There
   was no window in which the repair ran.
3. **A partially-applied install — no user error required.**
   `install()` writes `.goc-version` *fourth of nine* steps, ahead of
   `_sync_game_of_cards_config`, `_write_skills_source`,
   `_sync_methodology_blocks` and `_append_precommit_hook`. Interrupt the
   install any time after the sentinel lands (Ctrl-C, a full disk, a killed
   CI step, a crash in one of the later syncs) and the repo reports
   "current" while missing the stubs, the marker block and the pre-commit
   stanza. Re-running `goc install` refuses and points at `goc upgrade`,
   which no-opped. `goc validate` does not check any of the four surfaces
   either, so nothing reported the gap — the repo was permanently
   half-installed by first-party commands alone.
4. **A tidy-up commit.** Deleting `.pre-commit-config.yaml` (or a skill
   dir that "looked generated") is a normal thing to try; the documented
   undo is `goc upgrade`.

The user-visible symptom in cases 1 and 3 was the worst kind: an agent
session in a repo whose `AGENTS.md` GoC block is gone silently stops
following the methodology, and the command whose whole job is to restore
it printed success.

## This is the family, not an instance

`goc-upgrade-same-version-short-circuit-skips-the-pre-commit-glob-migration`
(done, 2026-06-29) is the same defect at one call site: the guard
returned before `_append_precommit_hook`, so a stale glob was never
migrated. It was fixed by *adding a fourth term to the allowlist*
(`pending_precommit_refresh`) and its own body named the shape:

> The guard already carves out *specific* pending work that must run
> even at the same version (`pending_cleanup`,
> `pending_briefing_migration`), but a stale pre-commit glob is not one
> of those signals, so the migration is skipped.

That fix was per-site by construction: every repair added to `upgrade()` had to
remember to register a `pending_*` predicate, and the register lived in a
different part of the function from the work. Four had not — including the
*absent-stanza* half of the very file the predecessor card was about. Filing a
fifth instance card would have repeated the pattern, so this was filed as the
meta-fix.

Same shape as this repo's other "X re-enumerates Y and keeps drifting"
roots — [dry-run-plan-reenumerates-executor-conditionals-and-keeps-drifting](../dry-run-plan-reenumerates-executor-conditionals-and-keeps-drifting/),
[frontmatter-emitter-quote-trigger-reenumerates-parser-shapes-and-keeps-drifting](../frontmatter-emitter-quote-trigger-reenumerates-parser-shapes-and-keeps-drifting/) —
and it is the mirror image of the first: there the *preview* re-lists
the executor's conditionals, here the *executor's own no-op guard*
re-listed its own steps.

Related, not duplicates:

- [goc-upgrade-same-version-short-circuit-skips-the-pre-commit-glob-migration](../goc-upgrade-same-version-short-circuit-skips-the-pre-commit-glob-migration/)
  (done) — instance one, fixed by extending the allowlist. Amended with a
  forward pointer here; the allowlist term it added is now retired and its
  behavioral contract is carried by the plan-derived guard.
- [goc-upgrade-silently-downgrades-newer-install-without-guard-or-warning](../goc-upgrade-silently-downgrades-newer-install-without-guard-or-warning/)
  (open) — the *other* branch of the same version comparison. Still open and
  untouched: this fix only changed what happens when the versions are equal.
- [goc-upgrade-overwrites-authored-game-of-cards-content-stubs-and-hooks](../goc-upgrade-overwrites-authored-game-of-cards-content-stubs-and-hooks/)
  — the opposite failure (overwriting authored content). Verified not
  reopened: `_sync_game_of_cards_config` already preserves diverged
  user-owned files, so making it *run* is safe, and a regression test pins it.
- [dry-run-plan-promises-full-install-that-the-real-run-refuses-as-already-installed](../dry-run-plan-promises-full-install-that-the-real-run-refuses-as-already-installed/)
  (done) — the install-side preview/executor split.

## Secondary observation (resolved with the same change)

`and not dry_run` in the pre-fix guard meant `goc upgrade --dry-run` *never*
took the short-circuit: on a pristine, already-current repo it printed
`goc upgrade would sync X → X` plus an 18-write plan, while the real run
printed `already at goc X — nothing to do` and wrote nothing. Because the
preview and the no-op decision now read the same computation, that term is
gone and both report the same verdict.

## Decision (rubric-derived)

Filed at `human_gate: none`. The mechanism was not a taste call — this
repo had already settled the same question twice, in the same direction,
and the fix followed from those precedents rather than needing a fresh
pick:

- **Principle: derive, do not re-enumerate.** `frontmatter-emitter-...-keeps-drifting`
  replaced a hand-listed character set with one derived from the spec;
  `repair-edges-dry-run-overstates-fixable-edges-that-apply-refuses`
  replaced two hand-mirrored passes with one shared classifier. AGENTS.md
  states the rule for the mirrors ("The hook list is derived from
  `templates/hooks/*.py` at install time … The event mapping is not
  derived — it stays explicit") and the repo treats every *non*-derived
  registry as a known liability.
- **Applied here:** `upgrade()` already computed a full write plan for
  `--dry-run` (`_plan_upgrade_writes`) whose ownership-aware actions
  distinguish `create` / `unchanged` / `preserved`. That is exactly the
  "is anything pending?" question the allowlist was guessing at.

So: **replace the version-equality allowlist with a plan-derived guard.**

## Fix (applied)

1. **Every write in the plan is labelled by its own executor.** `PlannedWrite`
   (`goc/install.py:90`) gained a `kind` (which executor operation produces the
   path), an optional template `source`, and an `executable` flag.
   `_upgrade_write_action` (`:1019`) dispatches on `kind` and either compares
   the bytes the copy would write or calls the executor with `probe=True`.
   The ownership-aware `create` / `unchanged` / `preserved` labelling that used
   to apply only to `.game-of-cards/` now covers the whole plan, so a healthy
   repo's plan is all no-ops and a damaged one's is not.
2. **`probe=True` on every text-editing executor.** `_append_marker_block`,
   `_sync_claude_import`, `_strip_claude_import`, `_append_precommit_hook`,
   `_merge_claude_settings` and `_write_skills_source` now return whether they
   change the file and accept `probe=True` to answer without writing (no file,
   no `.bak`, no warning). They share one primitive, `_commit_text` (`:220`),
   so the answer and the write cannot diverge. `_write_codex_skill` was split
   so `_codex_skill_text` (`:1324`) renders what the writer would produce and
   a vendored Codex skill is compared against *that*, not the untransformed
   template.
3. **The guard reads the plan.** `plan_has_effect` (`:1981`) is
   `any(action not in _NO_OP_ACTIONS)`. `pending_precommit_refresh` and its
   `_precommit_refresh_pending` predicate are deleted — the plan's pre-commit
   entry now covers both the drifted stanza the predicate handled *and* the
   absent config it did not. Two terms survive for work the plan does not
   model (the interactive vendored-cleanup prompt, the legacy-briefing strip)
   plus a probe of `_write_skills_source` for the `skills_source` pin; none of
   them restate an executor.
4. **`and not dry_run` is gone**, so `--dry-run` and the real run print the
   same verdict, and the dry-run preview reports pending cleanup/migration it
   previously suppressed.
5. **`_plan_upgrade_writes` takes the resolved `deck_dir`**, so a legacy
   `deck/` install's version sentinel is checked where it actually lives
   rather than at the canonical path it does not occupy.
6. `_print_plan` appends `(N effecting)` when a plan contains no-ops, so a
   49-line upgrade preview says at a glance that 3 writes land.

## Regression contract

`tests/test_upgrade_repairs_damaged_install_at_same_version.py` (12 tests):

- one test per repair the allowlist skipped — vendored skill dir, absent
  project-state stub, destroyed marker block, absent pre-commit stanza;
- a diverged user-owned stub survives a run that repairs its neighbour;
- the pristine repo prints the exact `already at goc X — nothing to do.`
  message and a byte-and-mtime snapshot of the whole tree is unchanged;
- a repair run converges — the second bare upgrade is a no-op again;
- a **synthetic** pending write injected into the plan (no `pending_*`
  predicate names it) defeats the short-circuit, which is the forward
  guarantee for the next repair added to `upgrade()`;
- `--dry-run` and the real run agree on a pristine repo (identical output,
  no writes) and on a damaged one;
- the plan labels an absent `.pre-commit-config.yaml` `append` and a current
  one `unchanged`; a deleted harness file `sync` and a current one `unchanged`.

`tests/test_upgrade_precommit_refresh_at_same_version.py` keeps the
predecessor card's two behavioral cases and now exercises
`_append_precommit_hook(probe=True)` — including the absent-config and
no-stanza cases the retired predicate reported as "not pending".

Both modules pin the engine's config lookup to the repo under test
(`_engine_config_at`), because `goc.engine` resolves
`GAME_OF_CARDS_CONFIG_FILE` once at import time. Every real `goc`
invocation is its own process, so that constant always matches; an
in-process test inherits whichever directory imported the engine first,
which otherwise makes `effective_skills_source()` — and so the
vendored/plugin decision — depend on test ordering.
