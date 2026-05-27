## 2026-05-27T01:05:42Z: filed (audit-deck)

Surfaced by an audit hunt against under-audited engine seams. Third sibling
of the regex-replacement-template family (engine.py:336 and install.py:222
already fixed and closed). Reproduced both the crash variant (`\p`) and the
silent group-reference variant (`\1`) via reproduce.py before filing.

Sibling sweep: grepped all `.sub(` call sites in engine.py / install.py /
cli.py. Only engine.py:356 passes a dynamic (user-derived) replacement
template; install.py:169 and install.py:183 use static literals (`"\n"`,
`""`) and are safe. Confirmed 3rd instance, not a 4th — no architectural
meta-fix warranted; the per-site `lambda _:` fix matches the family.

## 2026-05-27: fixed (pull-card)

engine.py:356 switched to `DECISION_REQUIRED_RE.sub(lambda _: block, ...)`,
mirroring engine.py:336. reproduce.py now exits 0 (both variants verbatim).
Empirical confirmation: ran a real `goc decide --decision 'Use C:\path'
--because 'go \1 ahead'` against a parked card in an isolated temp repo —
recorded both strings literally, no crash, no group expansion, gate lowered.

Full sibling re-sweep (broader than the filing-time pass): the two
`_move_text_rewrite` sites (engine.py:3945 `\g<1>{new}` and engine.py:3952
bare `new`) DO route dynamic text into a replacement template, but `new` is
a card slug constrained to `[a-z0-9-]` (engine.py:3555 validator), so no
backslash escape can reach them — not exposed. install.py's dynamic-content
sites (222, 884, 1040) already use the opaque `lambda _:` form. No unfixed
`pattern.sub(<dynamic-template>, ...)` site remains.

## 2026-05-27T01:09:41Z — Closure

- **What changed**: engine.py:356 — `DECISION_REQUIRED_RE.sub(block, ...)` → `.sub(lambda _: block, ...)`, mirroring engine.py:336.
- **Verification**: reproduce.py exits 0 (2/2 variants verbatim); real `goc decide --decision 'Use C:\path' --because 'go \1 ahead'` recorded both strings literally with no crash / no group expansion.
- **Audit**: PASS — no principle touched, mechanical fix (regex-template opacity, matching the shipped family idiom).
- **Project impact**: n/a
- **Tests**: no pytest suite; goc validate green, plugin-asset sync green.
- **Bundled with**: none

## Closure verification (2026-05-27T01:10:46Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-05-27 — Closure' present
