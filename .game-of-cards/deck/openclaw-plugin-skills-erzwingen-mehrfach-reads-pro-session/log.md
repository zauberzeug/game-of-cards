
## 2026-07-18 — Filed

Filed from a consuming deployment's latency analysis (trajectory-JSONL category split,
2026-07-16/17): GoC skill bodies were among the top orientation-read targets, re-read
150-200x/day across three path variants; the goc-owned AGENTS.md marker block (~4.1k chars)
additionally crowds the consumer's bootstrap char budget (OpenClaw trims at 20k). Scoped as
upstream work because both the marker block (regenerated wholesale on `goc upgrade`) and the
shipped skill bodies are goc-owned — consumers cannot durably fix them locally.

## 2026-07-18T12:58:15Z: decision recorded

Implement all three levers combined: slim AGENTS_GOC.md to a lean pointer block, audit skill cores for one-read self-sufficiency, and serve OpenClaw skill bodies via a tool-side skill verb — Maintainer selected all three scope options; OpenClaw SDK verifiably offers no sandbox location rewriting, so tool-served bodies are the only plugin-side fix. Gate decision → none.
