#!/usr/bin/env python3
"""Prove the publish-npm job packs a vendored engine with a stale __version__.

Two independent legs:

1. STRUCTURAL — inspect `.github/workflows/release.yml`'s publish-npm job:
   its checkout has no `ref:` (so in release mode it gets the pre-rewrite
   dispatch SHA) and no step runs `sync_plugin_assets.py` after the version
   rewrite, so `openclaw-plugin/goc/__init__.py` keeps whatever version the
   dispatch commit carried (the *previous* release's literal, since mirrors
   are only re-synced on main by the release-bump commit that this job's
   checkout predates).

2. SIMULATION — copy the exact file set `release_rewrite_versions.py`
   touches (plus the shipped mirror) into a tmpdir mirror and run the script
   there with version 9.9.9, exactly what publish-npm's "Rewrite version
   literals" step does. The shipped `openclaw-plugin/package.json` flips to
   9.9.9 while the shipped `openclaw-plugin/goc/__init__.py` literal stays
   put — the skew that lands in the npm tarball (its `files` list includes
   `goc/`).

Exits 0 (defect present) iff both legs show the skew. A network cross-check
against the live 0.0.27 tarball is attempted but non-fatal (clean checkouts
may be offline).
"""

import re
import shutil
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

failures = []

# ── Leg 1: structural inspection of the publish-npm job ────────────────────
workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text()
m = re.search(r"^  publish-npm:\n(.*?)(?=^  \S)", workflow, re.MULTILINE | re.DOTALL)
assert m, "publish-npm job not found in release.yml"
job = m.group(0)

checkout_has_ref = bool(re.search(r"uses: actions/checkout@[^\n]*\n\s+with:\s*\n\s+ref:", job))
runs_sync = "sync_plugin_assets" in job
runs_rewrite = "release_rewrite_versions.py" in job

print(f"publish-npm checkout pins a ref:        {checkout_has_ref}")
print(f"publish-npm re-runs the version rewrite: {runs_rewrite}")
print(f"publish-npm runs sync_plugin_assets:     {runs_sync}")
if checkout_has_ref or runs_sync or not runs_rewrite:
    failures.append("structural: publish-npm no longer matches the defect shape")

files_list = (ROOT / "openclaw-plugin" / "package.json").read_text()
ships_mirror = '"goc/"' in files_list
print(f'npm "files" list ships the goc/ mirror:  {ships_mirror}')
if not ships_mirror:
    failures.append("structural: tarball no longer ships the vendored engine")

# ── Leg 2: run the rewrite in a tmpdir mirror, exactly as publish-npm does ──
TOUCHED = [
    "scripts/release_rewrite_versions.py",
    "goc/__init__.py",
    "openclaw-plugin/package.json",
    "openclaw-plugin/package-lock.json",
    "openclaw-plugin/goc/__init__.py",  # NOT touched by the script — the point
    "claude-plugin/.claude-plugin/plugin.json",
    "codex-plugin/.codex-plugin/plugin.json",
    ".claude-plugin/marketplace.json",
    ".game-of-cards/deck/.goc-version",
    "AGENTS.md",
    "pyproject.toml",
]

with tempfile.TemporaryDirectory() as td:
    tmp = Path(td)
    for rel in TOUCHED:
        dst = tmp / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, dst)

    proc = subprocess.run(
        [sys.executable, str(tmp / "scripts" / "release_rewrite_versions.py"), "9.9.9"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        sys.exit(f"rewrite script failed:\n{proc.stdout}{proc.stderr}")

    pkg_version = re.search(
        r'"version":\s*"([^"]+)"', (tmp / "openclaw-plugin" / "package.json").read_text()
    ).group(1)
    mirror_version = re.search(
        r'^__version__\s*=\s*"([^"]+)"',
        (tmp / "openclaw-plugin" / "goc" / "__init__.py").read_text(),
        re.MULTILINE,
    ).group(1)

    print(f"after rewrite: openclaw-plugin/package.json version  = {pkg_version}")
    print(f"after rewrite: openclaw-plugin/goc/__init__.py       = {mirror_version}")
    if pkg_version != "9.9.9":
        failures.append("simulation: rewrite did not bump the shipped package.json")
    if mirror_version == "9.9.9":
        failures.append("simulation: rewrite now covers the vendored mirror — defect fixed")

# ── Optional: live-registry cross-check (non-fatal, needs network) ─────────
try:
    import io
    import tarfile
    import urllib.request

    url = "https://registry.npmjs.org/game-of-cards/-/game-of-cards-0.0.27.tgz"
    data = urllib.request.urlopen(url, timeout=10).read()
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tf:
        pkg = tf.extractfile("package/package.json").read().decode()
        init = tf.extractfile("package/goc/__init__.py").read().decode()
    live_pkg = re.search(r'"version":\s*"([^"]+)"', pkg).group(1)
    live_engine = re.search(r'^__version__\s*=\s*"([^"]+)"', init, re.MULTILINE).group(1)
    print(f"live npm 0.0.27 tarball: package.json = {live_pkg}, vendored engine = {live_engine}")
except Exception as exc:  # noqa: BLE001 — network is best-effort on clean checkouts
    print(f"live-registry cross-check skipped ({type(exc).__name__})")

if failures:
    for f in failures:
        print(f"NOT REPRODUCED: {f}")
    sys.exit(1)
print("DEFECT REPRODUCED: publish-npm ships a vendored engine at the previous version")
