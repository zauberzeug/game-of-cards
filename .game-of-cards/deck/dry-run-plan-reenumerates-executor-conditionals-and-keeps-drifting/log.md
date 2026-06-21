## 2026-06-21 — 4th instance added (repair-edges)

Added [repair-edges-dry-run-overstates-fixable-edges-that-apply-refuses](../repair-edges-dry-run-overstates-fixable-edges-that-apply-refuses/)
to "instances so far" and wired its `advances` edge into this card's
`advanced_by`. First instance outside the install/upgrade/migrate cluster:
`_cmd_repair_edges`'s dry-run classifies half-edges against one original
snapshot while `--apply` reloads per edge, so the preview overstates the
repairs apply will make. Updated the summary count (three → four; three
fixed, one open). The architectural decision (mechanism A/B/C) is unchanged
and still pending on this card.
