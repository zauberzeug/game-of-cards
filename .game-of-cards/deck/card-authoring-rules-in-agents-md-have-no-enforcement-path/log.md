## 2026-07-27 — Filed from the Stop-hook pattern check

The refine-deck pass that renamed
`openclaw-plugin-skills-erzwingen-mehrfach-reads-pro-session` treated it as a
one-off mechanical fix. The Stop-hook pattern check asked whether the change
touched something broader, and it did: the rename was possible only because a
human-or-agent read the title, and nothing in the toolchain could have found
it.

Dedup before filing. `goc --status all` grepped for `title` / `jargon` /
`antipattern` / `quality-pass` returned 19 cards; all are about the *mechanics*
of the guard (it crashes, it is bypassed by `move`, it shows a raw regex error,
it mutates terminal cards) and none about what the guard does not cover.
Grepping deck bodies for "English only" / "non-English" returned exactly one
hit — the rename log entry written minutes earlier in this same pass. No root
card exists, so this is a filing and not a connection.

Two adjacent cards are cross-referenced in the body rather than edged, and the
body says explicitly why each is adjacent rather than parent:
`doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them`
(different root: tree-derived claims, not authoring conventions) and
`static-source-guards-never-prove-they-can-catch-an-offender` (not a parent,
but its requirement is inherited into DoD box 3).

Scope kept deliberately narrow. The live instance count is one, on one of the
three unguarded rules; the other two were audited during this pass and are
clean. That is well under the four-instance threshold `Skill(audit-deck)` uses
for filing an architectural meta-fix, so this is filed as an ordinary
`contribution: low` gap card and not as a family umbrella. The body states the
instance count plainly so a later reader can judge whether it is worth the
false-positive budget a language heuristic would spend.

Gate left at `none` per the unattended-pass instruction; the scope and surface
picks are carried by the first DoD box.
