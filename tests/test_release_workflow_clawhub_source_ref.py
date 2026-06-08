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


if __name__ == "__main__":
    unittest.main()
