## 2026-10-04T06:05:00Z — Hypothesis verified

Claimed from the ready queue. `reproduce.py` ran the falsification recipe on
scratch bare remotes with two clones each. Neither escape fired. A default claim
printed `committed` with no `pushed`, the remote's main did not move, and a
second stale claimer also exited 0. With the shipped `claim_push: true` line
uncommented, agent-A's claim pushed and agent-B's stale claim exited 2 with
"claim race — already claimed by 'agent-A'", and the remote kept agent-A. Both
halves of the hypothesis hold, so the `unverified` tag comes off.

Three more findings came out of the run:

- **Identical claims under `claim_push`.** Two clones with one shared
  `user.name`, or a card whose preset `worker` designation both claims keep,
  write patch-identical claims. The second one's rebase drops its commit and
  it prints `pushed (after rebase)`, exit 0. When both claims land in the same
  second, the commits are byte-identical and the first push already "succeeds".
  This is already filed, decision-gated:
  `claim-push-reports-success-when-rebase-drops-identical-racing-claim`. It
  is not fix-through material, since a human has to pick abort, adopt, or an
  explicit `--reclaim`. The row therefore documents the hole and links that
  card, rather than overclaiming "the later claimer is refused".
- **Offline under `claim_push`.** The same page's Offline row says "Git push
  deferred". With `claim_push: true` and an unreachable remote, the claim
  commits locally, but `goc status` exits 2 ("push failed and fetch failed").
  It is the same page and the same omission of the opt-in, so it is fixed here
  under an added DoD box.
- **The cited decision is the source of the error.** The Decision on the
  closed `design-claim-protocol-with-branch-and-author-metadata` says
  "last-writer-wins on claim push with re-fetch+retry", while its own DoD
  item 4 shipped an abort for the later claimer. The page restated the
  decision faithfully. The closed card gets a forward pointer.

Grepping the claim rather than the file found the same reassurance ("git's
merge handles the claim race", "whichever commits first wins") in `ABOUT.md`
and in the shipped deck skill (`SKILL.md`, `reference.md`). That is three files
plus six mirrors, so it is not fix-through. It is filed as
`deck-skill-promises-git-merge-settles-claim-races-the-default-config-never-detects`
(gate none, left in the queue).

## 2026-10-04T06:19:15Z — Closure

- **What changed**:
  - `DECK_LOCATION.md` "Claim and sync semantics", Same-repo row. A claim
    commits locally and pushes only with `workflow.claim_push: true` (off by
    default). With it set, the first writer wins and the later claimer exits 2
    naming the racing worker. An identical claim reports success, with a link to
    the open card. Without it, nothing detects the race.
  - `DECK_LOCATION.md` "Offline behavior", Same-repo row: the `claim_push`
    exception (an offline claim exits 2).
  - New guard `tests/test_deck_location_claim_rows.py` (3 tests). It runs the
    protocol on scratch remotes in four setups (default, distinct identities,
    one shared identity, offline) using the shipped config template. It checks
    both rows in both directions, fires all five checks on the pre-fix wording,
    and fires all five on the current wording with every observation flipped.
  - `design-claim-protocol-with-branch-and-author-metadata`: one-line forward
    pointer and a post-close amendment in its log.
  - `doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them`:
    edge wired (26th instance) with a table row, the count sentence and a log
    entry. The new sibling is wired as the 27th, with a *none yet — open* row.
- **Verification**:
  - `reproduce.py` exits 1 on the pre-fix page (`git show 8c7a4053:DECK_LOCATION.md`)
    with five contradicted claims, and exits 0 on the fix.
  - Pointed at the pre-fix page with live observations, the guard reports the
    same five checks.
  - A scratch-copy mutation that defaults `claim_push` to on turns the live
    guard red on `default-push` and `default-race`.
- **Audit**: no rubric configured; mechanical fix.
- **Project impact**: a reader setting up parallel agents from
  `DECK_LOCATION.md` now learns that claims only propagate with
  `workflow.claim_push: true`, who wins a race under it, and the shared-identity
  hole that bot fleets hit.
- **Tests**: 1220 passed / 0 failed (`uv run python -m unittest discover -s
  tests`). `goc validate`, `sync_plugin_assets.py --check`,
  `port_skills_to_openclaw.py --check`, `check_card_language.py` and
  `check_card_frontmatter_yaml.py` are all clean.

## Closure verification (2026-10-04T06:19:41Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-10-04 — Closure' present
