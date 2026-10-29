## 2026-10-23 — One more inverted reproducer observed

`goc-upgrade-drops-plugin-mode-claude-in-dual-claude-codex-installs/reproduce.py`
prints `DEFECT CONFIRMED` and exits 0 on main at `0a457032`. Noted while that
card was linked to a new root decision card. It was not fixed there, so it is
left for this card's EMPIRICAL sweep.

## 2026-10-25 — Inverted reproducer found and fixed on close

`goc-attest-mutates-log-md-on-already-closed-cards/reproduce.py` printed
`DEFECT REPRODUCED` and exited 0, and exited 1 once the defect was gone,
under a DoD that read `reproduce.py exits zero`. It was rewritten to the
0/1/2 contract when that card closed: exit 1 against the pre-fix engine,
exit 0 after. Unlike the 2026-10-23 instance, this one needs no sweep.

## 2026-10-28 — Two more inverted reproducers fixed on close

`goc-unadvance-claims-success-when-removing-a-non-existent-edge/reproduce.py`
and `goc-advance-claims-success-when-adding-an-already-existing-edge/reproduce.py`
both exited 0 while their defect fired. Each was rewritten to the 0/1/2
contract when its card closed (exit 1 against the pre-fix engine, exit 0
after), so neither needs the sweep.

The advance card is a variant the sweep should expect. Its DoD had been
worded to match the inversion — `reproduce.py exits non-zero (defect no
longer fires …)` — while its body said the DoD "flips this so exit 0 only
happens once the fix is in", so a sweep keyed on the DoD wording alone would
have read the pair as consistent. The DoD line now says `exits zero`. The
script spelled the inversion `sys.exit(0 if defect_fires else 1)`, which a
static scan for a literal `return 0` on the defect-present branch would not
match.

## 2026-10-28 — Third inverted reproducer in the family fixed on close

`goc-decide-accepts-empty-decision-and-because-arguments/reproduce.py` was
the same variant as the advance card: `sys.exit(0 if defect_fires else 1)`,
a DoD reading `reproduce.py exits non-zero (defect no longer fires …)`, and
a body saying the DoD "flips this". It was rewritten to the 0/1/2 contract
when the card closed (exit 1 against the pre-fix engine, exit 0 after), and
its DoD line now says `exits zero`.

A further shape for the sweep to expect: the inverted script never ran its
defect-absent branch, so it could not handle it. Against the fixed engine it
died on `out.splitlines()[0]` of an empty stdout (`IndexError`, exit 1)
before printing any verdict. Under its own inverted DoD that crash would have
read as "fixed", and under the 0/1/2 contract it reads as "fires". Either
way the exit code reflects the crash, not the defect, so a classification
run should treat a traceback as exit 2 (harness broken), whatever the code.

## 2026-10-28 — Fourth inverted reproducer in the family fixed on close

`goc-attest-silently-ignores-unknown-skip-names/reproduce.py` printed
`DEFECT REPRODUCED` and returned 0 on its defect-present branch — the plain
`return 0` shape a static scan would match — under a DoD that already read
`reproduce.py exits zero`. It was rewritten to the 0/1/2 contract when the
card closed (exit 1 against the pre-fix engine, exit 0 after), so it needs
no sweep.

One more shape for the sweep to expect: the inverted script recognised a fix
only by a phrase in stderr (`do not match any configured check` or
`unknown skip name`) from the fix sketch. The landed message words it
differently, so against the fixed engine it reported `typo accepted
silently: True` beside its `No defect` verdict. A reproducer that keys its
verdict on prose the fix had not yet written can misread the fix; the
rewrite keys on exit code, `ERROR:`, whether any check ran and whether
log.md changed.

## 2026-10-29 — Fifth inverted reproducer in the family fixed on close

`goc-move-renames-terminal-status-cards-without-any-guard/reproduce.py`
printed `DEFECT REPRODUCED` and returned 0 on its defect-present branch,
which is the plain `return 0` shape, under a DoD that read
`reproduce.py exits zero`. It was rewritten to the 0/1/2 contract when
the card closed (exit 1 against the pre-fix engine, exit 0 after), so it
needs no sweep.

The script also had a further shape for the sweep to expect: it had no
positive control. Its "No defect" branch fired whenever the closed card
was not renamed, for whatever reason. A fix that broke `goc move`
outright, or an argparse error, would have read as fixed. The rewrite
adds the live-card rename and the `--force` retitle as paired positive
cases, and treats either one failing as exit 2. A classification run
should flag a reproducer whose only fixed-branch evidence is the absence
of the defect.
