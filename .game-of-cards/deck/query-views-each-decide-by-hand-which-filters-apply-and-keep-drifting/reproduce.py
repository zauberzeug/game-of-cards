"""Reproduce: the views of one `goc` query disagree about which filters apply.

For each scope filter, builds a temp deck holding a ready, a gated and an
active card inside the filter's scope, and the same three outside it. The
out-of-scope gated card outranks the in-scope one. Every out-of-scope card's
title starts with `out-`. Five views of the same query are then checked:

  table     `goc <filter>`, every line except the ACTIVE banner
  json      `goc --json <filter>`
  board     `goc --board <filter>`
  banner    the ACTIVE line of `goc <filter>`
  leverage  the gated half of `goc --ready <filter>`

A view honors the filter when it names no `out-` card. Prints the matrix.
Exits 1 when a view ignores a filter that is not listed in EXCEPTIONS (the
drift this card tracks). Exits 0 when every view honors every filter or
declares the exception. EXCEPTIONS is empty until the card's decision names
the deliberate ones.
"""
import json
import os
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
VIEWS = ("table", "json", "board", "banner", "leverage")
# (view, filter) pairs the recorded decision declares deliberately unscoped.
EXCEPTIONS: set[tuple[str, str]] = set()

# filter -> (CLI args, in-scope card fields, out-of-scope card fields)
FILTERS = {
    "--worker": (["--worker", "alice"], {"worker": "alice"}, {"worker": "bob"}),
    "--tag": (["--tag", "documentation"], {"tags": "documentation"}, {"tags": "infra"}),
    "--contribution": (["--contribution", "low"], {"contribution": "low"}, {"contribution": "high"}),
    "--stage": (["--stage", "alpha"], {"stage": "alpha"}, {"stage": "beta"}),
    "--advances": (["--advances", "out-epic"], {"advances": "out-epic"}, {}),
    "--advanced-by": (["--advanced-by", "out-root"], {"advanced_by": "out-root"}, {}),
}
STATES = {"ready": ("open", "none"), "gated": ("open", "decision"), "active": ("active", "none")}


def _write_card(cwd: Path, title: str, status: str, gate: str, fields: dict) -> None:
    f = {"contribution": "low", "stage": "null", "tags": "bug", **fields}
    if title == "in-gated" and "contribution" not in fields:
        f["contribution"] = "medium"
    if title == "out-gated":
        f["contribution"] = "high"

    def edge(name: str) -> str:
        targets = [t for t in f.get(name, "").split(",") if t]
        return f"{name}: []\n" if not targets else f"{name}:\n" + "".join(f"- {t}\n" for t in targets)

    card_dir = cwd / "deck" / title
    card_dir.mkdir(parents=True)
    (card_dir / "README.md").write_text(
        "---\n"
        f"title: {title}\n"
        f"summary: {title}\n"
        f"status: {status}\n"
        f"stage: {f['stage']}\n"
        f"contribution: {f['contribution']}\n"
        "created: 2026-05-04\n"
        "closed_at: null\n"
        f"human_gate: {gate}\n"
        + edge("advances")
        + edge("advanced_by")
        + f"tags: [{f['tags']}]\n"
        + (f"worker: {f['worker']}\n" if f.get("worker") else "")
        + "definition_of_done: |\n"
        "  - [ ] test card\n"
        "---\n\n"
        f"# {title}\n"
    )


def _build_deck(cwd: Path, in_fields: dict, out_fields: dict) -> None:
    for state, (status, gate) in STATES.items():
        _write_card(cwd, f"in-{state}", status, gate, in_fields)
        _write_card(cwd, f"out-{state}", status, gate, out_fields)
    in_titles = ",".join(f"in-{s}" for s in STATES)
    if "advances" in in_fields:
        _write_card(cwd, "out-epic", "open", "none", {"advanced_by": in_titles})
    if "advanced_by" in in_fields:
        _write_card(cwd, "out-root", "open", "none", {"advances": in_titles})


def _goc(cwd: Path, *args: str) -> str:
    env = os.environ.copy()
    env.pop("GOC_WORKER", None)
    pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(ROOT) if not pythonpath else f"{ROOT}{os.pathsep}{pythonpath}"
    r = subprocess.run(
        [sys.executable, "-m", "goc.cli", *args],
        cwd=cwd, env=env, text=True, capture_output=True, check=False,
    )
    if r.returncode != 0:
        raise SystemExit(f"goc {' '.join(args)} exited {r.returncode}:\n{r.stdout}{r.stderr}")
    return r.stdout


def _views(cwd: Path, args: list[str]) -> dict[str, str]:
    """The text each view shows for the query `args`."""
    queue = _goc(cwd, "--no-color", *args).splitlines()
    pulling = next((ln for ln in _goc(cwd, "--ready", "--no-color", *args).splitlines()
                    if ln.startswith("Pulling ")), "")
    return {
        "table": "\n".join(ln for ln in queue if not ln.startswith("ACTIVE:")),
        "json": " ".join(c["title"] for c in json.loads(_goc(cwd, "--json", *args))),
        "board": _goc(cwd, "--board", "--no-color", *args),
        "banner": next((ln for ln in queue if ln.startswith("ACTIVE:")), ""),
        "leverage": pulling.partition("Highest gated card:")[2],
    }


def main() -> None:
    drift = []
    print(f"{'filter':<15}" + "".join(f"{v:<10}" for v in VIEWS))
    for flag, (args, in_fields, out_fields) in FILTERS.items():
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            _build_deck(cwd, in_fields, out_fields)
            shown = _views(cwd, args)
        cells = []
        for view in VIEWS:
            ignores = "out-" in shown[view]
            if not ignores and "in-" not in shown[view]:
                # A view that shows nothing names no `out-` card either; that
                # would read as "honors" without testing anything.
                raise SystemExit(f"{view} shows no card under {flag}: {shown[view]!r}")
            if ignores and (view, flag) not in EXCEPTIONS:
                drift.append(f"{view} ignores {flag}")
            cells.append("IGNORES" if ignores else "honors")
        print(f"{flag:<15}" + "".join(f"{c:<10}" for c in cells))
    print()
    if drift:
        print(f"FAIL: {len(drift)} view/filter pair(s) drift from the query: " + "; ".join(drift))
        sys.exit(1)
    print("PASS: every view of the query honors every scope filter (or declares the exception).")
    sys.exit(0)


if __name__ == "__main__":
    main()
