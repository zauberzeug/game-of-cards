---
title: pypi-trusted-publisher-missing-for-release-workflow
summary: "The tag-triggered release workflow builds valid artifacts but PyPI rejects the trusted-publishing token because no matching publisher is configured for zauberzeug/game-of-cards, release.yml, environment pypi."
status: active
stage: null
contribution: high
created: 2026-05-04
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [x] PyPI trusted publisher is configured for owner `zauberzeug`, repo `game-of-cards`, workflow `release.yml`, environment `pypi`
  - [x] A tag-triggered release publish succeeds without a manual PyPI token
  - [x] Release docs or workflow comments include the exact claims needed to repair the setup
---

# PyPI Trusted Publisher Missing For Release Workflow

## Location

- `.github/workflows/release.yml`
- GitHub Actions run `25322155017`, job `Publish to PyPI`
- PyPI project `game-of-cards`

## What's Broken

The `v0.0.3` release workflow accepted the tag and built both artifacts, but
the publish job failed during PyPI's trusted-publishing exchange.

The failed job reported:

```text
Trusted publishing exchange failure:
Token request failed: the server refused the request for the following reasons:

* `invalid-publisher`: valid token, but no corresponding publisher
  (Publisher with matching claims was not found)
```

The debug claims PyPI saw were:

```text
sub: repo:zauberzeug/game-of-cards:environment:pypi
repository: zauberzeug/game-of-cards
repository_owner: zauberzeug
workflow_ref: zauberzeug/game-of-cards/.github/workflows/release.yml@refs/tags/v0.0.3
job_workflow_ref: zauberzeug/game-of-cards/.github/workflows/release.yml@refs/tags/v0.0.3
ref: refs/tags/v0.0.3
environment: pypi
```

## Evidence

Local release checks passed before the tag was pushed:

```text
uv run pytest -> 33 passed
uv run goc validate --quiet -> exit 0
uv run goc --version -> goc, version 0.0.3
uv build -> built dist/game_of_cards-0.0.3.tar.gz and dist/game_of_cards-0.0.3-py3-none-any.whl
```

GitHub Actions job state:

```text
Build wheel + sdist -> success
Verify tag matches pyproject version -> success
Publish to PyPI -> failure
```

## Why It Matters

The release workflow looks production-ready from the repository side, but
cannot publish without the one-time PyPI trusted-publisher registration. Until
that external project setting exists, releases require a manual token upload.

## Fix

Configure PyPI trusted publishing for:

```text
Owner: zauberzeug
Repository: game-of-cards
Workflow name: release.yml
Environment: pypi
```

Then re-run a tag-triggered release with a fresh version and verify PyPI
publishes without `UV_PUBLISH_TOKEN`.
