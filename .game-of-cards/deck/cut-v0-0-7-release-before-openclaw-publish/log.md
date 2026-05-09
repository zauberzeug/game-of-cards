
## 2026-05-09 — Tag-push CI gap surfaced; published via workflow_dispatch on tag ref

Sequence of events:

1. Bumped versions in 7 source-of-truth files; sync hook auto-mirrored `goc/__init__.py` to the two plugin payloads. Committed as `23d8958 release: bump to 0.0.7`.
2. Pushed `main` and tagged + pushed `v0.0.7` (run `25608246745`). Build job passed; smoke job failed at `Path A — kickoff completes against fresh repo` with `Action failed with error: Unsupported event type: push` from `anthropics/claude-code-action@v1`. Publish job was skipped (gated on `needs: [build, smoke]`).
3. Re-triggered via `gh workflow run release.yml --ref v0.0.7` (run `25608296877`) — the workflow_dispatch event type IS supported by the smoke action, while `github.ref` still resolves to `refs/tags/v0.0.7` so publish's `startsWith(github.ref, 'refs/tags/v')` guard still fires. Build (12s) → Smoke (6m18s, both Path A and Path B passed) → Publish (17s) all green.
4. Confirmed `pip index versions game-of-cards` reports `0.0.7` as latest; PyPI JSON API agrees.

**Follow-up:** the release workflow as currently designed quietly breaks tag-push: build runs, smoke errors on the unsupported event, publish is silently skipped, and a human watching the Actions tab might assume the broken smoke is the only issue. The canonical flow is now "push the tag, then `gh workflow run release.yml --ref vX.Y.Z`" — but that's an undocumented procedural workaround. A clean fix would either (a) make smoke skip on `push` events and not block publish there, (b) split smoke into a separate workflow that runs on workflow_dispatch only, or (c) replace the action with something that accepts push events. Worth filing a card for it, but out of scope here.
