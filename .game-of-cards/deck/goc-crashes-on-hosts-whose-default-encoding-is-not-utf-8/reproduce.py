#!/usr/bin/env python3
"""Prove that `goc` reads, writes and prints in the HOST's default encoding.

Nothing in the package pins UTF-8 — not the file IO, not stdout — so every
text surface inherits `locale.getpreferredencoding(False)`. On a UTF-8 host
that is invisible; on a host whose default encoding is something else the
same commands raise `UnicodeDecodeError` / `UnicodeEncodeError`.

The probe forces a non-UTF-8 default the way a non-UTF-8 host presents one:
`LC_ALL=C` plus `PYTHONUTF8=0` / `PYTHONCOERCECLOCALE=0`. The two opt-outs
are needed only because PEP 538 + PEP 540 auto-upgrade the *C* locale to
UTF-8 — they are the stand-in for a host that simply has a non-UTF-8 default
(Windows' ANSI code page on Python <= 3.14; any installed `*.ISO-8859-1`
locale on POSIX), which needs no environment variables at all.

Exits 0 only when every check below is clean.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


ROOT = _repo_root()

# A host whose Python default encoding is not UTF-8.
NON_UTF8_ENV = {
    **os.environ,
    "LC_ALL": "C",
    "LANG": "C",
    "PYTHONUTF8": "0",
    "PYTHONCOERCECLOCALE": "0",
    "PYTHONPATH": str(ROOT),
}

IO_CALL = re.compile(r"\.(?:read_text|write_text)\(")


def _effective_encoding() -> str:
    out = subprocess.run(
        [sys.executable, "-c",
         "import locale;print(locale.getpreferredencoding(False))"],
        env=NON_UTF8_ENV, capture_output=True, text=True,
    )
    return out.stdout.strip()


def _run_goc(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "goc.cli", *args],
        cwd=cwd, env=NON_UTF8_ENV, capture_output=True, text=True,
    )


def check_io_sites() -> int:
    """Package-level text IO that omits `encoding=` — the root cause."""
    total = 0
    for name in ("engine.py", "install.py", "cli.py"):
        path = ROOT / "goc" / name
        hits = [
            (i, line.strip())
            for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
            if IO_CALL.search(line) and "encoding=" not in line
        ]
        print(f"  goc/{name}: {len(hits)} read_text/write_text call(s) without encoding=")
        if hits:
            i, line = hits[0]
            print(f"      first: goc/{name}:{i}: {line[:88]}")
        total += len(hits)
    return total


def check_templates_encodable() -> int:
    """Shipped templates the Windows default ANSI code page cannot write."""
    files = [
        f for f in (ROOT / "goc" / "templates").rglob("*")
        if f.is_file() and f.suffix in (".md", ".yaml", ".py", ".sh")
    ]
    offenders, chars = [], {}
    for f in files:
        text = f.read_text(encoding="utf-8")
        try:
            text.encode("cp1252")
        except UnicodeEncodeError:
            offenders.append(f)
            for c in text:
                if ord(c) > 127:
                    try:
                        c.encode("cp1252")
                    except UnicodeEncodeError:
                        chars[c] = chars.get(c, 0) + 1
    top = sorted(chars.items(), key=lambda kv: -kv[1])[:8]
    print(f"  shipped template files scanned: {len(files)}")
    print(f"  files unwritable under cp1252:  {len(offenders)}")
    if top:
        print("  offending characters: "
              + ", ".join(f"{c!r}x{n}" for c, n in top))
    return len(offenders)


def check_install_and_queue() -> int:
    """`goc install` (read path) and the bare queue (stdout path)."""
    failures = 0
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        subprocess.run(["git", "init", "-q", "."], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.email", "probe@example.com"],
                       cwd=repo, check=True)
        subprocess.run(["git", "config", "user.name", "probe"], cwd=repo, check=True)

        res = _run_goc(["install"], repo)
        tail = (res.stderr.strip().splitlines() or ["(no stderr)"])[-1]
        print(f"  goc install            -> exit {res.returncode}: {tail[:96]}")
        if res.returncode != 0:
            failures += 1
            briefing = repo / "AGENTS.md"
            print(f"      left behind: .game-of-cards/ exists="
                  f"{(repo / '.game-of-cards').is_dir()}, "
                  f"AGENTS.md briefing exists={briefing.exists()}")

        # Install cleanly (UTF-8) so the queue check exercises stdout, not setup.
        utf8_env = {**os.environ, "PYTHONPATH": str(ROOT)}
        subprocess.run([sys.executable, "-m", "goc.cli", "install"],
                       cwd=repo, env=utf8_env, capture_output=True, text=True)
        subprocess.run(
            [sys.executable, "-m", "goc.cli", "new", "encoding-probe-card",
             "--summary", "A probe card so the queue table has a row to render."],
            cwd=repo, env=utf8_env, capture_output=True, text=True, check=False,
        )
        subprocess.run([sys.executable, "-m", "goc.cli", "publish",
                        "encoding-probe-card"],
                       cwd=repo, env=utf8_env, capture_output=True, text=True)

        res = _run_goc([], repo)
        tail = (res.stderr.strip().splitlines() or ["(no stderr)"])[-1]
        print(f"  goc (queue listing)    -> exit {res.returncode}: {tail[:96]}")
        if res.returncode != 0:
            failures += 1
    return failures


def main() -> int:
    enc = _effective_encoding()
    print(f"simulated host default encoding: {enc}")
    if "utf" in enc.lower():
        print("SKIP: this host forces UTF-8 even with the locale opted out; "
              "the behavioural half of this probe cannot run here.")
        behavioural = -1
    else:
        print("\n[1] behaviour on a non-UTF-8 host")
        behavioural = check_install_and_queue()

    print("\n[2] package text IO that inherits the host encoding")
    io_sites = check_io_sites()

    print("\n[3] shipped templates vs the Windows default code page")
    unwritable = check_templates_encodable()

    print(
        f"\nSUMMARY: encoding-less IO sites={io_sites}, "
        f"cp1252-unwritable templates={unwritable}, "
        f"commands failing on a non-UTF-8 host="
        f"{'n/a' if behavioural < 0 else behavioural}"
    )
    if io_sites or unwritable or behavioural > 0:
        print("FAIL: goc still depends on the host's default encoding.")
        return 1
    print("OK: goc pins UTF-8 on every text surface.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
