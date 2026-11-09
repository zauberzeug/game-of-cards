## 2026-11-09T01:00:07Z — Related finding (audit-deck): CONTRIBUTING.md puts the smoke test before the tag push

Parked here, not filed separately: audit-deck files one new card per run, and this is another place where the release docs disagree with what `release.yml` does.

- **Drift:** `CONTRIBUTING.md:142-143` lists step 3 "Runs the end-to-end auto-bootstrap smoke test" before step 4 "Creates and pushes the tag". In `release.yml` the build job pushes the tag (`:424`, "Create and push release tag"), and the smoke job only starts afterwards (`:486`, `needs: build`). If smoke fails, the tag and the version-bump commit are already on the remote and nothing is published.
- **Already designed for:** the recovery is documented and was intended. `find-single-trigger-release-flow-for-all-three-registries` (done) and AGENTS.md "Recovery / republish on an existing tag" re-dispatch with `--ref vX.Y.Z`. The live defect is the ordering claim in CONTRIBUTING.md, which matters for how a reader judges a failed smoke run. Low contribution.
- **Not checked:** how `marketplace-pin-check` treats a tag that has no published packages. The hunter inferred this from the code and did not run it.
