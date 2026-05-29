/**
 * Game of Cards — OpenClaw plugin entry.
 *
 * Registers a `goc` tool that shells out to the bundled Python engine, plus
 * three lifecycle hooks ported from the Claude Code plugin's deck_*.py
 * scripts. The bundled engine lives at `<plugin-root>/goc/` (auto-synced
 * from the top-level `goc/` package via `scripts/sync_plugin_assets.py`).
 *
 * See:
 *   - https://docs.openclaw.ai/plugins/manifest.md (plugin manifest)
 *   - https://docs.openclaw.ai/plugins/sdk-overview.md (api.* surface)
 *   - https://docs.openclaw.ai/plugins/sdk-runtime.md (runtime helpers — incl. system.runCommandWithTimeout)
 *   - https://docs.openclaw.ai/plugins/hooks.md (lifecycle hooks)
 *   - https://docs.openclaw.ai/tools/index.md (tool concept)
 *
 * Architectural note: OpenClaw has no auto-PATH-prepend mechanism for plugin
 * binaries (verified via the PATH-integration spike on
 * `provide-openclaw-plugin-for-skills-and-hooks`). So the plugin exposes
 * goc as a registered tool rather than a shell binary on PATH. Subprocess
 * invocations route through `api.runtime.system.runCommandWithTimeout`
 * (the sanctioned spawn API per OpenClaw's plugin-sandbox policy) instead
 * of direct stdlib subprocess imports, which the safe-install policy
 * blocks. (The blocked-import name is intentionally not spelled out here:
 * OpenClaw's safe-install scanner pattern-matches on raw source bytes and
 * trips on the literal token even when it appears only in a comment.)
 *
 * After compilation, this file lives at `<plugin-root>/dist/index.js`, so
 * the vendored engine path is computed as `dirname(__file) + "/../"`
 * (the plugin root is the parent of dist/).
 */

import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";
import { Type, type Static } from "@sinclair/typebox";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { access, readFile, readdir } from "node:fs/promises";

const COMPILED_DIR = dirname(fileURLToPath(import.meta.url));
// PLUGIN_ROOT is the parent of the compiled dist/ — i.e., the
// openclaw-plugin/ directory itself, where goc/ is vendored.
const PLUGIN_ROOT = resolve(COMPILED_DIR, "..");
const VENDORED_GOC_PATH = PLUGIN_ROOT;

// Mirrors the click subparser surface in goc/cli.py — keep in sync if new
// verbs land. The argparse `commands` field is the source of truth.
const GOC_VERBS = [
  "validate",
  "quality-pass",
  "done",
  "attest",
  "status",
  "new",
  "advance",
  "unadvance",
  "move",
  "decide",
  "triage",
  "show",
  "migrate",
  "migrate-list-style",
] as const;

const GocToolParams = Type.Object({
  verb: Type.Union(
    GOC_VERBS.map((v) => Type.Literal(v)),
    {
      description:
        "The goc subcommand to run. Most card lifecycle work uses `new`, `status`, `done`, `decide`, `advance`, `show`, or `triage`.",
    },
  ),
  args: Type.Array(Type.String(), {
    description:
      "Positional and flag arguments forwarded to the verb (e.g., ['my-card-title', '--decision', 'X', '--because', 'Y']).",
    default: [],
  }),
  flags: Type.Optional(
    Type.Object(
      {
        tag: Type.Optional(Type.String()),
        status: Type.Optional(Type.String()),
        contribution: Type.Optional(Type.String()),
        worker: Type.Optional(Type.String()),
        board: Type.Optional(Type.Boolean()),
        json: Type.Optional(Type.Boolean()),
        since: Type.Optional(Type.String()),
      },
      {
        description:
          "Top-level filter flags applied before the verb. Use these for bare-queue listings; otherwise prefer verb-specific flags via `args`.",
      },
    ),
  ),
  cwd: Type.Optional(
    Type.String({
      description:
        "Working directory for the goc invocation. Defaults to the active workspace root.",
    }),
  ),
});

type GocToolInput = Static<typeof GocToolParams>;

function buildArgs(input: GocToolInput): string[] {
  const flagTokens: string[] = [];
  const f = input.flags ?? {};
  if (f.tag) flagTokens.push("--tag", f.tag);
  if (f.status) flagTokens.push("--status", f.status);
  if (f.contribution) flagTokens.push("--contribution", f.contribution);
  if (f.worker) flagTokens.push("--worker", f.worker);
  if (f.board) flagTokens.push("--board");
  if (f.json) flagTokens.push("--json");
  if (f.since) flagTokens.push("--since", f.since);
  return [...flagTokens, input.verb, ...(input.args ?? [])];
}

// === Lifecycle-hook helpers (ported from claude-plugin/hooks/*.py) ===

const FRONTMATTER_RE = /^---\n([\s\S]*?\n)---\n/;
const IMPEDED_WAITING_ON = new Set(["external", "resource", "deferred"]);
const ISO_DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
const ISO_DATETIME_UTC_RE = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/;

interface ActiveCard {
  name: string;
  humanGate: string;
  impeded: boolean;
}

function stripQuotes(s: string): string {
  return s.replace(/^["']|["']$/g, "");
}

function parseWaitingUntil(value: string): Date | null {
  // Mirrors goc.engine._waiting_until_instant: a bare date YYYY-MM-DD is
  // midnight UTC of that day; a datetime YYYY-MM-DDTHH:MM:SSZ is honored
  // at full precision so a same-day future timestamp does not collapse
  // to "today" and clear early.
  if (ISO_DATETIME_UTC_RE.test(value)) {
    const t = Date.parse(value);
    return Number.isNaN(t) ? null : new Date(t);
  }
  if (ISO_DATE_RE.test(value)) {
    const t = Date.parse(`${value}T00:00:00Z`);
    return Number.isNaN(t) ? null : new Date(t);
  }
  return null;
}

function isImpeded(waitingOn: string, waitingUntil: string, now: Date): boolean {
  // Mirrors goc.engine.waiting_impedes across the four-cell waiting_on ×
  // waiting_until matrix at full UTC timestamp precision (matching
  // engine._waiting_until_instant). An elapsed waiting_until resurfaces
  // the card even when waiting_on is also set (engine contract).
  const untilDt = waitingUntil !== "" ? parseWaitingUntil(waitingUntil) : null;
  const untilFuture = untilDt !== null && untilDt.getTime() > now.getTime();
  if (IMPEDED_WAITING_ON.has(waitingOn)) {
    if (untilDt !== null && !untilFuture) return false;
    return true;
  }
  return untilFuture;
}

async function findActiveCards(deckDir: string): Promise<ActiveCard[]> {
  let entries: string[];
  try {
    const dirents = await readdir(deckDir, { withFileTypes: true });
    entries = dirents
      .filter((d) => d.isDirectory())
      .map((d) => d.name)
      .sort();
  } catch {
    return [];
  }
  const now = new Date();
  const active: ActiveCard[] = [];
  for (const name of entries) {
    const readme = resolve(deckDir, name, "README.md");
    let text: string;
    try {
      text = await readFile(readme, "utf8");
    } catch {
      continue;
    }
    const m = FRONTMATTER_RE.exec(text);
    if (!m) continue;
    let status: string | null = null;
    let humanGate = "none";
    let waitingOn = "";
    let waitingUntil = "";
    for (const line of m[1].split("\n")) {
      if (line.startsWith("status:")) {
        status = line.split(":", 2)[1].trim();
      } else if (line.startsWith("human_gate:")) {
        const val = line.split(":", 2)[1].trim();
        if (val) humanGate = val;
      } else if (line.startsWith("waiting_on:")) {
        waitingOn = stripQuotes(line.split(":", 2)[1].trim());
      } else if (line.startsWith("waiting_until:")) {
        waitingUntil = stripQuotes(line.split(":", 2)[1].trim());
      }
    }
    if (status !== "active") continue;
    const impeded = isImpeded(waitingOn, waitingUntil, now);
    active.push({ name, humanGate, impeded });
  }
  return active;
}

async function resolveDeckDir(projectDir: string): Promise<string> {
  const primary = resolve(projectDir, ".game-of-cards", "deck");
  try {
    await readdir(primary);
    return primary;
  } catch {
    return resolve(projectDir, "deck");
  }
}

// Patterns mirror goc/templates/hooks/deck_prompt_router.py exactly.
const WORK_INITIATING = [
  /\blet'?s\s+(do|build|implement|make|add|create|fix|introduce|write|refactor)\b/i,
  /\b(implement|build|introduce|refactor)\s+\w/i,
  /\b(fix|add|create|write)\s+(a|an|the|this|that|some)\b/i,
  /\bi\s+(want|need)\s+(to|a|an|the|this)\b/i,
  /\bwe\s+(need|should|want)\s+to\b/i,
  /\bcan\s+you\s+(add|fix|build|create|implement|introduce|write)\b/i,
  /\bplease\s+(add|fix|build|create|implement|introduce|write)\b/i,
  /\bmake\s+it\s+(work|do|so|happen)\b/i,
  /\bship\s+(it|this|the)\b/i,
];

const EXPLORATION = [
  /\bexplain\b/i,
  /\bwhat\s+does\b/i,
  /\bwhat\s+is\b/i,
  /\bhow\s+does\b/i,
  /\bwhy\s+(is|does|are)\b/i,
  /\bshow\s+me\b/i,
  /\b(can|could)\s+you\s+(explain|tell|show|describe)\b/i,
  /\bwalk\s+me\s+through\b/i,
];

const TOOLING = [
  /\bgit\s+(status|log|diff|stash)\b/i,
  /\brebase\b/i,
  /\brun\s+(pytest|the\s+tests)\b/i,
  /\bnpm\s+(install|run)\b/i,
  /\buv\s+(sync|run|pip)\b/i,
];

const DECK_REMINDER = [
  "[Game of Cards | runtime active]",
  "The user's prompt above is a card request. Run the GoC pipeline SILENTLY:",
  "  1. goc verb='show' (or scan the deck) — does a card already cover this?",
  "  2. If not, file it via goc verb='new' args=[<title>]. The user's words ARE the briefing.",
  "  3. Claim with goc verb='status' args=[<title>, 'active'].",
  "  4. Implement the work.",
  "  5. Close with goc verb='done' args=[<title>] (DoD-gated). Then commit work + closure.",
  "DO NOT announce card operations to the user (\"I'll file a card now…\", \"closing the card…\").",
  "The user is a vibe coder; they see code, not bookkeeping.",
].join("\n");

const PATTERN_REMINDER =
  "[GoC | pattern-check] Before yielding: did your recent change touch a pattern with broader applicability? " +
  "If yes, file a generalization card via goc verb='new' before stopping. " +
  'If no generalization is warranted, respond "no generalization needed" and stop.';

const CODE_MUTATING_TOOLS = new Set(["Edit", "Write"]);
const BASH_COMMIT_PATTERNS = [/\bgit\s+commit\b/, /\bgit\s+add\s+[-.]/];

async function pathExists(p: string): Promise<boolean> {
  try {
    await access(p);
    return true;
  } catch {
    return false;
  }
}

async function isOptedOut(projectDir: string): Promise<boolean> {
  const configPath = resolve(projectDir, ".game-of-cards", "config.yaml");
  try {
    const text = await readFile(configPath, "utf8");
    return /pattern_generalization_check\s*:\s*false/i.test(text);
  } catch {
    return false;
  }
}

// === Plugin entry ===

export default definePluginEntry({
  id: "game-of-cards",
  name: "Game of Cards",
  description:
    "Agile work-card methodology for AI-agent collaborators. Files, advances, and closes cards in `.game-of-cards/deck/` via the bundled goc engine.",

  register(api: any) {
    // session_start captures the host-side project root here so the goc
    // tool handler can fall back to it when the agent-supplied cwd is a
    // sandbox-internal path that does not exist on the host (e.g. a
    // Slack-bridged subagent passing "/workspace"). Without this, Node
    // raises `spawn python3 ENOENT` for the missing cwd, which reads
    // misleadingly as "python3 is not installed".
    let sessionProjectDir: string | undefined;

    // === goc tool ===
    // Subprocess invocation routes through the sanctioned
    // api.runtime.system.runCommandWithTimeout API. Defined inside
    // register so it captures the runtime helper in its closure;
    // OpenClaw's safe-install policy blocks plugins that directly
    // import the Node stdlib subprocess module.
    //
    // SDK contract (verified against openclaw/dist/exec-Kfr6njO_.js):
    //   - signature: runCommandWithTimeout(argv, optionsOrTimeout) at :165
    //     (single argv array; argv[0] is the binary, rest are args)
    //   - result schema: { code, signal, stdout, stderr, ... } at :306
    //     (exit code field is `code`, not `exitCode`)
    async function runGoc(args: string[], cwd: string): Promise<{
      exitCode: number;
      stdout: string;
      stderr: string;
    }> {
      const env = {
        ...process.env,
        PYTHONPATH: process.env.PYTHONPATH
          ? `${VENDORED_GOC_PATH}:${process.env.PYTHONPATH}`
          : VENDORED_GOC_PATH,
      };
      const result = await api.runtime.system.runCommandWithTimeout(
        ["python3", "-m", "goc.cli", ...args],
        { cwd, env, timeoutMs: 60_000 },
      );
      return {
        exitCode:
          (result?.code as number | undefined) ??
          (result?.exitCode as number | undefined) ??
          0,
        stdout: (result?.stdout as string | undefined) ?? "",
        stderr: (result?.stderr as string | undefined) ?? "",
      };
    }

    api.registerTool({
      name: "goc",
      description:
        "Game of Cards deck CLI. Files, advances, decides on, or closes cards in `.game-of-cards/deck/`. " +
        "The deck is a backlog-as-folder where each task is a directory with frontmatter, body, and Definition-of-Done checklist that gates closure. " +
        "Common verbs: `new` (file a card), `status` (claim or block), `done` (close, DoD-enforced), `decide` (record decision, lower gate), `show` (read full card), `triage` (list parked cards by gate).",
      parameters: GocToolParams,
      async execute(_id: any, params: GocToolInput) {
        const requestedCwd = params.cwd ?? sessionProjectDir ?? process.cwd();
        let cwd = requestedCwd;
        let cwdNotice = "";
        if (!(await pathExists(cwd))) {
          for (const candidate of [sessionProjectDir, process.cwd()]) {
            if (!candidate || candidate === cwd) continue;
            if (await pathExists(candidate)) {
              cwdNotice = `[goc plugin] requested cwd "${requestedCwd}" does not exist on host; using "${candidate}" instead.`;
              cwd = candidate;
              break;
            }
          }
        }
        const argv = buildArgs(params);
        const result = await runGoc(argv, cwd);
        const stderrPieces = [cwdNotice, result.stderr].filter(Boolean);
        const stderrJoined = stderrPieces.join("\n");
        const text =
          (result.stdout + (stderrJoined ? `\n${stderrJoined}` : "")).trim() ||
          `goc ${params.verb} returned exit ${result.exitCode}`;
        return {
          content: [{ type: "text", text }],
          isError: result.exitCode !== 0,
        };
      },
    });

    // --- session_start: active-card reminder (was deck_session_start.py) ---
    // TODO(verify-context-shape): the session_start handler context is not
    // documented at https://docs.openclaw.ai/plugins/hooks.md beyond
    // "track session lifecycle boundaries". The fields used below
    // (ctx.projectDir, ctx.notify) are reasonable guesses based on the
    // SDK overview — confirm against the actual SDK types when running
    // npm install openclaw.
    api.on("session_start", async (ctx: any) => {
      const projectDir = (ctx?.projectDir as string | undefined) ?? process.cwd();
      sessionProjectDir = projectDir;
      const deckDir = await resolveDeckDir(projectDir);
      const active = await findActiveCards(deckDir);
      const resumable = active
        .filter((c) => c.humanGate === "none" && !c.impeded)
        .map((c) => c.name);
      const parkedGate = active
        .filter((c) => !c.impeded && c.humanGate !== "none")
        .map((c) => c.name);
      const impeded = active.filter((c) => c.impeded).map((c) => c.name);
      const messages: string[] = [];
      if (resumable.length > 0) {
        messages.push(
          `[GoC] Active card(s): ${resumable.join(", ")} — resume or close before starting new work.`,
        );
      }
      if (parkedGate.length > 0) {
        messages.push(
          `[GoC] Parked active card(s) (awaiting human): ${parkedGate.join(", ")} — agent cannot resume.`,
        );
      }
      if (impeded.length > 0) {
        messages.push(
          `[GoC] Impeded active card(s) (waiting_on): ${impeded.join(", ")} — agent cannot resume.`,
        );
      }
      for (const message of messages) {
        if (typeof ctx?.notify === "function") {
          ctx.notify(message);
        } else if (typeof ctx?.appendSystemContext === "function") {
          ctx.appendSystemContext(message);
        }
      }
    });

    // --- before_prompt_build: deck-first reminder (was deck_prompt_router.py) ---
    // Per https://docs.openclaw.ai/plugins/hooks.md, before_agent_run runs
    // AFTER prompt construction, so it cannot inject system context. The
    // right hook is before_prompt_build, which exposes
    // appendSystemContext / prependSystemContext / systemPrompt.
    api.on("before_prompt_build", async (ctx: any) => {
      const prompt = ((ctx?.userPrompt as string | undefined) ?? "").toLowerCase();
      if (!prompt) return;
      const hasWork = WORK_INITIATING.some((re) => re.test(prompt));
      const hasExploration = EXPLORATION.some((re) => re.test(prompt));
      const hasTooling = TOOLING.some((re) => re.test(prompt));
      if ((hasExploration || hasTooling) && !hasWork) return;
      if (!hasWork) return;
      if (typeof ctx?.appendSystemContext === "function") {
        ctx.appendSystemContext(DECK_REMINDER);
      } else if (typeof ctx?.prependSystemContext === "function") {
        ctx.prependSystemContext(DECK_REMINDER);
      }
    });

    // --- agent_end: pattern-generalization self-assessment ---
    // (was pattern_generalization_check.py)
    //
    // `agent_end` is in OpenClaw's CONVERSATION_HOOK_NAMES list (see
    // node_modules/openclaw/dist/types-CdFhLeaX.js). For non-bundled
    // plugins, OpenClaw silently drops conversation-hook registrations
    // unless the operator opts in. To enable this hook, add to OpenClaw
    // config (~/.openclaw/config.json5 or workspace config):
    //
    //   plugins:
    //     entries:
    //       game-of-cards:
    //         hooks:
    //           allowConversationAccess: true
    //
    // Opt-out per workspace via .game-of-cards/config.yaml
    //   hooks:
    //     pattern_generalization_check: false
    api.on("agent_end", async (ctx: any) => {
      const projectDir = (ctx?.projectDir as string | undefined) ?? process.cwd();
      if (await isOptedOut(projectDir)) return;
      if (ctx?.config?.pattern_generalization_check === false) return;

      // TODO(verify-context-shape): agent_end is documented as observing
      // "final messages, success state, and run duration" but the precise
      // shape of tool-call metadata is not on the hooks page. Try
      // ctx.toolCalls then ctx.events.toolCalls.
      const toolCalls: any[] = ctx?.toolCalls ?? ctx?.events?.toolCalls ?? [];
      const mutating = toolCalls.some((tc: any) => {
        if (CODE_MUTATING_TOOLS.has(tc?.name)) return true;
        if (tc?.name === "exec" || tc?.name === "Bash") {
          const cmd = (tc?.params?.command ?? tc?.params?.cmd ?? "") as string;
          return BASH_COMMIT_PATTERNS.some((re) => re.test(cmd));
        }
        return false;
      });
      if (!mutating) return;
      if (typeof ctx?.notify === "function") {
        ctx.notify(PATTERN_REMINDER);
      } else if (typeof ctx?.appendSystemContext === "function") {
        ctx.appendSystemContext(PATTERN_REMINDER);
      }
    });
  },
});
