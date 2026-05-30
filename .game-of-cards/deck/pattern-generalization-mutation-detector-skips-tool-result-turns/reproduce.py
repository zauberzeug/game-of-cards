"""Reproduce: _had_code_mutation breaks on tool_result before reaching the Edit.

Claude Code wraps every tool_result in a role=user message. The hook's
backward walk uses role==user as a turn boundary, so any transcript that
ends with an assistant text reply trips the break before the loop reaches
the prior tool_use entry. The reminder is then suppressed for the typical
"edit, observe result, report" shape that real sessions produce.

This reproducer feeds the unmodified shipped hook three synthetic
transcripts and asserts:

  case A — realistic Edit-then-text shape:    REMINDER SHOULD fire
  case B — degenerate Edit-as-last-entry:     REMINDER SHOULD fire
  case C — no code mutation (baseline):       REMINDER SHOULD NOT fire

Case B is the only shape the existing sibling card's reproduce.py
exercises. The fact that the hook passes B but fails A is the defect
this card files.
"""

from __future__ import annotations

import json
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
HOOK = ROOT / "goc" / "templates" / "hooks" / "pattern_generalization_check.py"


def _run_hook(entries: list[dict]) -> tuple[int, str]:
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as tf:
        tf.write("\n".join(json.dumps(e) for e in entries))
        transcript_path = tf.name
    payload = json.dumps({"transcript_path": transcript_path, "cwd": str(ROOT)})
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=payload,
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout


def main() -> int:
    case_a = [
        {"message": {"role": "user", "content": "please fix the bug"}},
        {
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "tool_use", "name": "Edit", "input": {"file_path": "/x"}}
                ],
            }
        },
        {
            "message": {
                "role": "user",
                "content": [
                    {"type": "tool_result", "tool_use_id": "x", "content": "ok"}
                ],
            }
        },
        {"message": {"role": "assistant", "content": [{"type": "text", "text": "Done."}]}},
    ]

    case_b = [
        {"message": {"role": "user", "content": "edit it"}},
        {
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "tool_use", "name": "Edit", "input": {"file_path": "/x"}}
                ],
            }
        },
    ]

    case_c = [
        {"message": {"role": "user", "content": "what is the weather?"}},
        {"message": {"role": "assistant", "content": [{"type": "text", "text": "Sunny."}]}},
    ]

    results = []
    for label, entries, should_fire in [
        ("A realistic Edit-then-text", case_a, True),
        ("B degenerate Edit-last     ", case_b, True),
        ("C no-tool baseline         ", case_c, False),
    ]:
        rc, stdout = _run_hook(entries)
        fired = "[GoC | pattern-check]" in stdout
        ok = fired is should_fire
        results.append((label, should_fire, fired, ok))
        print(
            f"case {label}: should_fire={should_fire}  fired={fired}  "
            f"exit={rc}  -> {'PASS' if ok else 'FAIL'}"
        )

    print()
    all_pass = all(ok for *_, ok in results)
    if all_pass:
        print("PASS: every case classified correctly.")
        return 0
    print(
        "FAIL: at least one case is misclassified.\n"
        "      The defect is case A — the realistic Edit-then-text shape\n"
        "      trips the loop's boundary break on the tool_result wrapper\n"
        "      before reaching the Edit entry, so the REMINDER is suppressed."
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
