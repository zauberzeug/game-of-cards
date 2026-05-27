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
