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
