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
