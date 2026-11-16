## 2026-11-16T01:05:00Z — Parked as unverified by audit-deck

Came up while sweeping siblings for
[regression-suite-is-red-in-bot-runs-whose-git-refuses-implicit-bare-repositories](../regression-suite-is-red-in-bot-runs-whose-git-refuses-implicit-bare-repositories/),
by checking whether shipped code mishandles bare repositories as the test
fixtures do. It does, but with a different root cause: the shared worktree-deck
walk equates "parent of the common directory" with "primary working tree".
Reproduced once by hand. The commands and output are in the README's
Falsification recipe. Parked without a `reproduce.py` under the audit's
park-or-disprove rule.

- **Dedup**: 12 cards mention `worktree_deck` or `GOC_WORKTREE_DECK`, and none
  covers a bare clone or a layout without a primary working tree.
