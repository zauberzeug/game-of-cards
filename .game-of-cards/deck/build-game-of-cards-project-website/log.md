## 2026-05-05: decision recorded

Hand-crafted static homepage at site/index.html (chronicle/serif aesthetic, dark navy + gold, starfield) replaces the Jekyll-rendered README at /; goc.md and ABOUT.md still render via Jekyll-cayman as subpages; raw markdown mirrors stay untouched for LLMs. — Rodja delivered a finished design (zip drop) with a distinct masthead and chronicle styling that the Jekyll-cayman default cannot express. README.md remains the LLM-readable canonical content (mirrored at /index.md, /README.md), so the visual surface and the LLM surface diverge by design.. Gate session → none.

## 2026-05-05: implementation landed

`site/index.html` + `site/styles.css` + `site/stars.js` shipped with chronicle masthead (Cinzel/Cormorant SC), dark navy palette, starfield canvas, and inline SVG-data joker favicon. References `assets/game-of-cards-dark.png` (comic) and `assets/how-it-works-dark.png` (how-it-works diagram) by their canonical repo names — no duplicate image bytes under `site/assets/`.

`.github/workflows/pages.yml` rewritten: removed `README.md → /` Jekyll render, added `site/**` verbatim copy step, kept `goc.md → /goc/` and `ABOUT.md → /about/` Jekyll-rendered subpages, kept raw markdown mirrors (`/index.md`, `/README.md`, `/goc.md`, `/ABOUT.md`, `/llms.txt`) for LLMs. Added `site/**` to the workflow path triggers. Asset-copy step changed from `shutil.copytree` to per-file with `dst.exists()` guard so future `site/assets/` overrides win without breaking the build. Synthesized `_pages/` dry-run verified the layout produces the expected 16+ files including raw mirrors and dark assets.

After Rodja's visual review at multiple viewports, widened the body column for less wasted side margin: `.container` max-width 820 → 1100; `.readme` max-width 720 → `clamp(720px, 70vw, 940px)`. Article width now scales fluidly from 720 (≤1030px viewport) to 940 (≥1342px viewport). Bounding-box checks at 1024/1280/1440/2560 confirm symmetric centering at every size.

## 2026-05-05: closed

DoD 8/8 satisfied. Out-of-repo follow-ups are unchanged from the v1 attempt: registrar DNS to GitHub Pages IPs, Pages source = "GitHub Actions" in repo settings, first `workflow_dispatch` run to verify deploy.
