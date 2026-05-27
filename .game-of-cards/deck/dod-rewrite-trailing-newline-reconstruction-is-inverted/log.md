## 2026-05-27 — disproved as a behavioral defect

Confirmed the inversion at `engine.py:2724` is real: `"\n".join(lines)`
never produces a trailing newline, and the appended `"\n" if not
dod_text.endswith("\n")` is the inverse of faithful restoration.

But it is masked and unreachable as an observable defect. The only caller
of `_apply_dod_rewrite` is `_apply_verdict_interactive` (`engine.py:2774`),
which writes via `emit_frontmatter` (`engine.py:2725`). That routes
`definition_of_done` through `_emit_block_field` (`engine.py:291`), whose
first action is `text = (value or "").rstrip("\n")` (`engine.py:246`),
normalizing away any trailing newline this line produces or drops. The
file on disk is byte-identical either way. Grepped 2026-05-27: no caller
consumes the value without that rstrip.

The MECHANICAL DoD item (drop `unverified` via a reproduce.py showing a
written-file difference) is unsatisfiable because no such path exists. The
one-clause correction is available as cheap hygiene but changes no on-disk
byte today, so it is not filed.

Closed `disproved` per the card's stated falsification recipe. Re-file if
the emit-time `rstrip("\n")` is removed/narrowed or a path serializes the
DoD value directly.
