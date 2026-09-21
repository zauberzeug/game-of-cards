---
title: shipped-epic-recipe-builds-the-backwards-edge-its-own-next-bullet-forbids
summary: "The aggregation-epic recipe in `advance-card/reference.md` states the canonical encoding as `child.advances: [epic]` and then gives the verb as `goc advance <child> --by <epic>` — but `goc advance <title> --by <advancer>` writes `advancer.advances += title`, so running the recipe verbatim produces `epic.advances: [children]`, the exact shape the next bullet nine lines down calls Never and that `goc validate` flags as BACKWARDS_EPIC_EDGE. The correct verb is `goc advance <epic> --by <child>`. The line ships identically in all six skill trees (templates, the two dogfood mirrors, and the three plugin payloads), so every consumer repo that follows the documented recipe builds the inverted edge on its first epic and inherits the broken value chain and the spurious attest failures the same bullet warns about."
status: open
stage: null
contribution: high
created: "2026-09-21T01:21:37Z"
closed_at: null
human_gate: none
advances:
  - doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them
advanced_by: []
tags: [bug, documentation, api-contract]
draft: true
definition_of_done: |
  - [ ] (replace with real criteria)
---

# shipped-epic-recipe-builds-the-backwards-edge-its-own-next-bullet-forbids

(write the design doc here)
