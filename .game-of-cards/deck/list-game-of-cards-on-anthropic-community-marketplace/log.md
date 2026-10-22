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
