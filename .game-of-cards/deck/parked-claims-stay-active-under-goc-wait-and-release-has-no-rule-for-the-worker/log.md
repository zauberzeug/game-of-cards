
## 2026-10-22T05:20:16Z — Filed from the PR #11 split

- The identity part of PR #11 landed separately as `claims-without-a-git-identity-leave-active-cards-no-one-is-named-for`. The PR's three lifecycle changes (release on `goc wait` with `--keep-claim`, clearing `worker` on re-queue, `goc validate` requiring `worker` on active cards) were not taken over, because no card had decided them and clearing deletes pre-assignments.
- Evidence: probe on a temp deck with `worker: gpu-required`, run against the PR branch merged with main and against main (output in the README's Evidence section).
- Parked at `decision`: three questions, options in the README.
