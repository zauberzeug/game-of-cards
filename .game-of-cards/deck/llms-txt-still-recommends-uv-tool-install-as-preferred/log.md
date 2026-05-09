# 2026-05-09 — implementation done, blocked on validate-drift bug

The one-comment edit to `site/llms.txt` is applied: lines 58-59 now
read

```
pipx install game-of-cards
# or: uv tool install game-of-cards
```

DoD items 1, 2, 3 are satisfied by the edit alone. Item 4 (`uv run
goc validate` passes) cannot be ticked: validate fails at HEAD with
`plugin mirror drift: goc vs openclaw-plugin/goc: templates/hooks
(only in goc)`. The drift was introduced upstream by commit
`8277962` and has nothing to do with this card. Filed as
`validate-plugin-mirror-fails-when-openclaw-omits-hooks-dir`
(advanced_by). Once that lands, validate will pass, item 4 ticks,
and this card closes.
