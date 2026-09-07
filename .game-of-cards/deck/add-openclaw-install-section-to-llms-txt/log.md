## 2026-08-01 — forward pointer: the pre-publish framing was never flipped

Post-close evidence. This card's own "Notes" section required the OpenClaw
section to be "honest about state" and to move from the source-build path to
the registry install once publishing landed. The section shipped 2026-05-09 in
its pre-publish form; ClawHub began serving `game-of-cards` on 2026-05-10 and
now tracks the current release (`latestVersion` 0.0.27). Nothing owned the
transition, so `site/llms.txt` told LLMs the channel was still pending for ten
releases while README.md, ABOUT.md, goc.md and site/index.html all advertised
it as live.

No re-open: the card's DoD was satisfied as written on the day it closed.
Corrected under `llms-txt-still-presents-the-clawhub-install-as-unpublished`,
which also lands `tests/test_llms_txt_install_channels.py` so the next
publish-state caveat that outlives its publish fails CI.
