## 2026-05-30 — pin reversed to floating `opus` alias

The "explicit reproducible pin over auto-rolling alias" preference
recorded in this card's "Out of scope" section was reversed. After Opus
4.8 shipped, the pinned `claude-opus-4-7` literal meant the autonomous
loops silently ran a stale model between releases until a human edited
the YAML. Owner's call: prefer "always strongest" over a self-chosen
version string in run logs (the resolved id still appears per-turn in
each run's logs, so reproducibility is reported rather than lost).

Both `pull-card.yml` and `audit-deck.yml` now pass `--model opus`.
Follow-up card: float-opus-alias-on-autonomous-github-workflows. This
card stays `done` — its work shipped and was correct for its window.
