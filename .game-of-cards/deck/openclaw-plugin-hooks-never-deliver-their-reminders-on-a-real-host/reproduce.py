"""Reproduce: the OpenClaw plugin's lifecycle hooks never deliver on a real host.

Loads the committed openclaw-plugin/dist/index.js (the artifact OpenClaw
loads), registers it against a recording `api`, and calls each lifecycle
handler the way OpenClaw 2026.5.7 does: `handler(event, ctx)`, with the event
and context fields the SDK declares, merging only the handler's return value
(`runModifyingHook` / `runVoidHook` in the SDK's hook-runner-global chunk).
The workspace holds a deck with an active card and opts into the pattern
check, and the process cwd is that workspace, so every handler has the input
it needs to speak.

Reported per hook: the event/context fields the handler reads that the SDK
does not declare, and what reaches the host. Exits 1 while the defect fires
(the deck-first reminder is missing from before_prompt_build's return value,
or any handler reads a field the SDK does not declare), 0 once neither holds,
2 when the harness cannot run (no node >= 22, no dist/index.js).

`openclaw/plugin-sdk/plugin-entry` is stubbed with an identity
`definePluginEntry`; the real one copies `register` through unchanged, so no
`npm ci` is needed.
"""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / ".game-of-cards").is_dir():
            return p
        p = p.parent
    raise RuntimeError(".game-of-cards/ not found")


DIST = _repo_root() / "openclaw-plugin" / "dist" / "index.js"

# Field sets declared by openclaw@2026.5.7,
# dist/plugin-sdk/src/plugins/hook-types.d.ts and hook-before-agent-start.types.d.ts.
AGENT_CTX = ["runId", "jobId", "trace", "agentId", "sessionKey", "sessionId", "workspaceDir",
             "modelProviderId", "modelId", "messageProvider", "trigger", "channelId"]
DECLARED = {
    "session_start": {"event": ["sessionId", "sessionKey", "resumedFrom"],
                      "ctx": ["agentId", "sessionId", "sessionKey"]},
    "before_prompt_build": {"event": ["prompt", "messages"], "ctx": AGENT_CTX},
    "agent_end": {"event": ["runId", "messages", "success", "error", "durationMs"], "ctx": AGENT_CTX},
}

PROBE_MJS = r"""
import { pathToFileURL } from "node:url";
const [entryPath, workspace, declaredJson] = process.argv.slice(2);
const declared = JSON.parse(declaredJson);
const entry = (await import(pathToFileURL(entryPath).href)).default;
const handlers = {};
entry.register({ on: (name, fn) => { handlers[name] = fn; }, registerTool: () => {}, runtime: { system: {} } });
process.chdir(workspace);
const inputs = {
  session_start: [{ sessionId: "s1" }, { agentId: "main", sessionId: "s1" }],
  before_prompt_build: [
    { prompt: "please fix the login redirect bug", messages: [] },
    { agentId: "main", sessionId: "s1", workspaceDir: workspace },
  ],
  agent_end: [
    { messages: [{ role: "assistant", content: [{ type: "toolCall", name: "write", arguments: { path: "a.py" } }] }], success: true },
    { agentId: "main", sessionId: "s1", workspaceDir: workspace },
  ],
};
function recording(obj, allowed, reads) {
  return new Proxy(obj, { get(target, prop) {
    if (typeof prop === "string" && prop !== "then" && !allowed.includes(prop)) reads.add(prop);
    return Reflect.get(target, prop);
  } });
}
const report = {};
for (const [name, [event, ctx]] of Object.entries(inputs)) {
  if (!handlers[name]) { report[name] = { registered: false }; continue; }
  const eventReads = new Set(), ctxReads = new Set();
  const returned = await handlers[name](
    recording(event, declared[name].event, eventReads),
    recording(ctx, declared[name].ctx, ctxReads),
  );
  report[name] = {
    registered: true,
    undeclared: [...[...eventReads].map((f) => "event." + f), ...[...ctxReads].map((f) => "ctx." + f)],
    returned: returned ?? null,
  };
}
console.log(JSON.stringify(report));
"""

ACTIVE_CARD = """---
title: some-active-card
status: active
human_gate: none
---
"""


def main() -> int:
    if shutil.which("node") is None or not DIST.is_file():
        print(f"harness: needs node >= 22 on PATH and {DIST}")
        return 2
    with tempfile.TemporaryDirectory() as tmp:
        plugin = Path(tmp, "plugin")
        stub = plugin / "node_modules" / "openclaw"
        stub.mkdir(parents=True)
        (stub / "package.json").write_text(json.dumps({
            "name": "openclaw", "type": "module",
            "exports": {"./plugin-sdk/plugin-entry": "./plugin-entry.js"},
        }))
        (stub / "plugin-entry.js").write_text("export const definePluginEntry = (e) => e;\n")
        (plugin / "dist").mkdir()
        shutil.copy(DIST, plugin / "dist" / "index.js")
        (plugin / "probe.mjs").write_text(PROBE_MJS)
        workspace = Path(tmp, "workspace")
        card = workspace / ".game-of-cards" / "deck" / "some-active-card"
        card.mkdir(parents=True)
        (card / "README.md").write_text(ACTIVE_CARD)
        (workspace / ".game-of-cards" / "config.yaml").write_text(
            "hooks:\n  pattern_generalization_check: true\n"
        )
        run = subprocess.run(
            ["node", str(plugin / "probe.mjs"), str(plugin / "dist" / "index.js"),
             str(workspace), json.dumps(DECLARED)],
            capture_output=True, text=True,
        )
    if run.returncode != 0:
        print(f"harness: probe failed\n{run.stderr}")
        return 2
    report = json.loads(run.stdout)
    fires = False
    print("openclaw-plugin/dist/index.js, each hook called as OpenClaw 2026.5.7 calls it:")
    for name, r in report.items():
        if not r["registered"]:
            print(f"  {name:20} not registered")
            continue
        undeclared = ", ".join(r["undeclared"]) or "none"
        print(f"  {name:20} reads undeclared: {undeclared}")
        print(f"  {'':20} returns to host:  {json.dumps(r['returned'])}")
        fires = fires or bool(r["undeclared"])
    prompt_result = report.get("before_prompt_build", {}).get("returned") or {}
    delivered = any("[Game of Cards | runtime active]" in str(v) for v in prompt_result.values())
    print(f"deck-first reminder reaches the host in an opted-in workspace: {delivered}")
    if fires or not delivered:
        print("DEFECT FIRES: the hooks read guessed fields and deliver nothing on a real host.")
        return 1
    print("ok: every hook reads only declared fields and the reminder reaches the host.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
