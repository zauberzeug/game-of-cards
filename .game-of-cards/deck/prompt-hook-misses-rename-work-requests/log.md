## 2026-05-30 — regression / forward pointer

The fix shipped by this card was orphaned by a subsequent file rename:
commit `33d000a` (2026-05-05) created `deck_prompt_router.py` as a fresh
copy of the older `user-prompt-submit.py`, then commit `14864cc` added
the rename/update/change/delete/remove/move verbs to the *orphaned*
`user-prompt-submit.py`. Commit `8277962` (2026-05-09) deleted that
orphan, taking the fix with it.

Forward pointer:
`.game-of-cards/deck/deck-prompt-router-missing-rename-update-change-delete-edit-verbs/`
restores the missing verbs via a shared `WORK_VERBS` constant (the
meta-fix shape that prevents the next single-site verb addition from
falling out of sync with the others).
