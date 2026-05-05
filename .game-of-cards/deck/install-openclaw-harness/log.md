# install-openclaw-harness log

## 2026-05-04: deferred by product direction

OpenCLAW harness work is deferred. OpenCLAW installation is not needed in this
repo, so the card should not remain active or be pulled by autonomous agents
until a concrete downstream repo needs OpenCLAW-native GoC guidance.

## 2026-05-05: superseded by plugin direction

Superseded by [provide-openclaw-plugin-for-skills-and-hooks](../provide-openclaw-plugin-for-skills-and-hooks/).

Reason: the clarified repo-footprint direction is plugin-provided skills/hooks
rather than checked-in per-repo harness files. OpenClaw should be added later
as a plugin/runtime package, not as another `goc install --agents ...` harness.
