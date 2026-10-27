## 2026-10-27T06:22:04Z — Closure

The verbs that write a card back now restore a `created` stamp that a wholesale rewrite of the
scaffold dropped, from the earlier of the card directory's birth time and the first commit of
README.md, and refuse without evidence; `goc new` asks for an in-place edit. Regression test
`tests/test_release_verbs_restore_a_lost_created_stamp.py` red before the change, green after; the
min/max mutation turns it red again. Full suite 1389 tests green, mirrors in sync.
