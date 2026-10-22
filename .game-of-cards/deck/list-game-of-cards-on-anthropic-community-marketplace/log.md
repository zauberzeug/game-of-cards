## 2026-05-09: submission opened, awaiting Anthropic review

Rodja submitted the plugin via the form at `clau.de/plugin-directory-submission` (channel decided 2026-05-08, see body's "Decisions" section). DoD ticked: items 2 (channel decision), 4 (version stays pre-1.0 0.0.6 per the same decision block), 5 (submission opened today).

Card stays `active`. Next state transition is driven by Anthropic's reviewer:
- **If accepted/merged**: tick item 6 → tick item 7 (post-merge documentation updates) → `goc done`.
- **If review feedback requires changes**: log the feedback here, address as appropriate (likely on prereq cards rather than this one), iterate.

Open dependencies that don't block submission but should land before the listing goes wide:
- Item 1 (hard prereqs) — `add-readme-to-claude-code-plugin` is gate=session awaiting Rodja's sign-off on the rendered README.
- Item 3 (fresh-machine smoke test) — captured as written reproduction would strengthen the listing's credibility; Anthropic reviewer may or may not request it.

Submission URL: pending capture. The worker field's "captures the URL of the submission" sub-promise is a follow-up; not blocking. If Rodja can paste the submission URL/ID in a follow-up log entry, future readers won't need to dig through email/forms to find it.

## 2026-10-22T05:14:48Z: decision recorded

Close: the listing exists; move the re-pin, the fresh-machine smoke and the docs update into a follow-up card — The maintainer decided in a human session on 2026-10-22; GitHub issue #6 from the community-marketplace maintainers confirms game-of-cards is listed, but the entry is frozen on 4e4c5a1, so the remaining work waits on a re-pin rather than on acceptance. Gate decision → none. Status active → open — the claim parked behind the gate is released, so the next pull-card claims the card per this decision.

## 2026-10-22T05:16:34Z — Closure

- **What changed**: no code — DoD 1 ticked (`add-readme-to-claude-code-plugin` and all eleven `advanced_by` cards closed), DoD 6 ticked (listed per GitHub issue #6), DoD 3 (fresh-machine smoke) and DoD 7 (install docs) moved to the new card [`community-marketplace-pin-is-frozen-on-a-commit-that-fails-plugin-validation`](../community-marketplace-pin-is-frozen-on-a-commit-that-fails-plugin-validation/), whose first step is re-submitting via `clau.de/plugin-directory-submission` once 0.0.29 is published. The stale "awaits sign-off" mentions are corrected and an "## Outcome" section records the frozen pin.
- **Verification**: issue #6 body ("we maintain the Claude Code plugins community marketplace, where **game-of-cards** is listed"); issue #8 (2026-10-21) reports the pin at `4e4c5a1`, behind v0.0.28; `uv run goc validate` exit 0.
- **Audit**: no rubric configured; mechanical fix.
- **Project impact**: the listing is recorded as achieved; the remaining, re-pin-dependent work has its own card instead of keeping this one active indefinitely.
- **Tests**: no code touched; the full suite runs at the end of this batch.
- **Submission reference**: still not captured in this card (see the 2026-05-09 entry); the follow-up card records the re-submission reference.

## Closure verification (2026-10-22T05:16:34Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — all 11 closed
- [x] dod-100-percent — 8/8 ticked
- [x] log-md-closure-entry — '## 2026-10-22 — Closure' present
