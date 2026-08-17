## 2026-08-17 — Decision: what "safe on the second run" means

The DoD asked whether "refuses on the second run" counts as safe for every
verb or only for the ones where refusing is the documented contract. Neither:
**refusal is not the property at all.** What protects the deck is that a
second run leaves the recorded state alone; refusing is one way a verb
achieves that, and a verb that refuses *after* a partial write is exactly the
defect shape this card generalizes. Making exit-nonzero the pass condition
would wrongly redden `status`/`wait`/`publish`, whose silent no-op is correct;
making exit-zero the pass condition would wrongly redden `new`/`move`/`decide`,
whose refusal is correct.

So `tests/test_verb_rerun_safety.py` asserts state preservation for every
surface and has each surface declare, in one word, which shape its second run
takes:

| Disposition | Second run | Declared by |
|---|---|---|
| `READ_ONLY` | exits 0; *neither* run touches the tree | validate, show, triage, quality-pass |
| `NO_OP` | exits 0; touches nothing | status, done, publish, repair-edges, migrate, migrate-list-style |
| `REFUSES` | exits nonzero; touches nothing | new, move, decide, install |
| `RE_EMITS` | exits 0; rewrites files with identical bytes | advance, unadvance, wait, upgrade |
| `APPENDS` | exits 0; only extends existing files | attest |

Three consequences worth stating, because each was a judgment call:

- **Exit codes are pinned coarsely, zero versus nonzero, not exactly.** A verb
  silently flipping between "refuse" and "no-op" is a contract change and
  should turn the build red; whether it exits 1 or 2 is the business of the
  per-verb test. This is not hypothetical — `second-install-exits-nonzero`
  closed on an exit-zero reinstall in 2026-05 and the contract was
  deliberately reversed in 2026-07. Coarse pinning would have reddened on that
  reversal, which is right, and would not have churned on a code change.
- **A same-bytes rewrite counts as a change** (the check compares mtime as
  well as content) for every disposition except `RE_EMITS`. Content alone is
  too weak where a timestamp is involved: the two runs land in the same
  wall-clock second, so a re-stamped `closed_at` — instance 2 of this card's
  own family — compares byte-equal. Verified by reintroducing that defect:
  deleting the `if prior == "done"` short-circuit in `_cmd_done` reddens the
  `done` subtest via the mtime clause, and the content clause alone stays
  green. Four surfaces re-emit identical bytes today and say so in their row;
  that is declared, not exempted, and a surface that stops re-emitting also
  turns red, so the allowance cannot quietly widen.
- **`attest` is append-only, not idempotent.** It writes to `log.md`, which is
  the journal, so a second attestation is a second event and appending is the
  contract. The check for it is that the second run *extends* the record —
  every prior file still present, every prior content a prefix of the new,
  and something actually grew — rather than rewriting history.

## 2026-08-17 — Decision: which non-verb surfaces come under the check

The DoD asked for the instance list's non-verb surfaces to be covered or
scoped out with a reason. Both entry points are covered; the internal helper
is covered through one of them; skill bodies are out.

- **`goc install` / `goc upgrade` are first-class rows.** They never reach the
  engine parser — `goc/cli.py` intercepts them on `argv[0]` — so a
  parser-derived list would have silently missed the two oldest instances in
  the family. That tuple is now the module constant `cli.INSTALL_VERBS` and
  the test unions it with the subparser registry, which is the whole
  derivation: both places a verb can be registered, neither hand-copied.
- **`_merge_claude_settings` is covered through `upgrade`.** It is not a
  command, and it is reachable only from the vendored install path, so the
  `upgrade` recipe installs with `--local-skills` and re-runs with
  `--keep-local-skills`. That is the only recipe that invokes the merge twice
  (`install` refuses its second run before reaching it), and both closed
  instances on that surface — a reflowed `settings.json` and a spurious `.bak`
  — are a content change or an added file, which the check reads directly.
- **Skill bodies are out of scope.** Two instances (the kickoff skill, the
  refine-deck citation-repair recipe) are prose an agent executes, not a
  command a harness can invoke twice; there is no process to run and no exit
  code to read. They keep their own per-surface tests. The card said as much
  when it was filed, and building the check confirmed it rather than changing
  it: this guard covers the executable surface, and the prose surface needs a
  different mechanism than "run it twice".

## 2026-08-17 — Closure

- **What changed**: `tests/test_verb_rerun_safety.py` (new) runs all 19
  surfaces goc registers twice against a scratch repo and asserts the second
  run preserves recorded state, with the surface list derived from
  `engine._build_parser()`'s subparser registry unioned with the new
  `cli.INSTALL_VERBS` constant (`goc/cli.py`, the only production change: the
  intercept tuple was a literal inside `main()`). A verb added tomorrow has no
  row in the recipe table and fails `test_every_registered_surface_has_a_rerun_recipe`
  before it can fail anything subtler.
- **Verification**: `reproduce.py` exits 0, and it no longer decides that by
  grepping for the right words — its first rewritten draft nominated
  `tests/test_guidance_accuracy.py`, so it now requires a module carrying a
  table keyed by exactly the registered verb set, and then runs it. Removing
  `tests/test_verb_rerun_safety.py` puts it back to exit 1. The guard is shown
  to catch offenders three ways: five stub surfaces, one per clause, each of
  which must make the assertion helper raise; a synthetic `frobnicate`
  subparser, which reddens the recipe check; and the reintroduced `done`
  re-stamp described above, which reddens the `done` subtest end to end.
- **Audit**: PASS — no rubric configured; the project-local finish-card hook is
  an empty stub. Every fixture asserts the first run changed something, so a
  recipe that rots into a no-op fails loudly instead of passing vacuously.
- **Project impact**: the module runs in 4.8s (a per-surface deck template is
  built once and copied, which cut it from 14.2s).
- **Tests**: 993 passed / 0 failed (`uv run python -m unittest discover -s
  tests`); `uv run goc validate` clean; `scripts/sync_plugin_assets.py --check`
  and `scripts/port_skills_to_openclaw.py --check` both clean.
- **Bundled with**: n/a

The census in `reproduce.py` still reads 1/14 and should. It counts per-verb
re-run tests, which is a different measurement from the single class-level
check that now covers all of them; driving that number up by writing thirteen
more named tests is the practice this card was filed against.

## Closure verification (2026-08-17T05:31:15Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — all 1 closed
- [x] dod-100-percent — 6/6 ticked
- [x] log-md-closure-entry — '## 2026-08-17 — Closure' present
