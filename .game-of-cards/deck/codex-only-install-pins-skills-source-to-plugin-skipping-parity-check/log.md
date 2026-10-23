## 2026-05-30: Human directive — verify before deciding

Decision-walk verdict (Rodja): do **not** pick `skills_source`
semantics yet. The card is UNVERIFIED; run the falsification recipe
first —

1. `goc install --agents codex` (no claude) into a fresh temp repo.
2. Read `.game-of-cards/config.yaml`; confirm `skills_source: plugin`.
3. Delete a `.codex/skills/<verb>/` dir to simulate drift; run the
   parity validator; confirm it returns `[]` (drift unreported).

If it disproves → flip to `disproved` with evidence (and lower this
gate as part of that closure). If it confirms → re-surface the
semantics fork (plugin = Claude-specific + codex→vendored, vs.
per-agent skills_source tracking) for a decision then.

Gate intentionally left `decision` — the semantics pick is deferred,
not made.

## 2026-08-31 — refine-deck: stale park re-checked, kept

96 days parked. Re-read against HEAD: the pin is unchanged —
`chosen_source = "vendored" if "claude" in local_skills_agents else "plugin"`
(`goc/install.py:1616`; the body's cite was repaired from `:1597` to that
number by this pass). A codex-only install therefore still writes
`skills_source: plugin`.

No `reproduce.py` built this round. The recipe needs a full `goc install`
into a scratch repo with a codex-only agent set, then a deliberate template
divergence under `.codex/skills/`, then `goc validate` — three stateful
steps whose failure modes overlap with the sibling card
`codex-install-from-plugin-payload-vendors-skills-and-crashes-on-omitted-templates-skills`.
Building one fixture that serves both is the efficient move and is worth
more than the remaining budget of a hygiene pass.

## 2026-10-07T04:45:00Z — Cross-linked to the Codex install-default decision

Filed `codex-install-defaults-to-plugin-path` (gate decision), the Codex install-default follow-up that
`claude-install-defaults-to-plugin-path` promised. It governs this card's
question, so a `## Related decision` pointer was added here. No edge was added,
because a governing decision gets a shared tag and no edge.

## 2026-10-22T05:56:37Z: decision recorded

Lower the gate: write the reproduce.py next, which needs no human input — Bulk rule approved by the maintainer in a human session on 2026-10-22: a gated card with no written question and a mechanical fix drops to gate none. Gate decision → none.

## 2026-10-23 — pull-card: confirmed, gate raised back to decision

Ran the falsification recipe as `reproduce.py`, which exits 1 on main at
`fc791c43`. A codex-only install pins `skills_source: plugin` beside a real
vendored `.codex/skills/` with no Claude plugin on the host. After
`.codex/skills/pull-card/` is deleted, `validate_skill_dir_parity()` returns
`[]` and `goc validate` exits 0. With the pin flipped to `vendored`, the same
check reports `.codex/skills: missing skills ['pull-card']`. DoD items 1 and 2
are ticked, and `unverified` is dropped.

The defect is wider than filed. The mixed `--agents claude,codex` install and
the codex-only `--local-skills` install pin `plugin` too and lose the same
check. In the mixed install the pin is correct for Claude, so the original
DoD item 4 ("fix the pick at install.py and the upgrade re-pin guard") could
not have fixed that case. The item is rewritten in place as an option-neutral
TDD + MECHANICAL pair whose acceptance test is reproduce.py exiting 0. Two
more facts were checked by hand. For a legacy repo with no pin, the Codex
check runs or not depending on whether the validating host has the Claude
plugin (exit 1 without it, 0 with it). Plain `goc upgrade` repairs the
deleted directory, but the drift message's `--keep-local-skills` advice,
combined with `--agents claude,codex`, vendors Claude and re-pins `vendored`.

Per the 2026-05-30 directive, a confirmed defect re-surfaces the semantics fork
for a decision. The project's pull-card consultation hook is empty, so the gate
goes from `none` back to `decision`, with a `## Decision required` section that
offers Option A (the key is Claude-only and the vendored Codex tree is always
checked) and Option B (a per-host key), and recommends A. No fix was applied.
The directive reserves this pick for the maintainer, and the options diverge
beyond the validator: B changes the config format, install and upgrade. B is
also what `codex-install-defaults-to-plugin-path` needs if it moves Codex to
the plugin, so the two decisions belong together. The stale
2026-10-22 `## Decision` block left the README because its "write the
reproduce.py next" is done and its text stays in the entry above. Leaving it
would also have made `extract_resolved_decision_text`, which reads the first
`## Decision` match, return the stale text after the next `goc decide`. The
claim is released (`active → open`) so the card parks like every other gated
card.
