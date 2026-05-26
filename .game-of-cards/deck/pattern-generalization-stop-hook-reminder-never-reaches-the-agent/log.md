## 2026-05-26 — filed (audit-deck)

Found during an audit-deck pass. The pattern-generalization Stop hook
emits its reminder via `print()`+`return 0`. For a Claude Code Stop
event, exit-0 stdout reaches only the user's transcript view, never the
model — so the nudge has been inert for its stated purpose since it
shipped.

`reproduce.py` output (exit 1 = defect fires):

```
exit code .................. 0
reminder on stdout ......... True
reminder on stderr ......... False
stdout is JSON block ....... False

FAIL: reminder is on exit-0 stdout — the one channel a Stop hook
      CANNOT use to reach the model. The agent never sees it; the
      reminder only appears in the user's transcript (Ctrl-R) view.
```

Filed at `human_gate: decision` — the fix (block-the-stop) reverses the
originating card's deliberate "reminder-only, no-block" A+B+A decision,
so a human must pick block / drop / re-document. See README `## Decision
required`.
