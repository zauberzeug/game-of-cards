## 2026-08-01T06:06:24Z — Closure

- **What changed**: two surfaces that told a consumer where a
  `.game-of-cards/` content stub gets delivered were brought back in step
  with the shipped skill tree.
  - `goc/templates/skills/audit-deck/SKILL.md:133-135` — the prose pointer
    ("For model-tier guidance … see `.game-of-cards/tooling-conventions.md`")
    became the injection the catalogue documents:
    `` !`cat .game-of-cards/tooling-conventions.md 2>/dev/null || true` ``.
    The code drifted, not the doc, so the code moved.
  - `goc/templates/game_of_cards/{domain-vocabulary,domain-examples,file-path-map,documentation-conventions}.md`
    — headers rewritten from the injected-stub boilerplate to "Reserved for
    project use. No goc-shipped skill inlines this file today …", matching
    the catalogue rows that already said `(reserved for project use)`.
  - `goc/templates/game_of_cards/README.md` § "Content stubs" — the blanket
    preamble ("Markdown files inlined verbatim into skill bodies at
    documented injection points"), which its own four reserved rows
    contradicted, now states what a reserved row means and names the guard.
  - The five dogfood copies under `.game-of-cards/` were verified
    byte-identical to the pre-fix templates (i.e. unauthored) before being
    refreshed — they are user-owned and not auto-synced.
- **Guard added**: `tests/test_readme_content_stub_catalogue_parity.py`, a
  sibling to the hook-table guard from
  `deck-readme-hook-catalogue-omits-refine-deck-hook`. It derives the
  delivered set from `goc/templates/skills/**/*.md` and holds three things
  to it: each stub header's injection claim, each catalogue row's "Inlined
  into" cell, and the dogfood copies' headers — over-claiming *and*
  under-claiming, in the template and the dogfood copy. That closes the
  direction the hook guard leaves open: the hook guard proves a shipped hook
  has a table row; this one proves a catalogued injection point exists.
- **Verification**: `reproduce.py` exit 1 → exit 0 (`5/6` header liars and
  `1` over-claiming catalogue row → `0` and `0`; seven injections → eight).
  The guard is non-vacuous — replayed against the pre-fix tree restored from
  `git show HEAD:…` for the two changed source files it reports 4 failures;
  post-fix all 4 tests pass.
- **Size cap**: the first draft of the injection lead-in pushed
  `audit-deck/SKILL.md` to 10,057 bytes and
  `tests/test_skill_body_size.py` failed it against its 10,000-byte cap.
  Trimmed to one line of lead-in prose (final 9,975); the `model: "opus"`
  example stays where the catalogue already carries it rather than being
  duplicated into the always-loaded hot path.
- **Mirrors**: `scripts/sync_plugin_assets.py` regenerated `.claude/`,
  `.codex/`, `claude-plugin/`, `codex-plugin/` and `openclaw-plugin/goc/`;
  `scripts/port_skills_to_openclaw.py` re-ported
  `openclaw-plugin/skills/audit-deck/`. Both `--check` modes clean. The
  OpenClaw port renders the new injection the same way it already renders
  the `hooks/audit-deck.md` one (leading `!` dropped — no pre-execution on
  that host).
- **Full suite**: 882 tests, green. `goc validate` exit 0. Card-language
  guard clean (696 cards).
- **Audit**: no project rubric configured
  (`.game-of-cards/hooks/pull-card.md` is an empty stub). The gate stayed
  `none` because each half is settled by the same tie-break rather than a
  taste call: the per-stub catalogue row is the specific statement of
  intent, the stub header is boilerplate copied across all six.
- **Family**: thirteenth instance of
  `doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them`,
  wired as an `advances` edge at filing time rather than filed as a
  duplicate umbrella.

## Closure verification (2026-08-01T06:07:04Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 6/6 ticked
- [x] log-md-closure-entry — '## 2026-08-01 — Closure' present
