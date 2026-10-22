## 2026-10-07T04:45:00Z — Cross-linked to the Codex install-default decision

Filed `codex-install-defaults-to-plugin-path` (gate decision), the Codex install-default follow-up that
`claude-install-defaults-to-plugin-path` promised. It governs this card's
question, so a `## Related decision` pointer was added here. No edge was added,
because a governing decision gets a shared tag and no edge.

## 2026-10-07T04:50:00Z — Staleness re-check

`27db384e` rewrote the `_should_use_local_skills` docstring quoted in § Hypothesis
and dropped its "(no plugin yet)" premise. The quoted comment is now stale, but
the code under it, `return agent != "claude" or local_skills`, did not change.
The vendoring-from-plugin-engine path this card hypothesizes is still reachable,
so the hypothesis stands.
