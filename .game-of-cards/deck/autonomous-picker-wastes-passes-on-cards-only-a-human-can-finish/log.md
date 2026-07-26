## 2026-07-22 — filed from a downstream drain observation

Filed after the Zoe App drain repeatedly auto-pulled a verify-first card
(`conversations-send-and-receive-file-attachments`) whose DoD needs a
human to trigger a production `chat.send` with an attachment plus a
live-device check — work no unattended agent may do. The card was born at
`human_gate: none`, so the picker kept offering it; ~2–3 passes were spent
before the Zoe App drain's own release-attempt counter
(`_count_release_attempts` / `release_claim_if_stuck` in its `tool/_lib.sh`)
tripped and escalated it to `human_gate: session`.

Two observations drove the filing: (1) that escalation net lives in a
downstream drain wrapper, so every other `goc` consumer gets no backstop;
(2) even with the net, the first passes are wasted — the DoD carried the
human-only signal (`EMPIRICAL:` items) at creation, so detection at
`goc new` / `goc validate` could prevent the waste rather than bound it.

Scope-checked against the closest open card,
`aggregation-epics-head-block-the-autonomous-pull-queue` (open, gate
decision): same symptom (picker offers an unclosable card), different root
cause (pure-aggregator with no work of its own vs. real work only a human
can execute). Kept distinct; cross-linked in the README. Filed
`human_gate: decision` because the fix relocates a behaviour from downstream
wrappers into the engine's gate lifecycle and a human should pick the
mechanism (A/B/C/D) first. Left uncommitted for review.
