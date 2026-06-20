## 2026-06-20T05:10:00Z — Filed (generalization meta-fix)

Filed by the pattern-generalization check after closing the json instance
(render-json-shows-awaiting-advisory-on-terminal-cards). Consolidates the
terminal-status liveness gate for the dependency advisory, which is
reimplemented in board card_cell, render_table, and render_json — two of
the three drifted into shipping bugs. Gate none: the extraction shape is
determined; left in the queue rather than fixed through because it spans
three call sites.
