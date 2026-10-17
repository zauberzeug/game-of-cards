## 2026-06-12 — supporting evidence: nameless check entry crashes attest with raw KeyError

An audit round surfaced a third symptom of the same root cause (config-supplied
check dicts are shape-unvalidated): a `layer_2_project_dod` entry missing the
`name` key crashes `goc attest` at `engine.py:4266` with an unhandled
`KeyError: 'name'` traceback (exit 1) before any check runs, instead of the
clean `ERROR: … exit 2` convention used for other config problems. Verified in
a /tmp sandbox deck. Recorded as a new "Third symptom" subsection in the README
dashboard and a new DoD item (shape error for missing `name`/`kind`/`cmd`),
rather than filed as a separate card — the pending decision's load-time
validation branch covers it.

## 2026-10-17T05:06:12Z — supporting evidence: malformed list-shaped cmd crashes too

While fixing the sibling card
`attest-automated-check-crashes-with-traceback-when-its-command-cannot-run-or-prints-undecodable-bytes`,
two more symptoms of this card's root cause (no shape gate on check
entries) were confirmed by calling `_run_automated_check` directly: a
non-string `cmd` element (`["sleep", 5]`) raises `TypeError`, and an
empty `cmd: []` raises `IndexError`, both from `subprocess.run`. The
README's third-symptom section now records them and notes which
decision option covers them (A does; B needs an extra element check).
The sibling card fixed exec failures (EACCES, ENOEXEC) and
undecodable output for a well-shaped `cmd`. That fix adds an
`except OSError` branch after the `FileNotFoundError` one and leaves
the `command not found: {cmd[0]}` message for this card's decision.
