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
  "wait",
  "advance",
  "unadvance",
  "repair-edges",
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
const ISO_DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
const ISO_DATETIME_UTC_RE = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/;
// Mirrors `goc._vendor.yaml_lite._NULL_SET` (and the Python hook's `_NULL_SET`):
// explicit YAML null literals that resolve to absent, so `waiting_on: null` / `~`
// reads as "no reason", not the truthy string "null".
const NULL_LITERALS = new Set(["null", "Null", "NULL", "~"]);
// Mirrors `goc._vendor.yaml_lite._TRUE_SET` / `_FALSE_SET` / `_INT_RE` (and the
// Python hook's same-named constants): tokens the yaml-lite parser coerces away
// from `str` (to bool / int). The engine's `Card.waiting_on` drops a non-`str`
// value via `isinstance(v, str)`, so the `waiting_on` read resolves these to ""
// too — see `cardWaitingOn`.
const BOOL_LITERALS = new Set(["true", "True", "TRUE", "yes", "Yes", "YES", "false", "False", "FALSE", "no", "No", "NO"]);
const INT_RE = /^-?\d+$/;

interface ActiveCard {
  name: string;
  humanGate: string;
  impeded: boolean;
}

function stripQuotes(s: string): string {
  return s.replace(/^["']|["']$/g, "");
}

function frontmatterTail(line: string): string {
  // Mirrors the Python sibling's `split(":", 1)[1]` semantic in
  // `goc/templates/hooks/deck_session_start.py` — return everything after
  // the first `:`. JS `String.prototype.split(sep, limit)` truncates the
  // result array to `limit` elements (it does NOT cap the number of
  // splits), so `split(":", 2)[1]` drops everything past the second
  // colon and corrupts colon-bearing values like ISO datetimes.
  //
  // Also strips a trailing YAML inline `# comment` from the bare scalar
  // tail, mirroring `_frontmatter_tail` in the Python hook. YAML 1.1/1.2
  // rule: a `#` terminates a bare scalar only when preceded by whitespace
  // (or at the very start), so `status: active # note` yields `'active'`
  // while `status: foo#bar` yields `'foo#bar'`.
  const i = line.indexOf(":");
  if (i < 0) return "";
  let tail = line.slice(i + 1);
  for (let j = 0; j < tail.length; j++) {
    if (tail[j] === "#" && (j === 0 || /\s/.test(tail[j - 1]))) {
      tail = tail.slice(0, j);
      break;
    }
  }
  return tail.trim();
}

function scalarOrEmpty(line: string): string {
  // Mirrors the Python hook's `_scalar_or_none`: resolve an *unquoted*
  // explicit YAML null literal on the scalar tail to "absent" (empty string)
  // so a hand-edited `waiting_on: null` / `~` reads as no impediment rather
  // than the truthy token "null". The null coercion is quote-aware —
  // yaml-lite coerces only *bare* null literals, so a quoted `"null"` stays
  // the live string the engine keeps; resolving it to "" here would diverge.
  // Used only for the `waiting_on` / `waiting_until` reads — `status` /
  // `human_gate` keep the raw tail, matching the Python hook, which routes
  // only the two waiting fields through `_scalar_or_none`.
  const raw = frontmatterTail(line);
  const quoted = raw[0] === '"' || raw[0] === "'";
  const value = quoted ? stripQuotes(raw) : raw;
  if (value === "") return "";
  if (!quoted && NULL_LITERALS.has(value)) return "";
  return value;
}

function waitingOnScalar(line: string): string {
  // Scoped narrowing beyond scalarOrEmpty for the `waiting_on` read only:
  // the engine's Card.waiting_on drops any *unquoted* value the yaml-lite
  // parser coerces away from `str` via `isinstance(v, str)`, so a null/bool
  // literal (null/true/yes/false/no …) or an integer token reads as "" (no
  // reason) here too. The coercion is quote-aware: a quoted `"true"` / `"42"`
  // / `"null"` is parsed as a live string reason the engine keeps, so it must
  // not be coerced. The `waiting_until` read keeps scalarOrEmpty — the
  // engine's waiting_until property has no isinstance guard, so its
  // unparseable backstop must still see the raw token.
  const raw = frontmatterTail(line);
  const quoted = raw[0] === '"' || raw[0] === "'";
  const value = quoted ? stripQuotes(raw) : raw;
  if (value === "") return "";
  if (!quoted && (NULL_LITERALS.has(value) || BOOL_LITERALS.has(value) || INT_RE.test(value))) return "";
  return value;
}

function parseWaitingUntil(value: string): Date | null {
  // Mirrors goc.engine._waiting_until_instant: a bare date YYYY-MM-DD is
  // midnight UTC of that day; a datetime YYYY-MM-DDTHH:MM:SSZ is honored
  // at full precision so a same-day future timestamp does not collapse
  // to "today" and clear early.
  //
  // The regexes check shape only (`\d{2}` for month/day), so a
  // calendar-impossible-but-shaped value like `2026-02-30` reaches
  // Date.parse — which is lenient and ROLLS it forward (2026-02-30 ->
  // 2026-03-02) instead of rejecting it. The engine parses with the real
  // calendar (`date.fromisoformat` / `strptime` via `_is_iso_date`) and
  // rejects these, so `_waiting_until_instant` returns None and
  // `waiting_impedes` keeps the card impeded via its `until_unparseable`
  // backstop. Round-trip the parsed UTC Y-M-D against the input's date
  // prefix and return null on mismatch, matching the engine's strict
  // calendar check (a rolled-forward instant would re-admit a deferred
  // card to the queue — the bug this guards against).
  let t: number;
  if (ISO_DATETIME_UTC_RE.test(value)) {
    t = Date.parse(value);
  } else if (ISO_DATE_RE.test(value)) {
    t = Date.parse(`${value}T00:00:00Z`);
  } else {
    return null;
  }
  if (Number.isNaN(t)) return null;
  const d = new Date(t);
  const ymd =
    `${String(d.getUTCFullYear()).padStart(4, "0")}-` +
    `${String(d.getUTCMonth() + 1).padStart(2, "0")}-` +
    `${String(d.getUTCDate()).padStart(2, "0")}`;
  if (ymd !== value.slice(0, 10)) return null;
  return d;
}

function isImpeded(waitingOn: string, waitingUntil: string, now: Date): boolean {
  // Mirrors goc.engine.waiting_impedes across the waiting_on ×
  // waiting_until matrix at full UTC timestamp precision (matching
  // engine._waiting_until_instant). The engine gates on `reason is not
  // None` — any non-empty waitingOn (canonical *or* hand-edited /
  // typo'd) impedes unless waitingUntil is elapsed. An elapsed
  // waitingUntil resurfaces the card even when waitingOn is set
  // (engine contract). A present-but-unparseable waitingUntil with no
  // waitingOn hits the engine's `until_unparseable` backstop (impede,
  // don't silently un-defer) — `goc validate` is the upstream net;
  // this is the read-time guard for pre-validate / hand-edited decks.
  let untilDt: Date | null = null;
  let untilUnparseable = false;
  if (waitingUntil !== "") {
    untilDt = parseWaitingUntil(waitingUntil);
    if (untilDt === null) untilUnparseable = true;
  }
  const untilFuture = untilDt !== null && untilDt.getTime() > now.getTime();
  if (waitingOn !== "") {
    if (untilDt !== null && !untilFuture) return false;
    return true;
  }
  if (untilDt === null) return untilUnparseable;
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
        status = stripQuotes(frontmatterTail(line));
      } else if (line.startsWith("human_gate:")) {
        const val = stripQuotes(frontmatterTail(line));
        if (val) humanGate = val;
      } else if (line.startsWith("waiting_on:")) {
        waitingOn = waitingOnScalar(line);
      } else if (line.startsWith("waiting_until:")) {
        waitingUntil = scalarOrEmpty(line);
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
// WORK_VERBS is the single source-of-truth verb list — keep in sync with the
// Python hook's WORK_VERBS constant.
const WORK_VERBS =
  "add|build|change|create|delete|extract|fix|implement|" +
  "introduce|move|refactor|remove|rename|update|write";

const WORK_INITIATING = [
  new RegExp(String.raw`\blet'?s\s+(do|make|ship|${WORK_VERBS})\b`, "i"),
  new RegExp(String.raw`\b(${WORK_VERBS})\s+\w`, "i"),
  new RegExp(String.raw`\b(${WORK_VERBS})\s+(a|an|the|this|that|some)\b`, "i"),
  /\bi\s+(want|need)\s+(to|a|an|the|this)\b/i,
  /\bwe\s+(need|should|want)\s+to\b/i,
  new RegExp(String.raw`\bcan\s+you\s+(${WORK_VERBS})\b`, "i"),
  new RegExp(String.raw`\bplease\s+(${WORK_VERBS})\b`, "i"),
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
  'If NO, respond "no generalization needed" and stop. ' +
  "If YES, dedup first (scan the deck): if a generalization/root card already exists, " +
  "CONNECT this instance to it (cross-reference or an advances edge) and name it — " +
  "do not file a duplicate; only if none exists, file a new card via goc verb='new'.";

const CODE_MUTATING_TOOLS = new Set(["Edit", "Write", "NotebookEdit"]);

// Broad-staging flags for `git add`: short single-letter forms plus their
// long-form aliases documented in `git-add(1)`. The bare `.` pathspec is
// handled separately as a non-flag token.
const BROAD_STAGING_FLAGS = new Set([
  "-A",
  "-p",
  "-u",
  "--all",
  "--update",
  "--patch",
]);

// Minimal shell tokenizer mirroring `shlex.split(..., posix=True)` for the
// command strings we care about: handles single/double quotes and
// backslash escapes. Returns null on unbalanced quotes so the caller can
// fall through to "not a mutation".
function shellSplit(s: string): string[] | null {
  const tokens: string[] = [];
  let current = "";
  let started = false;
  let inSingle = false;
  let inDouble = false;
  let escaped = false;
  for (const ch of s) {
    if (escaped) {
      current += ch;
      started = true;
      escaped = false;
      continue;
    }
    if (ch === "\\" && !inSingle) {
      escaped = true;
      continue;
    }
    if (ch === "'" && !inDouble) {
      inSingle = !inSingle;
      started = true;
      continue;
    }
    if (ch === '"' && !inSingle) {
      inDouble = !inDouble;
      started = true;
      continue;
    }
    if (!inSingle && !inDouble && /\s/.test(ch)) {
      if (started) {
        tokens.push(current);
        current = "";
        started = false;
      }
      continue;
    }
    current += ch;
    started = true;
  }
  if (inSingle || inDouble) return null;
  if (started) tokens.push(current);
  return tokens;
}

// Match `git commit ...` (any form) and `git add` with one of the broad-
// staging flags in BROAD_STAGING_FLAGS or the bare `.` pathspec.
// Deliberately reject `git add -- <path>` and bare `git add <path>`: those
// stage explicit paths and are the documented safe parallel-agent staging
// idiom in AGENTS.md.
function isBroadGitMutation(cmd: string): boolean {
  const tokens = shellSplit(cmd);
  if (!tokens || tokens.length < 2 || tokens[0] !== "git") return false;
  if (tokens[1] === "commit") return true;
  if (tokens[1] !== "add") return false;
  for (const tok of tokens.slice(2)) {
    if (tok === "--") return false;
    if (tok === "." || BROAD_STAGING_FLAGS.has(tok)) return true;
  }
  return false;
}

async function pathExists(p: string): Promise<boolean> {
  try {
    await access(p);
    return true;
  } catch {
    return false;
  }
}

async function hasDeck(projectDir: string): Promise<boolean> {
  return (
    (await pathExists(resolve(projectDir, ".game-of-cards", "deck"))) ||
    (await pathExists(resolve(projectDir, "deck")))
  );
}

function fallbackProjectCandidates(sessionProjectDir?: string): string[] {
  const candidates = [
    sessionProjectDir,
    process.env.OPENCLAW_WORKSPACE_DIR,
    process.env.OPENCLAW_WORKSPACE,
    process.env.HOME ? resolve(process.env.HOME, ".openclaw", "workspace") : undefined,
    process.cwd(),
  ];
  return [...new Set(candidates.filter(Boolean) as string[])];
}

async function bestFallbackProjectDir(sessionProjectDir?: string): Promise<string | undefined> {
  const candidates = fallbackProjectCandidates(sessionProjectDir);
  for (const candidate of candidates) {
    if (await hasDeck(candidate)) return candidate;
  }
  for (const candidate of candidates) {
    if (await pathExists(candidate)) return candidate;
  }
  return undefined;
}

// Opt-in (default off): the GoC project config must explicitly enable the
// hook. Absent config, absent key, or any other value leaves it disabled.
async function isEnabled(projectDir: string): Promise<boolean> {
  const configPath = resolve(projectDir, ".game-of-cards", "config.yaml");
  try {
    const text = await readFile(configPath, "utf8");
    return /pattern_generalization_check\s*:\s*true/i.test(text);
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
          const candidate = await bestFallbackProjectDir(sessionProjectDir);
          if (candidate && candidate !== cwd) {
            cwdNotice = `[goc plugin] requested cwd "${requestedCwd}" does not exist on host; using "${candidate}" instead.`;
            cwd = candidate;
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
    // Opt-in per workspace via .game-of-cards/config.yaml (default off)
    //   hooks:
    //     pattern_generalization_check: true
    api.on("agent_end", async (ctx: any) => {
      const projectDir = (ctx?.projectDir as string | undefined) ?? process.cwd();
      // Run only when explicitly enabled, via either the GoC project config
      // file or the OpenClaw plugin config.
      if (!(await isEnabled(projectDir)) &&
          ctx?.config?.pattern_generalization_check !== true) return;

      // TODO(verify-context-shape): agent_end is documented as observing
      // "final messages, success state, and run duration" but the precise
      // shape of tool-call metadata is not on the hooks page. Try
      // ctx.toolCalls then ctx.events.toolCalls.
      const toolCalls: any[] = ctx?.toolCalls ?? ctx?.events?.toolCalls ?? [];
      const mutating = toolCalls.some((tc: any) => {
        if (CODE_MUTATING_TOOLS.has(tc?.name)) return true;
        if (tc?.name === "exec" || tc?.name === "Bash") {
          const cmd = (tc?.params?.command ?? tc?.params?.cmd ?? "") as string;
          return isBroadGitMutation(cmd);
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
