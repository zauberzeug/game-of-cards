## 2026-11-02T01:02:06Z — Same root cause found in the runtime hooks' opt-in gate

- **Finding**: the opt-in gate added by `runtime-hooks-fire-in-repos-that-never-opted-in` (2026-10-24) treats a bare `deck/` directory as a GoC deck. Its tests pin the legacy-`deck/` reminder on purpose. Three sites carry the check: `goc/templates/hooks/deck_prompt_router.py:225-228` (`_has_deck`: `return (project_dir / ".game-of-cards" / "deck").is_dir() or (project_dir / "deck").is_dir()`), `goc/templates/hooks/deck_session_start.py:424-430`, and OpenClaw's `hasDeck` at `openclaw-plugin/index.ts:569-573`.
- **Reproduced** (2026-11-02, scratch git repo with no `.game-of-cards/`, holding only `deck/intro/README.md` and `deck/config.yml`):
  - Piping `{"prompt": "please fix the typo on the intro slide", "cwd": "<repo>"}` into `deck_prompt_router.py` printed the full `[Game of Cards | runtime active]` reminder.
  - `goc` printed `No cards match (status: open).` and no missing-deck notice.
  - `goc new fix-intro-slide-typo --summary "Fix typo."` warned `using legacy deck/ location` and created `deck/fix-intro-slide-typo/` beside the slides.
- **Why it is recorded here, not filed**: same root cause, the deck-identity predicate. The engine and the hooks fail on the same input and are fixed by the same decision. The hooks import nothing from the engine, though, so a DoD line now makes sure the decision reaches them. The body has a pointer paragraph at the end of `## Decision required` and a Location bullet. No option text changed and the gate stays `decision`.
- **Surfaced by**: `audit-deck` run, 2026-11-02.
