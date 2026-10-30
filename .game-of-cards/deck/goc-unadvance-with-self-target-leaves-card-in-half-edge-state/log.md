## 2026-10-28: the no-self-edge variant is now refused by the missing-edge guard

`goc-unadvance-claims-success-when-removing-a-non-existent-edge` closed:
`_cmd_unadvance` now loads both cards and refuses (exit 2, nothing written)
when neither `title.advanced_by` lists the advancer nor `advancer.advances`
lists the title. For a self-target that changes the first test case in
`## Fix`: `goc unadvance foo --by foo` on a card with empty lists now exits 2
with `ERROR: cannot remove foo → foo: no such edge — …`, not a success line.

The on-disk self-edge variant this card is about is unchanged: with
`foo.advanced_by: [foo]` a half is listed, so the guard lets the call through
to `_mutate_pair`, which still leaves `advances: []` / `advanced_by: [foo]`
(re-checked 2026-10-28). Both options stay open. Option A's self-target guard
would sit ahead of the new check and give both variants its own message;
Option B can reuse the shared `_refuse_invalid_input` helper if it refuses
rather than handles child == parent.

## 2026-10-30: re-checked — the self-edge variant still fires; the reproducer's exit code is inverted

Re-ran `reproduce.py`: with `advances: [foo]` / `advanced_by: [foo]` on disk,
`goc unadvance foo --by foo` still exits 0 and leaves `advances: []` /
`advanced_by: [foo]`. The script returns 0 on its `DEFECT FIRES` branch and 1
once the defect is gone, the reverse of this card's TDD item ("reproduce.py
exits zero — … no longer leaves the card in a half-edge state"), so swap its
return codes when implementing. The convention is tracked by
`reproducers-can-exit-zero-while-their-defect-still-fires`.
