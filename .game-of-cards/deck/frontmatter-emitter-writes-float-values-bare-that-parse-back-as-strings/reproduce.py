#!/usr/bin/env python3
"""Float frontmatter values must not silently round-trip to strings.

Before the fix, `_yaml_inline` emitted a Python `float` bare via `str(value)`
(`3.14`), but the vendored parser has no float recognizer, so it read back as
the string `"3.14"` — silent type-loss.

Resolution (a): the emitter refuses floats at the serialization boundary. No
card frontmatter field is a float, so advertising a type the parser cannot
round-trip is the bug; refusing loud is the fix.

Exit 0 = emitter refuses floats AND int / float-looking-string still behave.
Exit 1 = a float silently survives emit (defect present).
"""
import sys

from goc.engine import FrontmatterError, emit_frontmatter, parse_frontmatter

failures = []

# 1. A genuine float must be refused, not silently coerced to a string.
try:
    emit_frontmatter({"title": "x", "k": 3.14}, body="body\n")
    failures.append("emit_frontmatter accepted a float instead of refusing it")
except FrontmatterError:
    pass  # expected
except Exception as exc:  # pragma: no cover - any other error is a regression
    failures.append(f"unexpected error type for float emit: {type(exc).__name__}: {exc}")

# 2. Regression guard: genuine ints still round-trip bare as ints.
text = emit_frontmatter({"title": "x", "n": 42}, body="body\n")
back, _ = parse_frontmatter(text)
if type(back["n"]) is not int or back["n"] != 42:
    failures.append(f"int regressed: {back['n']!r} ({type(back['n']).__name__})")

# 3. Regression guard: a float-LOOKING string still round-trips as a string.
text = emit_frontmatter({"title": "x", "s": "3.14"}, body="body\n")
back, _ = parse_frontmatter(text)
if type(back["s"]) is not str or back["s"] != "3.14":
    failures.append(f"float-looking string regressed: {back['s']!r} ({type(back['s']).__name__})")

if failures:
    for f in failures:
        print(f"FAIL: {f}")
    sys.exit(1)

print("OK: emitter refuses floats; int and float-looking string round-trip unchanged")
sys.exit(0)
