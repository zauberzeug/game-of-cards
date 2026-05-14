## 2026-05-14: decision recorded

Add skills_source key (plugin|vendored|auto) to .game-of-cards/config.yaml; default for new installs and unset-key reads is 'auto' which performs real plugin-presence detection — config.yaml already holds project state and the existing audience reads it; skills_source matches the noun it controls; 'auto' that actually auto-detects matches its name, and the safer-default reading was rejected — existing repos transitioning to plugin-mode will benefit from detection rather than continuing the wrong behavior. Gate decision → none.
