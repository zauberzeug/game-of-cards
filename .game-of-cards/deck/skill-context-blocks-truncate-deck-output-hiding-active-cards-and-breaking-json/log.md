
## 2026-08-11 — connected to the closed truncation family

Pattern-generalization check on filing: the "view bounds output without
reporting what it hid" shape already has four instances in the deck, all
`done`, all at the engine-renderer layer (board `--max-rows`, board worker
label, both triage previews). No root/umbrella card exists for it.

Filing a fifth umbrella over four already-closed cards would coordinate
nothing, so this card connects by cross-reference instead — see
`## The closed family this instance belongs to`. No `advances` edge: every
sibling is terminal, so an edge would carry no value flow, and the deck's
guidance for governing clusters is a shared reference rather than an edge.

The connection is load-bearing for the open decision, not decoration: four
prior instances were all resolved the same way (bound *and* report), which
is the strongest available evidence for Option 1.

## 2026-10-09T04:50:42Z — Live instance: the cut row was the one an agent could act on

The `pull-card` soft-lock table (`goc --status active -v | head -20`)
rendered six of this repo's seven active cards. The one it cut,
`engine-comments-claim-unflagged-placeholder-cards-count-as-drafts`, was
the only gate-free, unimpeded card in the list: an orphaned claim from the
previous day's run. The six it showed were all parked or impeded, so no
agent could act on them. The table sorts by value, the high-value parked
cards come first, and the low-contribution fix-through claims that
sessions orphan fall to the bottom where `head` cuts. Only the
SessionStart hook named the card. The contradiction between that hook and
the soft-lock rule is filed separately as
[session-start-hook-says-resume-active-cards-that-pull-card-says-to-leave-alone](../session-start-hook-says-resume-active-cards-that-pull-card-says-to-leave-alone/).
