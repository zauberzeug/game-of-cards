## 2026-05-11: decision recorded

Close — all DoD ticked; the chosen fix (smoke skipped on push events with publish gate tolerating skipped smoke) landed in 000708e, was verified on v0.0.13 and subsequent tags, and was further refactored into the single-trigger workflow_dispatch flow by find-single-trigger-release-flow-for-all-three-registries. — The 'human applies patch then verifies on real release' gate is satisfied: patch landed, releases v0.0.13/v0.0.15/v0.0.16 verified the smoke-on-dispatch flow, and the smoke job today only runs on workflow_dispatch by design.. Gate session → none.
