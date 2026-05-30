## 2026-05-30T03:18:42Z: decision deliberation archived

Archived from the README's `## Decision required` section by `goc decide` before it was replaced with the resolved `## Decision` block — README is the dashboard, log.md is the journal. This preserves the options and recommendation that produced the decision below.

The fix is structural — pick one approach and apply it to all three sites (and add a `goc validate`-time check that catches future redeclarations):

**Option A — drop the subparser duplicates.** The global versions already exist; deleting `p_qp.add_argument("--status", ...)`, `p_new.add_argument("--contribution", ...)`, and `p_triage.add_argument("--worker", ...)` removes the collision. Cost: `goc quality-pass --help` no longer lists `--status` in its own help section; users must read `goc --help` to discover it. Also breaks `goc quality-pass --status done` (sub-position form) — anyone with the flag in muscle-memory at that position hits an "unrecognized argument" error.

**Option B — `default=argparse.SUPPRESS` on the subparser flag.** Keeps the flag visible in `goc quality-pass --help`, but tells argparse not to write the dest if the user did not pass the flag. The parent's value (or its `None` default) survives. Smallest behavioral change; the help line for the subparser still shows the flag and its choices but the `(default: open)` annotation has to come from elsewhere (e.g. the global `--status` default).

**Option C — post-parse merge.** Leave both declarations alone; after `parse_args` returns, run a small reconciliation pass that resolves the conflict (e.g. parent's value wins iff non-default). Most flexible but most invisible — readers don't see the resolution in the parser definition.

**Option D — distinct dests.** Rename the subparser flag's dest (`status_flag_sub`) and have the command handler reconcile (`args.status_flag_sub or args.status_flag`). Verbose but explicit; trades parser conciseness for handler clarity.

Recommendation: **Option B** for the three current sites + a `goc validate` (or unit-test) tripwire that fails when any subparser redeclares a dest that also lives on the parent without `default=argparse.SUPPRESS`. The tripwire prevents drift, and Option B preserves both help-page surfaces and back-compat with users who pass the flag in either position. Also wire `_cmd_quality_pass` to honour `args.done_flag` so the global `--done` shortcut is no longer a no-op for that subcommand.


## 2026-05-30T14:00:21Z: decision recorded

Option B: set default=argparse.SUPPRESS on the three redeclared subparser flags (--status on quality-pass, --contribution on new, --worker on triage) so the parent value survives when unpassed; add a goc validate (or unit-test) tripwire that fails when any subparser redeclares a parent dest without SUPPRESS; wire _cmd_quality_pass to honour the global --done shortcut — smallest behavioral change that preserves both --help surfaces and back-compat with the flag passed in either position, while the tripwire prevents the collision from drifting back in across the three sites and any future one. Gate decision → none.
