---
title: add-privacy-policy-page-for-marketplace-submission
summary: "The Anthropic community plugin directory submission form has a 'Privacy policy URL' field. The marketing site (`game-of-cards.com`) currently has no privacy page — the homepage uses Plausible Analytics (added by `add-plausible-analytics-to-marketing-site`) but neither the website nor the plugin's data handling is documented anywhere user-facing. Add `site/privacy.html` so the form has a stable URL to point at, and the page itself honestly describes the two surfaces: (a) the GoC plugin and `goc` CLI, which are fully local and make zero network calls, no telemetry, no analytics; (b) the marketing site, which uses Plausible (cookieless, GDPR-friendly, no IP retention). The page must match the existing site's visual style (header / footer / starfield / styles.css) and deploy via the same GitHub Pages workflow that ships the rest of `site/`."
status: active
stage: null
contribution: low
created: 2026-05-08
closed_at: null
human_gate: none
advances:
  - list-game-of-cards-on-anthropic-community-marketplace
advanced_by:
  - add-plausible-analytics-to-marketing-site
tags: [documentation, infra]
definition_of_done: |
  - [ ] `site/privacy.html` exists, renders cleanly via the same Pages deploy as `site/index.html` (matching header, footer, starfield, `styles.css`)
  - [ ] Plugin / CLI section honestly states: zero data collection, no telemetry, no network calls, all cards are local files. This is a verifiable claim — `grep -n "import socket\|import urllib\|import requests\|import http" goc/*.py` returns nothing
  - [ ] Marketing site section discloses Plausible Analytics with a link to Plausible's own privacy policy and the key facts (no cookies, no IP retention, no third-party sharing)
  - [ ] Page is reachable at `https://game-of-cards.com/privacy.html` after the next Pages deploy
  - [ ] Footer link to `/privacy.html` added on `site/index.html` so the page is discoverable from the homepage (not only via the marketplace listing)
  - [ ] Rodja signs off on the rendered text before close (UI verification feedback)
  - [ ] `uv run goc validate` passes
worker: {who: Rodja Trappe, where: main}
---

# Add a privacy policy page for the marketplace submission

## Why

The Anthropic community plugin directory submission form requires a
privacy policy URL. The marketing site at `game-of-cards.com` does not
have one today.

The honest content is short. The plugin and CLI run entirely on the
user's machine — no network calls in `goc/*.py`, no telemetry, all
cards are local Markdown. The only data-handling component is the
marketing site itself, which loads Plausible Analytics. Plausible is
cookie-free and does not retain IP addresses, which keeps the policy
short and review-friendly.

This card files the page so the submission form can be filled in, and
adds a footer link from the homepage so the page is also discoverable
to anyone who finds it via the site rather than the marketplace.

## Out of scope

- A site-wide privacy banner / cookie consent UI. Plausible's
  cookie-free design means we do not need consent gating under GDPR
  / ePrivacy for analytics; this would be needed only if a future
  feature added cookie-based tracking, and is not blocking the
  submission.
- Translating the page. English-only is consistent with the rest of
  `site/`. If `game-of-cards.com` ever grows a localised landing
  page, this card is the precedent for parallel localised privacy
  pages.

## Cross-references

- `list-game-of-cards-on-anthropic-community-marketplace` (open,
  gate=decision) — the submission this card unblocks.
- `add-plausible-analytics-to-marketing-site` (closed) — added the
  analytics component the page now has to disclose.
