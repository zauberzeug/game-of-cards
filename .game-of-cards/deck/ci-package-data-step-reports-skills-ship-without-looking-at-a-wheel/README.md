---
title: ci-package-data-step-reports-skills-ship-without-looking-at-a-wheel
summary: "ci.yml's Verify package data ships templates step lists the skills under goc/templates/skills and checks each one exists under files('goc.templates'), which under CI's editable install is the same directory, so it prints that all 18 skills ship without ever looking at a wheel. The real check now runs in the suite (tests/test_wheel_package_parity.py builds the wheel with uv build), leaving the step as a pass that cannot fail beside it. Deleting or rewiring it is a .github/workflows/ edit the bot's GITHUB_TOKEN cannot push."
status: open
stage: null
contribution: low
created: "2026-10-04T06:39:54Z"
closed_at: null
human_gate: session
advances: []
advanced_by: []
tags: [bug, infra, test]
draft: true
definition_of_done: |
  - [ ] (replace with real criteria)
---

# ci-package-data-step-reports-skills-ship-without-looking-at-a-wheel

(write the design doc here)
