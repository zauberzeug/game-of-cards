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

## 2026-11-16T02:03:00Z — Cites re-anchored by their prose

`engine.py:7206` (summary) and `goc/engine.py:7206` (body) → `:6603`, the
`all_check_names = {c["name"] for c in layer_2_checks} | …` line the body
quotes. Both were written correctly on 2026-06-12 (`5ee8150e`, then line
4266). The 2026-08-10 pass (`69e1e4f2`) read that number at the card's
creating commit `fb3c509a`, where line 4266 was
`print("Structural problems requiring human review:", file=sys.stderr)`,
and moved both cites onto that print; every pass since anchored on its own
rewrite and tracked the print faithfully. The `:4283` / `:4296` numbers
in the same body sentence are bare continuations no pass can see and are
left as they are.
