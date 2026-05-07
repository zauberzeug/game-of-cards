---
title: redesign-readme-as-llm-first-marketing-page
summary: "Redesign README.md as the public marketing surface: comic above the fold, LLM-first install prompt, brief 'how it works' with the YOU→skills→LLM→goc→Cards diagram, with CLI detail and methodology context exiled to root-level goc.md and ABOUT.md. Pages workflow extended to also publish raw /llms.txt, /index.md, /README.md, /goc.md, and /ABOUT.md alongside the rendered HTML."
status: done
stage: null
contribution: high
created: 2026-05-05
closed_at: 2026-05-05
human_gate: none
advances:
  - build-game-of-cards-project-website
advanced_by: []
tags: [documentation, story]
definition_of_done: |
  - [x] README.md leads with the 4-panel comic and a one-line tagline; CLI is mentioned exactly once with a link to `goc.md`
  - [x] "Try it" section sits above the fold with the LLM install prompt and a single mention that bootstrapping flows from the PyPI package `game-of-cards`
  - [x] "How it works" replaces "What you get"; embeds `assets/how-it-works.png` and explains skills as the human↔LLM UI and `goc` as the LLM↔cards tool
  - [x] Agile lineage, ecosystem comparison, and the Game-of-Thrones name rationale live in a new root-level `ABOUT.md`, linked from README's "More" section
  - [x] Root-level `goc.md` exists, holding the CLI reference and manual install recipe (content moved from `docs/cli.md`); README links to `goc.md`, not `docs/cli.md`
  - [x] Pages workflow renders HTML for `/`, `/goc/`, and `/about/` (semantic markup, CSS-only styling) AND publishes raw markdown at `/index.md`, `/README.md`, `/goc.md`, `/ABOUT.md`, plus a curated `/llms.txt`
  - [x] `assets/` is copied into the rendered site so `![](assets/...)` images resolve from the same path on GitHub and on game-of-cards.com (single-source-of-truth invariant preserved)
  - [x] Internal markdown links in README rewrite cleanly on the rendered site (`goc.md` → `/goc/`, `ABOUT.md` → `/about/`, repo-relative non-rendered files → absolute GitHub blob URLs)
  - [x] `uv run goc validate` passes
---

# Redesign README as an LLM-first marketing page

## Why

The current README is a feature catalog: 130 lines that lead with positioning prose and bury the install prompt under a "Try it" section halfway down. That ordering serves *contributors* who need the methodology context but mis-serves the two audiences the public page is for:

- **Humans evaluating the project** — they want the comic, the install path, and a one-glance "how it works." Lineage and ecosystem comparison belong below the fold or behind a link.
- **LLMs scanning the site to install it** — they want a curated, copy-pasteable prompt and a direct link to a CLI reference. They don't need the agile-methodology essay.

## Decision (already recorded on `build-game-of-cards-project-website`)

README is the single source of truth for the marketing surface; the website renders it. This card preserves that invariant — README is rewritten in place, and the workflow is extended to publish both styled HTML and raw markdown from the same source.

## What changes

- `README.md` rewritten in the new structure (comic hero → tagline → Try it → How it works → Status → More → License)
- `goc.md` created at repo root (content moved from `docs/cli.md`; `docs/cli.md` removed since the only README link gets rewritten)
- `ABOUT.md` created at repo root, holding the Game-of-Thrones name rationale, the agile lineage that used to be in README's body, and the ecosystem comparison
- `.github/workflows/pages.yml` extended to render HTML pages for `/`, `/goc/`, `/about/` AND drop raw markdown mirrors + a curated `/llms.txt` into the build directory before upload

## How the LLM-friendly side works

GitHub Pages is static hosting, so we cannot do User-Agent content negotiation at the edge. The workflow instead writes both shapes from the same sources:

- Jekyll renders the markdown sources to semantic HTML for `/`, `/goc/`, `/about/`. CSS does the styling — no JS components, so the rendered HTML stays usable to LLMs that fetch it.
- After Jekyll's build step, a follow-up step copies raw markdown into `_site/` at fixed paths: `/index.md`, `/README.md`, `/goc.md`, `/ABOUT.md`. These serve as `text/markdown` since they have no Jekyll front matter at the served path.
- `/llms.txt` is a curated, terse markdown summary listing what the project is, how to install, and where the other documents live. Follows the emerging llmstxt.org convention.

## Notes

- The comic still has unresolved review issues (apostrophes, missing graph legend, methodology vocabulary). Those are tracked separately on `create-project-website-explanatory-illustration` and don't block this redesign — the redesign promotes the comic as it currently stands; subsequent comic iterations flow through automatically.
- The website card `build-game-of-cards-project-website` has DoD items that this redesign substantially advances. After this card closes, the website card's "First viewport" and "Reserves integration point for illustration" boxes are also satisfied; the remaining items there are deploy-time visual checks.
