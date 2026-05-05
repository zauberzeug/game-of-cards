---
title: create-project-website-explanatory-illustration
summary: "Create the project-website illustration that explains Game of Cards visually. This is not a generic flow diagram for README prose; it is a session-built visual asset for the project site, and the session should decide the metaphor, content density, style, and export format."
status: open
stage: null
contribution: medium
created: 2026-05-04
closed_at: null
human_gate: session
advances: [build-game-of-cards-project-website]
advanced_by: []
tags: [story, documentation]
definition_of_done: |
  - [ ] Interactive design session held for the illustration concept, not implemented autonomously from this card alone
  - [ ] Illustration explains Game of Cards on the project website at first-read speed
  - [ ] Visual content covers cards, gates, autonomous pull, and DoD closure without turning into a CLI reference diagram
  - [ ] Asset format chosen and documented (for example generated bitmap, hand-authored SVG, or web-native animated/interactive scene)
  - [ ] Illustration is integrated into the project website card's implementation surface
  - [ ] Text alternative or caption exists so the idea is understandable without the visual
  - [ ] `uv run goc validate` passes
---

# Create the project website explanatory illustration

## Why

The previous "flow diagram" phrasing was too narrow. The desired artifact is a project-website illustration: a first-viewport or near-first-viewport visual that helps visitors understand what Game of Cards is and why the card/deck/gate model matters.

## Location

The illustration belongs on the project website tracked by `build-game-of-cards-project-website`. README reuse is optional and should not drive the asset.

## Session required

This must be built in a session. The important choices are visual and positioning choices, not just technical rendering choices:

- What metaphor explains Game of Cards best without making it look like yet another task board?
- How much detail belongs in the illustration versus nearby copy?
- Should the asset be static, animated, or lightly interactive?
- Should the final form be web-native, SVG, or generated bitmap?
- Which parts of the methodology are mandatory to show: cards, gates, autonomous agents, DoD, value graph, or GitHub/plugins?

The implementation should wait for that session rather than turning this into a Mermaid-style process chart.
