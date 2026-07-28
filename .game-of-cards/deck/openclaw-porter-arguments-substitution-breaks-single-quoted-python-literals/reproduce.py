"""Prove the OpenClaw skill porter emits syntactically invalid Python.

The porter rewrites `$ARGUMENTS` to the phrase `the user's argument`
(`scripts/port_skills_to_openclaw.py:72`). That phrase contains an
apostrophe, so anywhere a source template interpolates `$ARGUMENTS`
inside a single-quoted Python literal, the ported result is an
unterminated string.

Differential probe: for each ``python3 -c "..."`` snippet in a source
skill template, compile the snippet as written and compile the ported
counterpart, and report only snippets the *port* breaks. That isolates
porter damage from pre-existing snippet quirks — the snippets are
embedded in a double-quoted shell word, so `\\"` escapes are unescaped
before parsing and `$ARGUMENTS` is bound to a value on the source side.

Exits non-zero while the port breaks any snippet that compiled before.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


ROOT = _repo_root()
PORTED = ROOT / "openclaw-plugin" / "skills"
SOURCE = ROOT / "goc" / "templates" / "skills"
PORTER = ROOT / "scripts" / "port_skills_to_openclaw.py"

# A `python3 -c "` snippet inside a fenced block: everything up to the closing
# double quote on its own line.
SNIPPET_RE = re.compile(r'python3 -c "\n(.*?)\n"', re.DOTALL)


def _as_python(snippet: str, *, bind_arguments: bool) -> str:
    """Recover the Python source the shell would hand to `python3 -c`."""
    text = snippet.replace('\\"', '"')
    if bind_arguments:
        # What the Claude host substitutes: the slash-command argument.
        text = text.replace("$ARGUMENTS", "10")
    return text


def _snippets(path: Path) -> list[tuple[int, str]]:
    text = path.read_text()
    out = []
    for m in SNIPPET_RE.finditer(text):
        out.append((text.count("\n", 0, m.start()) + 1, m.group(1)))
    return out


def _syntax_error(source: str) -> SyntaxError | None:
    try:
        ast.parse(source)
    except SyntaxError as exc:
        return exc
    return None


def main() -> int:
    substitution = next(
        (ln.strip() for ln in PORTER.read_text().splitlines() if r'r"\$ARGUMENTS"' in ln),
        None,
    )
    print("porter substitution:", substitution or "(not found)")
    print()

    regressions: list[str] = []
    compared = 0
    for src in sorted(SOURCE.rglob("SKILL.md")):
        dst = PORTED / src.relative_to(SOURCE)
        if not dst.exists():
            continue  # host-specific complement the porter skips
        src_snippets = _snippets(src)
        dst_snippets = _snippets(dst)
        if len(src_snippets) != len(dst_snippets):
            continue  # structural rewrite; not a like-for-like comparison
        for (src_line, s), (dst_line, d) in zip(src_snippets, dst_snippets):
            compared += 1
            src_err = _syntax_error(_as_python(s, bind_arguments=True))
            dst_err = _syntax_error(_as_python(d, bind_arguments=False))
            if src_err is None and dst_err is not None:
                bad = _as_python(d, bind_arguments=False).splitlines()
                offending = bad[(dst_err.lineno or 1) - 1].strip()
                print(f"[PORT BREAKS IT] {src.relative_to(ROOT)}:{src_line}")
                print(f"                 → {dst.relative_to(ROOT)}:{dst_line}")
                print(f"                 source snippet compiles; ported snippet: "
                      f"{type(dst_err).__name__}: {dst_err.msg}")
                print(f"                 offending line: {offending}")
                regressions.append(f"{dst.relative_to(ROOT)}:{dst_line}")
            elif src_err is not None and dst_err is not None:
                print(f"[pre-existing]   {src.relative_to(ROOT)}:{src_line} — "
                      f"{src_err.msg} (broken before the port too; not this defect)")

    print()
    print(f"snippet pairs compared: {compared}   broken by the port: {len(regressions)}")

    if regressions:
        print()
        print(
            f"[FAIL] the port turns {len(regressions)} compiling snippet(s) into a "
            "SyntaxError. An OpenClaw agent following the step gets nothing back — "
            "silently, because the snippet ends in `2>/dev/null || true`."
        )
        return 1
    print()
    print("[OK] the port breaks no snippet that compiled in its source template.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
