## 2026-10-31T05:46:44Z — Staleness re-check

ee682d87 (closing
[closure-log-attestation-misfires-across-utc-midnight](../closure-log-attestation-misfires-across-utc-midnight/))
rewrote the regex this card cites. It did not fix this card's defect.

- **Still fires.** The em-dash separator is unchanged. On the engine after
  ee682d87, `## 2026-06-29 - Closure` (ASCII hyphen) returns
  `(False, "no '## YYYY-MM-DDTHH:MM:SSZ — Closure' section")`. The miss
  message no longer names a date, but it still reports a present heading
  with the wrong punctuation as a missing section, so the complaint about
  the diagnostic stands.
- **What moved.** The check no longer compares the heading's date with
  attest's clock. It matches `_CLOSURE_HEADING_RE` (`goc/engine.py`), any
  well-formed `## <stamp> — Closure` heading anchored at a line start, and
  names the latest. So option 1 here would now loosen only the separator.
  Option 2's near-miss probe would have no date to pin either.
- **Stale anchors.** The Location excerpt, and the pattern `reproduce.py`
  copies instead of calling the engine, are the pre-ee682d87 date-bound
  regex. The reproducer still gives the right verdict on the hyphen, but
  it tests that copy, not the shipped check.
