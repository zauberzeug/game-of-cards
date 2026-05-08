## 2026-05-08 — Closure

Added `site/privacy.html` mirroring the homepage shell (`styles.css`, header, footer, starfield, Plausible loader). Five sections: plugin/CLI handling (verifiable zero-collection claim), marketing site disclosure (Plausible cookieless analytics), hosting (GitHub Pages logging notice with link to GitHub's own privacy statement), contact (info@zauberzeug.com + GitHub issues), updates (versioned in repo). Footer link added on `site/index.html` so the page is discoverable from the homepage too.

Pages deploy run **25571951008** finished `success` on commit `c961f18`. Live URL `https://game-of-cards.com/privacy.html` returns `HTTP/2 200` from GitHub.com. Rodja eyeballed the rendered page in-browser and signed off before close.

This unblocks the "Privacy policy URL" field on the Anthropic community plugin directory submission form. The marketplace card (`list-game-of-cards-on-anthropic-community-marketplace`) gains another closed prereq; the only remaining DoD items there are user-only steps (open the form, submit, post-merge docs sweep).

## Closure verification (2026-05-08)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — all 1 done
- [x] dod-100-percent — 7/7 ticked
- [x] log-md-closure-entry — '## 2026-05-08 — Closure' present
