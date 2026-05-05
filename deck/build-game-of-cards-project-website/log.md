## 2026-05-05: decision recorded

Render README.md at game-of-cards.com via GitHub Pages, single-source from README — Rodja owns the domain and wants README as the single source of truth for the marketing surface, with no duplicate copy to drift. Gate session → none.

## 2026-05-05: implementation landed

`.github/workflows/pages.yml` synthesizes the Jekyll site from README.md at deploy time (drops the leading H1, rewrites repo-relative `docs/` / `goc/` / `deck/` / `assets/` / `LICENSE` links to absolute GitHub blob URLs, builds with jekyll-theme-cayman, ships a CNAME for game-of-cards.com). Card stays `active`: two DoD items remain pending verification after first deploy — (1) responsive check on desktop + mobile, (2) green workflow_dispatch run. Out-of-repo follow-ups: registrar DNS to GitHub Pages IPs, repo Settings → Pages source = "GitHub Actions".
