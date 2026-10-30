## 2026-10-30: re-checked — still fires

`reproduce.py` against the current code: `goc wait --clear` combined with
`--reason resource --until 2027-06-30` still exits 0, prints `waiting overlay
cleared …` and leaves no `waiting_*` key, so the requested set is dropped.
`_cmd_wait` reads neither `--reason` nor `--until` on its `--clear` branch.
