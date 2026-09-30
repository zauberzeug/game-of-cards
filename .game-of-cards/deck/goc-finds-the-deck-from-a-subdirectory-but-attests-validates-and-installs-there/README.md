---
title: goc-finds-the-deck-from-a-subdirectory-but-attests-validates-and-installs-there
summary: "The deck lookup walks up from a subdirectory to the root deck, but every other notion of the project root is still the current directory: `REPO_ROOT = Path.cwd()` in the engine, `target = Path.cwd()` in `goc install` / `goc upgrade`, and the hook input's cwd in both runtime hooks. Run from a subdirectory, `goc attest` executes the project's closure checks there and records a PASS the root run fails, `goc validate` skips its skill-parity and plugin-mirror checks and exits 0, and the session-start hook stays silent about active cards that `goc` lists from the same directory. `goc upgrade` there reports no install and points at `goc install`, which scaffolds a stray nested deck that then hides the real one from everything below it."
status: active
stage: null
contribution: high
created: "2026-09-28T01:20:21Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, infra, meta-fix]
definition_of_done: |
  - [ ] TDD: `uv run python .game-of-cards/deck/goc-finds-the-deck-from-a-subdirectory-but-attests-validates-and-installs-there/reproduce.py` exits zero (every surface run from `src/pkg/` agrees with the root run)
  - [ ] TDD: a regression test runs `goc attest` from a subdirectory and asserts the automated check runs in the project root; the same test, under shared-deck worktree mode, asserts it runs in the linked worktree's root, not the primary tree
  - [ ] TDD: a regression test asserts `goc validate` from a subdirectory reports the same vendored skill-parity error as the root run
  - [ ] TDD: a regression test asserts `goc install` from a subdirectory of an installed repo refuses and writes nothing, and `goc upgrade` from there acts on the enclosing install
  - [ ] TDD: a parity test pins the hooks' project-dir walk to `engine._resolve_deck_root` over the layouts in `tests/test_subdirectory_deck_resolution.py`
  - [ ] MECHANICAL: the `REPO_ROOT` comment (`goc/engine.py:37`) and the `_resolve_deck_root` docstring describe the single derivation, and `goc.md:70`'s "any nested directory" promise covers attest, validate, upgrade and install (or names the exception)
  - [ ] MECHANICAL: `uv run goc validate` clean; `python scripts/sync_plugin_assets.py --check` clean
worker: {who: "claude[bot]", where: main}
---

# goc finds the deck from a subdirectory, but attests, validates and installs there

## Summary

Since 3e17e3b3 (2026-07-15), the engine finds the deck by walking up from
the current directory to the nearest ancestor that holds `.game-of-cards/`.
That is why `goc`, `goc new` and `goc show` work from any subdirectory, as
`goc.md` promises. But the walk feeds exactly one variable, `DECK_ROOT`.
Every other place that needs "the project" still answers with the current
directory:

- the engine's `REPO_ROOT = Path.cwd()`
- the installer's `target = Path.cwd().resolve()`
- the runtime hooks' `<cwd>/.game-of-cards/`

From a subdirectory the two answers disagree. Every surface that reads the
second answer quietly does the wrong thing, and none of them reports an
error:

| Surface, run from `src/pkg/` | Reads | What happens |
|---|---|---|
| `goc attest` automated checks | `REPO_ROOT` as the check's `cwd=` | The check runs over `src/pkg/` only. The root run fails it, this run passes it, and `log.md` records the pass as an attestation. |
| `goc validate`, vendored skill-dir parity | `REPO_ROOT / ".claude/skills"` | The directory is not found, so the check is skipped. Exit 0 where the root run exits 1. |
| `goc validate`, plugin mirror + hook-registry parity (this repo) | `REPO_ROOT / "claude-plugin"`, … | The payload roots are not found, so both checks are skipped. Exit 0 despite real mirror drift. |
| session-start hook | `<cwd>/.game-of-cards/deck` | Prints nothing, while `goc --status active` from the same directory lists the active card. |
| pattern-generalization hook | `<project dir>/.game-of-cards/config.yaml` | The opt-in is not found, so the hook is disabled. |
| `goc upgrade` | `target = Path.cwd()` | `no existing install detected — run \`goc install\` first.` (exit 1) |
| `goc install`, the next step that hint names | `target = Path.cwd()` | Scaffolds `src/pkg/.game-of-cards/`, `AGENTS.md` and `CLAUDE.md`. From then on, every command below `src/pkg/` resolves the empty stray deck. |

## Location

The one walk that does exist:

- `goc/engine.py:73` `_resolve_deck_root(cwd)`, feeding
  `goc/engine.py:146` `DECK_ROOT = _resolve_deck_root(REPO_ROOT)`.

The derivations that ignore it:

- `goc/engine.py:37`: `REPO_ROOT = Path.cwd()  # project being managed (consuming repo's root)`. It is read by:
  - `:5719` `cwd=str(REPO_ROOT)` in `_run_automated_check`, which is `goc attest`'s layer-2 runner.
  - `:1421` `consumer_dir = REPO_ROOT / relative`, then `:1422-1423` `if not consumer_dir.exists(): continue`, in `validate_skill_dir_parity`.
  - `:1599` `hooks_dir = REPO_ROOT / plugin / "hooks"` in `validate_plugin_hook_registration`.
  - `:1706-1708` `claude_plugin_root = REPO_ROOT / "claude-plugin"` … in `validate_plugin_mirror_parity`.
  - `:5672` `repo_root = REPO_ROOT if repo_root is None else repo_root` in `validate_plugin_hook_double_fire`.
  - `:6404` `path.relative_to(REPO_ROOT)` in `_display_path`.
- `goc/install.py:1827` `target = Path.cwd().resolve()` in `install()`, then
  `:1856` `existing_dir = _find_installed_deck_dir(target)`. That function
  (`:510-518`) only looks directly under `target`.
- `goc/install.py:1997` `target = Path.cwd().resolve()` in `upgrade()`, then
  `:2019-2022` `deck_dir = _find_installed_deck_dir(target)` →
  `no existing install detected — run \`goc install\` first.`
- `goc/templates/hooks/deck_session_start.py:274-290`:
  `_project_dir_from_hook_input()` returns the hook input's `cwd`, and
  `main()` then reads `Path(project_dir) / ".game-of-cards" / "deck"`.
- `goc/templates/hooks/pattern_generalization_check.py:216` and `:98`:
  `project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or "."`,
  then `Path(project_dir) / ".game-of-cards" / "config.yaml"`. The two
  hooks also disagree on precedence: session-start tries the hook input's
  `cwd` first, pattern-check tries `CLAUDE_PROJECT_DIR` first.

## What's broken

The documented contract is written for "any nested directory". Here is
`goc.md:70`:

> You may run it from any nested directory: GoC walks upward to the nearest
> existing `.game-of-cards/` root. If none exists, it refuses and points back
> to `goc install` instead of creating a stray deck.

And here is the engine's own rule for the fallback, in the
`_resolve_deck_root` docstring (`goc/engine.py:86-89`):

> Falling back to cwd keeps read-only commands useful before installation;
> mutating creation commands must reject that fallback instead of silently
> scaffolding a second deck.

`goc install` is the one creation command outside the engine, and it
scaffolds a second deck silently. It reaches that point in the most natural
way possible: `goc upgrade`, run from the same directory, prints that no
install exists and names `goc install` as the fix. The comment on
`REPO_ROOT` claims it is "the consuming repo's root". From a subdirectory it
is not, and nothing recomputes it once `DECK_ROOT` is known.

The family is not new. Three closed cards each moved one call site from
`REPO_ROOT` to `DECK_ROOT` for shared-deck worktree mode:

- [goc-new-crashes-with-valueerror-when-deck-lives-in-shared-worktree-root](../goc-new-crashes-with-valueerror-when-deck-lives-in-shared-worktree-root/), closed 2026-06-24
- [goc-move-runs-git-operations-in-the-wrong-tree-under-shared-deck-worktree-mode](../goc-move-runs-git-operations-in-the-wrong-tree-under-shared-deck-worktree-mode/), closed 2026-06-27
- [goc-migrate-runs-filesystem-operations-in-the-wrong-tree-under-shared-deck-worktree-mode](../goc-migrate-runs-filesystem-operations-in-the-wrong-tree-under-shared-deck-worktree-mode/), closed 2026-07-07

Then 3e17e3b3 made the two variables diverge in the default configuration,
from any plain subdirectory. Nobody re-audited the remaining `REPO_ROOT`
readers. Nobody audited the two derivations that never read `REPO_ROOT` at
all either: the installer's target and the hooks' project dir.
[subdirectory-deck-resolution-has-no-test-pinning-it](../subdirectory-deck-resolution-has-no-test-pinning-it/)
pinned the walk for readers. Its test runs `goc validate` from a
subdirectory, but it asserts only on card validation, so the skill-parity
branch that reads `REPO_ROOT` was never exercised.

## Empirical evidence

`reproduce.py` builds a throwaway git repo with a vendored
(`--local-skills`) install and a plain subdirectory `src/pkg/`. It runs each
surface once from the root and once from `src/pkg/`. The closure check it
configures takes one input, its working directory: it fails if any `*.py`
file below that directory holds a FIXME, and the fixture's only FIXME is in
the root-level `app.py`. For the install and upgrade rows it compares
outcomes (exit code, whether the install was recognized, whether anything
was created), not message wording.

`uv run python .game-of-cards/deck/goc-finds-the-deck-from-a-subdirectory-but-attests-validates-and-installs-there/reproduce.py`:

```
Precondition: the engine resolves the root deck from src/pkg/
  `goc --status all --json` from src/pkg/ lists: ['demo-card']

1. goc attest: where the project's closure check runs
  DIFFERS: closure-check row
      from <repo>/        : [ ] no-fixme-markers — exit 1: ran in <repo> -- 1 FIXME marker(s)
      from <repo>/src/pkg/: [x] no-fixme-markers — ran in <repo>/src/pkg -- 0 FIXME marker(s)
  DIFFERS: prints 'Attestation OK.'
      from <repo>/        : False
      from <repo>/src/pkg/: True
  last block written to log.md records: - [x] no-fixme-markers — ran in <repo>/src/pkg -- 0 FIXME marker(s)

2. goc validate: the vendored skill-dir parity check
  baseline from <repo>/: exit 0
  removed the vendored .claude/skills/deck/ skill
  DIFFERS: validate (exit code, parity verdict)
      from <repo>/        : (1, 'reports missing skill')
      from <repo>/src/pkg/: (0, 'silent')

3. hooks: the session-start reminder and the pattern-check opt-in
  `goc --status active --json` from src/pkg/ lists: ['demo-card']
  DIFFERS: session-start hook output
      from <repo>/        : [GoC] Active card(s): demo-card — resume or close before starting new work.
      from <repo>/src/pkg/: (nothing printed)
  DIFFERS: pattern-check hook after an Edit turn
      from <repo>/        : exit 2 (reminder)
      from <repo>/src/pkg/: exit 0 (disabled)

4. goc upgrade, then the goc install it points at
  DIFFERS: goc upgrade --dry-run
      from <repo>/        : exit 0: already at goc 0.0.27.post1.dev459 — nothing to do.
      from <repo>/src/pkg/: exit 1: no existing install detected — run `goc install` first.
  DIFFERS: goc install
      from <repo>/        : exit 1: already installed (.game-of-cards/deck/.goc-version → 0.0.27.post1.dev459)
      from <repo>/src/pkg/: exit 0: created .game-of-cards, AGENTS.md, CLAUDE.md here
  DIFFERS: deck `goc --status all --json` shows afterwards
      from <repo>/        : ['demo-card']
      from <repo>/src/pkg/: []
  `goc new` from src/pkg/ then prints: created .game-of-cards/deck/filed-from-the-subdirectory/
  ...and the card landed in: src/pkg/.game-of-cards/deck/ (the stray deck)

DEFECT CONFIRMED: 8 surface(s) run from a subdirectory disagree with the root run:
  - closure-check row
  - prints 'Attestation OK.'
  - validate (exit code, parity verdict)
  - session-start hook output
  - pattern-check hook after an Edit turn
  - goc upgrade --dry-run
  - goc install
  - deck `goc --status all --json` shows afterwards
```

Exit 1. The same shape holds for this repo's own mirror guard. In a scratch
clone with one byte appended to `claude-plugin/goc/engine.py`, `goc validate`
exits 1 at the root with
`ERROR: plugin mirror drift: goc vs claude-plugin/goc: engine.py (differs)`,
and exits 0 from `scripts/` with no mention of the drift.

## Why it matters

- **A closure gate that passes by where you stand.** `goc attest` is Step 5
  of `Skill(finish-card)`: it runs the project's layer-2 checks. The check's
  verdict is a function of the agent's shell directory, and the
  `## Closure verification` block does not record that directory. A pass
  recorded from `src/pkg/` therefore reads exactly like a real one. Agent
  harnesses keep the Bash working directory between calls, so the trigger
  is ordinary: `cd` into a package to run its tests, then attest. The
  resulting false pass is the failure mode this project files at high
  contribution (compare
  [bundled-closure-skips-configured-attestation-checks](../bundled-closure-skips-configured-attestation-checks/)).
  A false FAIL is just as reachable. A check written as
  `[python3, -m, unittest, discover, -s, tests]` fails from any directory
  without `tests/`, and the closer is sent hunting for a regression that
  does not exist.
- **A validator that goes quiet.** `goc validate` is how a human or agent
  checks the install. From a subdirectory it drops the skill-parity check,
  and in this repo also both plugin-payload checks, without saying so.
  Pre-commit and CI run at the root, so they are unaffected. The hand-run
  "is my install healthy?" check is what fails.
- **The printed hint splits the deck.** Following `goc upgrade`'s message
  from a subdirectory runs `goc install`, which creates a stray deck. From
  that point, the engine's own nearest-ancestor walk prefers the stray deck
  for every command below it:
  - `goc` there lists nothing;
  - cards filed there land in the stray deck, invisible from the root and to
    every other agent;
  - `goc new` prints `created .game-of-cards/deck/<title>/` (relative to
    cwd), so the agent cannot tell which deck received the card.
  It also writes a second `AGENTS.md` / `CLAUDE.md` pair into the
  subdirectory, which a host that loads nested guidance files would then
  read.
- **The resume signal disappears.** The session-start line is how an agent
  learns it has an active card to resume. A session launched in a monorepo
  package directory never sees it, although `goc` in that directory would
  list the card.

Reachability needs no hand-editing. Every trigger is a stock command run
from a subdirectory of an installed repo: an agent session launched there, a
`cd` that persists between agent tool calls, or a human running
`goc upgrade` from wherever their terminal happens to be.

## Fix

**1. One derivation of the project root in the engine.** Compute `DECK_ROOT`
from `Path.cwd()` first, then derive `REPO_ROOT` from it:

- **When `DECK_ROOT` holds `.game-of-cards/` and is cwd or an ancestor of
  cwd:** `REPO_ROOT` is `DECK_ROOT`.
- **Under the shared-deck worktree redirect** (`DECK_ROOT` is the primary
  tree and is not an ancestor of cwd): `REPO_ROOT` is the current working
  tree's top level (`git rev-parse --show-toplevel`). That is the tree the
  three shared-worktree fixes already assumed `REPO_ROOT` names.
- **When no deck resolves:** cwd, as today.

Every existing reader then gets the right root with no per-site edit:
`:1421`, `:1599`, `:1706-1708`, `:1752`, `:5672`, `:5719`, `:6404`, and the
`:6238` message.

**2. The installer uses the same walk.** Resolve `target` at
`goc/install.py:1827` and `:1997` through `engine._resolve_deck_root`,
including its boundary rule.

- `goc upgrade` from a subdirectory then upgrades the install it sits in,
  the same way `goc new` already files into it.
- `goc install` there prints the same `already installed (…)` refusal the
  root run prints, instead of scaffolding.
- With no enclosing deck, `install` keeps scaffolding at cwd. That keeps the
  "run `goc install` at the intended project root" contract of
  `goc/engine.py:6238-6239`.

**3. The hooks use the same walk.**
`goc/templates/hooks/deck_session_start.py:274-290` and
`pattern_generalization_check.py:98` / `:216` should resolve the project dir
with the same bounded walk: the nearest ancestor holding `.game-of-cards/`,
never crossing into a different git working tree. The hooks are standalone
scripts that import nothing from the package, by design, so the walk has to
be a mirror. Pin it to `engine._resolve_deck_root` over the fixture layouts
of `tests/test_subdirectory_deck_resolution.py`, the way
`tests/test_waiting_on_int_mirror.py` pins `_INT_RE`. While there, give
both hooks one input precedence, the session-start order. Once the walk
exists, the two sources agree whenever both sit inside the project.

**4. A test that runs each root reader from a subdirectory**, in the shape
of `reproduce.py`. The next surface that re-derives the root from cwd then
fails CI instead of failing a consumer.

**Why this fix and not the alternatives.** The card is filed at
`human_gate: none` because the project's own contracts decide the choice:

- *Refuse from subdirectories* (attest, install and upgrade exit with "run
  from the root"). This contradicts `goc.md:70`'s "any nested directory",
  and it makes these verbs disagree with `goc new`, which already redirects.
  Rejected.
- *Always run attest checks at `DECK_ROOT`.* Wrong under shared-deck
  worktree mode. There `DECK_ROOT` is the primary tree, while the code being
  closed is the linked worktree's checkout, so the checks would test the
  wrong tree. That is the mistake the three closed cards above fixed, in the
  other direction. The rule in step 1 picks `DECK_ROOT` when it encloses
  cwd, and the current tree's root otherwise.
- *Patch each site as it is found.* That is the shape that produced this
  card: three closed per-site fixes, then new divergences introduced by a
  change none of them anticipated.

A throwaway version of steps 1–3 (about 30 lines) turns `reproduce.py`
green in a scratch clone. `log.md` records that run and its suite result.

## Related cards

- [subdirectory-deck-resolution-has-no-test-pinning-it](../subdirectory-deck-resolution-has-no-test-pinning-it/)
  (done): pinned the walk for card readers. This card covers the root
  readers that walk never reached.
- [deck-root-ancestor-walk-escapes-nested-worktree-into-primary-deck-without-opt-in](../deck-root-ancestor-walk-escapes-nested-worktree-into-primary-deck-without-opt-in/)
  (done): the boundary rule the installer and hook walks must reuse.
- [openclaw-resolve-deck-dir-ignores-git-worktree-shared-deck-resolution](../openclaw-resolve-deck-dir-ignores-git-worktree-shared-deck-resolution/)
  (open): the OpenClaw port's resolver, which also never walks. This card
  covers the Python surfaces only.
- [session-start-hook-reimplements-engine-waiting-and-frontmatter-logic-and-keeps-drifting](../session-start-hook-reimplements-engine-waiting-and-frontmatter-logic-and-keeps-drifting/)
  (open): the hook's reimplementation family. The project-dir walk is one
  more reimplemented predicate.
- [attest-cmd-as-string-fails-with-misleading-single-character-not-found-error](../attest-cmd-as-string-fails-with-misleading-single-character-not-found-error/)
  (open): the same `_run_automated_check`, a different defect (the shape of
  `cmd`).
