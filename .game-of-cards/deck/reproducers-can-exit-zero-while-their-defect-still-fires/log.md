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
