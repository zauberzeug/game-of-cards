"""Reproduce: the pattern-generalization Stop hook cannot reach the agent.

A Claude Code Stop hook delivers text to the model ONLY by blocking the
stop — exit code 2 with the message on stderr, or JSON
{"decision": "block", "reason": ...} on stdout. Plain stdout on exit 0
goes to the user's transcript view, never to the model.

This reproducer feeds the shipped hook a synthetic transcript whose last
assistant turn used a code-mutating tool (Edit), captures the hook's
stdout / stderr / exit code, and shows the reminder lands on the
exit-0 stdout channel — the one channel a Stop hook CANNOT use to reach
the agent. No Claude Code runtime needed; the defect is the channel the
hook writes to.
"""

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


def main() -> int:
    # A transcript whose most recent assistant turn used a code-mutating tool.
    transcript_lines = [
        json.dumps({"role": "user", "content": "do the thing"}),
        json.dumps(
            {
                "role": "assistant",
                "content": [
                    {"type": "tool_use", "name": "Edit", "input": {"file_path": "x"}}
                ],
            }
        ),
    ]
    with tempfile.NamedTemporaryFile(
        "w", suffix=".jsonl", delete=False
    ) as tf:
        tf.write("\n".join(transcript_lines))
        transcript_path = tf.name

    stdin_payload = json.dumps(
        {"transcript_path": transcript_path, "cwd": str(ROOT)}
    )
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=stdin_payload,
        capture_output=True,
        text=True,
    )

    reminder_on_stdout = "[GoC | pattern-check]" in proc.stdout
    reminder_on_stderr = "[GoC | pattern-check]" in proc.stderr
    is_json_block = False
    try:
        is_json_block = json.loads(proc.stdout.strip()).get("decision") == "block"
    except (json.JSONDecodeError, AttributeError, ValueError):
        is_json_block = False

    print(f"exit code .................. {proc.returncode}")
    print(f"reminder on stdout ......... {reminder_on_stdout}")
    print(f"reminder on stderr ......... {reminder_on_stderr}")
    print(f"stdout is JSON block ....... {is_json_block}")
    print()

    # A Stop hook reaches the agent iff it blocks: exit 2 + stderr, or JSON block.
    reaches_agent = (proc.returncode == 2 and reminder_on_stderr) or is_json_block
    if reaches_agent:
        print("PASS: the hook uses a channel that reaches the agent.")
        return 0

    print(
        "FAIL: reminder is on exit-0 stdout — the one channel a Stop hook\n"
        "      CANNOT use to reach the model. The agent never sees it; the\n"
        "      reminder only appears in the user's transcript (Ctrl-R) view."
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
