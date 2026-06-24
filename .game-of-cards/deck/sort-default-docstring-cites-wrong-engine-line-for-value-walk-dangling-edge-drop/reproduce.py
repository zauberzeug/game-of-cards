#!/usr/bin/env python3
"""Reproduce: sort_default's docstring cites the wrong engine.py line.

The docstring cross-references "the value walk's dangling-edge drop" with a
hardcoded `engine.py:NNNN` line number. That number drifted out of sync — it
points at `_would_create_advance_cycle`, not at the value walk's actual
dangling-edge prune in `compute_values`'s `value_for`.

Before the fix: a hardcoded `engine.py:NNNN` citation survives in the docstring
and it does not name `value_for`  -> prints FAIL and exits 1.
After the fix: the line-number citation is gone and the docstring names the
symbol -> prints OK and exits 0.
"""
import re
import sys

from goc.engine import sort_default

doc = sort_default.__doc__ or ""

hardcoded = re.findall(r"engine\.py:\d+", doc)
names_symbol = "value_for" in doc

if hardcoded or not names_symbol:
    print("FAIL: sort_default docstring dangling-edge cross-reference is broken")
    if hardcoded:
        print(f"  hardcoded line citation(s) still present: {hardcoded}")
    if not names_symbol:
        print("  docstring does not name the value-walk symbol `value_for`")
    sys.exit(1)

print("OK: docstring cites `value_for` symbolically, no hardcoded engine.py:NNNN line")
sys.exit(0)
