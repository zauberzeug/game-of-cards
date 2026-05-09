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
 * invocations use `api.runtime.system.runCommandWithTimeout` (the sanctioned
 * spawn API per OpenClaw's plugin-sandbox policy) — NOT direct
 * `node:child_process` imports, which the safe-install policy blocks.
 *
 * After compilation, this file lives at `<plugin-root>/dist/index.js`, so
 * the vendored engine path is computed as `dirname(__file) + "/../"`
 * (the plugin root is the parent of dist/).
 */
declare const _default: {
    id: string;
    name: string;
    description: string;
    configSchema: import("openclaw/plugin-sdk/plugin-entry").OpenClawPluginConfigSchema;
    register: NonNullable<import("openclaw/plugin-sdk/plugin-entry").OpenClawPluginDefinition["register"]>;
} & Pick<import("openclaw/plugin-sdk/plugin-entry").OpenClawPluginDefinition, "kind" | "reload" | "nodeHostCommands" | "securityAuditCollectors">;
export default _default;
