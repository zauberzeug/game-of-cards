from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"


class ReleaseWorkflowClawHubSourceRefTest(unittest.TestCase):
    """ClawHub must package the post-rewrite tag, not only metadata.

    The reusable workflow accepts both `version` and `ref`. `version`
    controls registry metadata; `ref` controls which repository snapshot
    is fetched for the package files. A release can otherwise advertise
    X.Y.Z while bundling an older `openclaw-plugin/package.json`.
    """

    def test_build_exposes_release_tag_ref_for_clawhub(self) -> None:
        text = WORKFLOW.read_text()

        self.assertIn(
            "clawhub_source_ref: ${{ steps.clawhub_source_ref.outputs.ref }}",
            text,
        )
        self.assertIn("id: clawhub_source_ref", text)
        self.assertRegex(
            text,
            re.compile(r"release\|tag\)\n\s+ref=\"v\$RELEASE_VERSION\"", re.MULTILINE),
        )
        self.assertRegex(
            text,
            re.compile(r"dry_run\)\n\s+ref=\"\$GITHUB_SHA\"", re.MULTILINE),
        )

    def test_clawhub_publish_uses_source_ref_and_metadata_version(self) -> None:
        text = WORKFLOW.read_text()
        self.assertIn("\n  publish-clawhub:", text)
        publish_job = text.split("\n  publish-clawhub:", 1)[1]

        self.assertIn("source: ${{ github.repository }}", publish_job)
        self.assertIn("ref: ${{ needs.build.outputs.clawhub_source_ref }}", publish_job)
        self.assertIn("source_path: openclaw-plugin", publish_job)
        self.assertIn("version: ${{ needs.build.outputs.release_version }}", publish_job)
        self.assertNotRegex(
            publish_job,
            re.compile(r"^\s+source: \./openclaw-plugin$", re.MULTILINE),
        )


class ReleaseWorkflowClawHubRedispatchTest(unittest.TestCase):
    """ClawHub must be published by a workflow_dispatch run triggered ON the
    release tag, so the OIDC `sha` equals the published commit.

    ClawHub's trusted-publish guard rejects a publish whose resolved source
    commit differs from the OIDC-verified `sha`. A from-`main` `release`
    dispatch mints its OIDC token for the pre-rewrite HEAD, but the bundle
    is the bot's post-rewrite tag commit — they never match. The fix:
    `release.yml` self-re-dispatches on the tag with `clawhub_only=true`
    (GITHUB_TOKEN + `actions: write`; no PAT), where the OIDC `sha` IS the
    tag commit. The from-main run must therefore NOT publish ClawHub
    directly, and the tag-triggered run must NOT re-dispatch again (no loop).
    """

    def _job(self, text: str, key: str) -> str:
        """Slice a single top-level job body (from its key to the next job)."""
        keys = [
            "build", "smoke", "publish-pypi", "publish-npm",
            "publish-clawhub", "redispatch-clawhub",
        ]
        start = text.index(f"\n  {key}:")
        rest = text[start + len(f"\n  {key}:"):]
        nexts = [rest.index(f"\n  {k}:") for k in keys if f"\n  {k}:" in rest]
        return rest[: min(nexts)] if nexts else rest

    def test_clawhub_only_input_exists(self) -> None:
        text = WORKFLOW.read_text()
        self.assertRegex(
            text,
            re.compile(r"^      clawhub_only:$", re.MULTILINE),
            "release.yml must declare a `clawhub_only` workflow_dispatch input",
        )

    def test_redispatch_job_self_dispatches_clawhub_on_the_tag(self) -> None:
        text = WORKFLOW.read_text()
        self.assertIn("\n  redispatch-clawhub:", text)
        job = self._job(text, "redispatch-clawhub")

        # Gated to the from-main release path only — never in tag/dry/clawhub_only
        # modes, or it would loop forever.
        self.assertIn("needs.build.outputs.mode == 'release'", job)
        self.assertIn("!inputs.dry_run", job)
        self.assertIn("!inputs.clawhub_only", job)

        # Needs the tag (pushed by build) and smoke before delegating.
        self.assertIn("needs: [build, smoke]", job)

        # Self-dispatch requires actions: write; no PAT.
        self.assertIn("actions: write", job)

        # Re-dispatches THIS workflow on the tag ref, ClawHub-only.
        self.assertIn("gh workflow run release.yml", job)
        self.assertIn('--ref "v$RELEASE_VERSION"', job)
        self.assertIn("-f clawhub_only=true", job)
        # Version flows through env (not inline ${{ }}) into the shell.
        self.assertIn("RELEASE_VERSION: ${{ needs.build.outputs.release_version }}", job)

    def test_publish_clawhub_runs_only_in_tag_or_dry_run_not_release(self) -> None:
        text = WORKFLOW.read_text()
        job = self._job(text, "publish-clawhub")
        if_line = next(ln for ln in job.splitlines() if ln.strip().startswith("if:"))

        # Runs in tag mode (the clawhub_only re-dispatch + manual recovery)…
        self.assertIn("needs.build.outputs.mode == 'tag'", if_line)
        # …but NOT in release mode: that path delegates to redispatch-clawhub.
        self.assertNotIn("needs.build.outputs.mode == 'release'", if_line)
        # Accepts a skipped smoke (the clawhub_only re-dispatch skips smoke).
        self.assertIn("needs.smoke.result == 'skipped'", if_line)

    def test_smoke_pypi_npm_skipped_in_clawhub_only_mode(self) -> None:
        text = WORKFLOW.read_text()
        for key in ("smoke", "publish-pypi", "publish-npm"):
            job = self._job(text, key)
            if_line = next(
                ln for ln in job.splitlines() if ln.strip().startswith("if:")
            )
            self.assertIn(
                "!inputs.clawhub_only", if_line,
                f"{key} must be gated off in clawhub_only mode",
            )


if __name__ == "__main__":
    unittest.main()
