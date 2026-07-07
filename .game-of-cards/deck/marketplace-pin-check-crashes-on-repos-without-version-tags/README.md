---
title: marketplace-pin-check-crashes-on-repos-without-version-tags
status: open
stage: null
contribution: low
created: "2026-07-07T01:11:36Z"
closed_at: null
human_gate: session
advances:
  - community-marketplace-pin-drifts-silently-behind-releases
advanced_by: []
tags: [bug, infra]
summary: |
  The marketplace-pin-check workflow dies with a bare exit 1 on any repo
  with no vX.Y.Z tags, because grep failing under `set -euo pipefail`
  kills the script before the empty-tag guard runs. The one-line fix is
  authored and verified, but the autonomous bot's token lacks the
  `workflows` permission — a human must apply and push it.
definition_of_done: |
  - [ ] MECHANICAL: The `|| true` fix below is applied to
    `.github/workflows/marketplace-pin-check.yml` and pushed by someone
    with workflow-write permission.
  - [ ] EMPIRICAL: `REPO=anthropics/claude-plugins-community bash <extracted run block>`
    prints "No release tag yet — nothing to compare." and exits 0.
  - [ ] PROCESS: `uv run goc validate` passes.
---

# marketplace-pin-check-crashes-on-repos-without-version-tags

## Why a human gate

The fix is fully determined and already verified — no decision needed.
But GitHub rejects any push touching `.github/workflows/` from the
autonomous bot's App token (`refusing to allow a GitHub App to create or
update workflow ... without "workflows" permission`), so an agent cannot
land it. A human session with normal push rights closes this in one
minute.

## Location

`.github/workflows/marketplace-pin-check.yml:58-59` (the `tag=$(...)`
assignment at the top of the `run:` block).

## What's broken

The script begins with `set -euo pipefail`, then resolves the latest
release tag:

```bash
tag=$(gh api --paginate "repos/$REPO/tags?per_page=100" --jq '.[].name' \
  | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' | sort -V | tail -1)
if [ -z "$tag" ]; then
  echo "No release tag yet — nothing to compare."
  exit 0
fi
```

When the repo has no `vX.Y.Z` tags, `grep` exits 1, `pipefail` fails the
command substitution, and `set -e` kills the script at the assignment —
the empty-tag guard on the very next line never runs. The workflow fails
with a bare exit 1 instead of the intended clean "nothing to compare"
exit.

Verified 2026-07-07 by running the extracted `run:` block with
`REPO=anthropics/claude-plugins-community` (no version tags): bare
`exit=1`, trace shows death at `tag=`.

## Why it matters

The closed parent card's DoD promised "repos without a published release
exit cleanly instead of erroring cryptically". For *this* repo the path
is unreachable (version tags exist and are never deleted), so drift
detection is unaffected — but anyone copying this workflow into a
pre-first-release repo gets a cryptically red run, and the parent card's
robustness contract is only honest once this lands.

## Fix (authored and verified — apply verbatim)

```diff
-          tag=$(gh api --paginate "repos/$REPO/tags?per_page=100" --jq '.[].name' \
-            | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' | sort -V | tail -1)
+          # `|| true`: grep exits 1 when no version tag exists; without it,
+          # set -e + pipefail would kill the script before the empty-tag
+          # guard below can exit cleanly.
+          tag=$(gh api --paginate "repos/$REPO/tags?per_page=100" --jq '.[].name' \
+            | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' | sort -V | tail -1 || true)
```

Verified on 2026-07-07 against the fixed script: tagless repo → "No
release tag yet — nothing to compare.", exit 0; this repo's tag still
resolves (v0.0.26 → `d19aa09a`), stale detection and grace window
unchanged. Full verification narrative:
[parent card](../community-marketplace-pin-drifts-silently-behind-releases/).
