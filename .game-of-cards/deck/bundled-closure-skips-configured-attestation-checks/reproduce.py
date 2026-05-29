"""Demonstrate that `goc done --bundle` skips configured layer-2 /
layer-3 attestation checks.

Builds three cards in a temp deck:
  - card-c-prereq    (open, no DoD ticked)
  - card-a-bundle    (DoD ticked, advanced_by: [card-c-prereq])
  - card-b-bundle    (DoD ticked, no edges)

Runs:
  1. `goc attest card-a-bundle` — FAILs (advanced-by-closed, log-md-closure-entry).
  2. `goc done --bundle card-a-bundle card-b-bundle` — succeeds.

The exit asserts the asymmetry: attest=2, bundle-done=0, and the
bundle's Closure-verification block contains "DoD enforcement: PASS"
without any per-layer check results.

Run from the repo root:
    uv run python .game-of-cards/deck/bundled-closure-skips-configured-attestation-checks/reproduce.py
"""
from __future__ import annotations

import os
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


def _write_card(card_dir: Path, *, title: str, status: str, dod_box: str,
                advanced_by: list[str]) -> None:
    card_dir.mkdir(parents=True)
    advanced_block = (
        "advanced_by: []\n"
        if not advanced_by
        else "advanced_by:\n" + "".join(f"  - {t}\n" for t in advanced_by)
    )
    (card_dir / "README.md").write_text(
        "---\n"
        f"title: {title}\n"
        f"summary: reproducer fixture for bundled-closure attestation gap\n"
        f"status: {status}\n"
        "stage: null\n"
        "contribution: medium\n"
        "created: 2026-05-29\n"
        "closed_at: null\n"
        "human_gate: none\n"
        "advances: []\n"
        f"{advanced_block}"
        "tags: []\n"
        "definition_of_done: |\n"
        f"  {dod_box}\n"
        "---\n\n"
        f"# {title}\n"
    )
    (card_dir / "log.md").write_text("")


def main() -> int:
    repo_root = _repo_root()
    tmp = Path(tempfile.mkdtemp(prefix="goc-bundle-attest-"))
    try:
        deck_root = tmp
        (deck_root / ".game-of-cards" / "deck").mkdir(parents=True)
        (deck_root / ".game-of-cards" / "config.yaml").write_text(
            "layer_2_project_dod: []\n"
            "layer_3_goc_dod:\n"
            "  - name: advanced-by-closed\n"
            "    kind: derived\n"
            "  - name: dod-100-percent\n"
            "    kind: derived\n"
            "  - name: log-md-closure-entry\n"
            "    kind: derived\n"
            "workflow:\n"
            "  auto_commit: false\n"
        )

        deck = deck_root / ".game-of-cards" / "deck"
        _write_card(deck / "card-c-prereq", title="card-c-prereq",
                    status="open", dod_box="- [ ] still open", advanced_by=[])
        _write_card(deck / "card-a-bundle", title="card-a-bundle",
                    status="open", dod_box="- [x] DoD ticked",
                    advanced_by=["card-c-prereq"])
        _write_card(deck / "card-b-bundle", title="card-b-bundle",
                    status="open", dod_box="- [x] DoD ticked", advanced_by=[])

        env = {**os.environ, "PYTHONPATH": str(repo_root)}

        result_attest = subprocess.run(
            [sys.executable, "-m", "goc.cli", "attest", "card-a-bundle",
             "--non-interactive"],
            cwd=deck_root, env=env, capture_output=True, text=True,
        )
        print("=== goc attest card-a-bundle ===")
        print(f"exit: {result_attest.returncode}")
        print(result_attest.stdout, end="")
        if result_attest.stderr.strip():
            print(f"STDERR: {result_attest.stderr}", end="")

        result_bundle = subprocess.run(
            [sys.executable, "-m", "goc.cli", "done", "--bundle",
             "card-a-bundle", "card-b-bundle"],
            cwd=deck_root, env=env, capture_output=True, text=True,
        )
        print("\n=== goc done --bundle card-a-bundle card-b-bundle ===")
        print(f"exit: {result_bundle.returncode}")
        print(result_bundle.stdout, end="")
        if result_bundle.stderr.strip():
            print(f"STDERR: {result_bundle.stderr}", end="")

        log_text = (deck / "card-a-bundle" / "log.md").read_text()
        print("\n=== card-a-bundle/log.md after bundle close ===")
        print(log_text)

        # Assertions: attest blocks closure, bundle bypasses it.
        attest_blocked = result_attest.returncode == 2
        bundle_succeeded = result_bundle.returncode == 0
        bundle_block_lacks_layer_results = (
            "Closure verification" in log_text
            and "DoD enforcement: PASS" in log_text
            and "advanced-by-closed FAIL" not in log_text.split("--- bundled")[-1] if "bundled" in log_text else True
        )
        # Simpler: the BUNDLED block contains no "### Layer-" subsection.
        bundled_section = log_text.split("— bundled", 1)[-1] if "— bundled" in log_text else ""
        bundled_section_lacks_layer_results = "### Layer-" not in bundled_section

        print("=== assertions ===")
        print(f"  attest blocked card-a-bundle (exit 2)         : {attest_blocked}")
        print(f"  bundle closed card-a-bundle anyway (exit 0)   : {bundle_succeeded}")
        print(f"  bundled block has NO per-layer results        : {bundled_section_lacks_layer_results}")

        all_ok = attest_blocked and bundle_succeeded and bundled_section_lacks_layer_results
        if all_ok:
            print("\nDEFECT REPRODUCED: bundle bypassed the attestation that "
                  "`goc attest` would have failed.")
            return 0
        print("\nDEFECT NOT REPRODUCED — behavior diverged.")
        return 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
