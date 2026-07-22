# Log

## 2026-07-22 — post-closure amendment: contract reversed

- This card closed 2026-05-05 on the exit-zero contract ("re-running
  `goc install` in an already-installed repo exits zero when it makes
  no changes"). The shipped behavior was later deliberately reversed:
  `goc install` on an already-installed repo now prints
  `already installed (…)` plus a `goc upgrade` hint and exits 1, and
  `tests/test_install.py` pins the refusal (the guard even runs ahead
  of the dry-run short-circuit for preview parity — see
  `dry-run-plan-promises-full-install-that-the-real-run-refuses-as-already-installed`).
- The reversal left no trail on this card, so the module docstring and
  this card's DoD kept documenting exit-zero — surfaced and fixed by
  [install-docstring-still-claims-second-install-exits-clean](../install-docstring-still-claims-second-install-exits-clean/),
  which rewrote the docstring to the refusal contract. This entry is
  the forward pointer required by the closure-is-not-frozenness
  convention.
