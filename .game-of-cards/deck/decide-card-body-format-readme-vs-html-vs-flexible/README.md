---
title: decide-card-body-format-readme-vs-html-vs-flexible
summary: "Today every card body is markdown (`README.md`). A linked argument (https://x.com/i/status/2052809885763747935, screencap captured in this card's body) makes the case that HTML beats markdown for *Claude-generated artifacts that humans consume* — information density, visual clarity, ease of sharing, two-way interactive forms, and aesthetic richness. The framing question for the deck: do cards count as 'artifacts for humans' or as 'work tickets for agents'? Three candidate answers: (a) keep enforcing markdown — cards are work tickets that agents read and edit, markdown is universal; (b) switch to HTML — adopt the article's case wholesale; (c) leave the body format open via file-extension dispatch, with markdown as the default and HTML as an opt-in for projects that want it. Decision-gated; pairs with `split-card-frontmatter-from-body` because format flexibility becomes much cheaper if metadata lives in its own file."
status: disproved
stage: null
contribution: medium
created: 2026-05-09
closed_at: 2026-05-09T05:41:30Z
human_gate: none
advances: []
advanced_by:
  - split-card-frontmatter-from-body
tags: [story, infra, documentation]
definition_of_done: |
  - [ ] Decision recorded on this card: keep markdown / switch to HTML / leave format flexible.
  - [ ] If keep markdown: card closed `disproved` with the reasoning recorded — explicitly addressing why the article's case (information density, sharing, interactivity) does or does not transfer to *work-ticket* cards.
  - [ ] If switch to HTML: a migration plan exists (one-shot tool that converts each card body), templates updated, engine rendering / `goc show` updated to handle HTML, GitHub repo browsing UX validated.
  - [ ] If leave format flexible: file-extension dispatch defined (`README.md` → markdown, `card.html` → HTML, etc.), templates and `goc new` accept a `--body-format` flag, schema documents the contract, default stays markdown.
  - [ ] Pairs with `split-card-frontmatter-from-body`: if that decision lands "split", flexibility on the body extension is a one-line change in the engine; if it lands "stay", body-format flexibility requires bespoke fence-aware logic — call this out explicitly in the chosen decision.
---

# decide-card-body-format-readme-vs-html-vs-flexible

## Status quo

Every card body is markdown:

```
.game-of-cards/deck/<title>/README.md
```

The body content is unconstrained markdown. Cards render natively
on GitHub, in IDE markdown previews, in Claude Code, and in any
editor that handles `.md`.

## The HTML argument (article: "Using Claude Code: The Unreasonable Effectiveness of HTML")

Source: https://x.com/i/status/2052809885763747935. Paywalled —
screencap captured in this repo. The article's case (synthesized,
not quoted) is **not** that LLMs read HTML better than markdown. It
is that **HTML is the better output format for artifacts Claude
Code produces for humans to consume**. Five claims:

1. **Information density.** HTML+CSS can render structured content
   (color swatches with their hex values, tables with visual
   grouping, side-by-side comparisons, embedded charts) that
   degrades to a wall of text in markdown. The example given:
   nine named colors with hex codes — markdown shows the text;
   HTML shows the actual colors next to the text.

2. **Visual clarity.** Layout, typography, and spatial cues that
   markdown can't express (multi-column layouts, callout boxes,
   visual hierarchy beyond headings) are first-class in HTML.

3. **Ease of sharing.** A markdown file requires a renderer; an
   HTML file opens in any browser anywhere. Drop it on S3, send
   the link, anyone can view it without tooling.

4. **Two-way interaction.** HTML supports forms, sliders, inputs,
   buttons. Claude Code can produce a feedback form or a small
   interactive interface that the human fills in, and the response
   feeds back into the next turn. Markdown is read-only by nature.

5. **Aesthetics / joy.** Embedded images, emojis, custom styling,
   creative layouts — HTML is a creative outlet. The author claims
   this materially improves the artifact-production experience.

The author's own usage rule: HTML for almost everything Claude
Code produces; markdown remains for code blocks, terminal output,
and inline tool snippets. The author claims the per-token
information density advantage of HTML offsets its higher byte
count.

## Does the argument apply to GoC cards?

This is the framing question the decider has to answer. The
article is about *Claude-generated artifacts for human
consumption* — reports, mockups, planning documents, dashboards,
custom editing UIs. The argument's leverage points (visual
density, interactivity, easy sharing) are all about an
end-user-facing artifact.

**GoC cards are a different artifact class:**

- Cards are *work tickets* in a kanban deck. Both humans (PO,
  contributor) and agents (autonomous workers) read and edit
  them.
- The primary consumer is often an *agent* picking up the card
  from the queue. Agents read markdown fluently; the
  information-density gains of HTML accrue to humans, not to
  the agent's context.
- Cards live in `git` and render in `github.com` directory
  views. `README.md` auto-renders inline; `card.html` would
  display as raw HTML source unless the viewer downloads and
  opens it locally.
- Cards are short-lived in attention but persistent on disk.
  They're more like Jira tickets than like polished reports.
  The article's case for HTML is strongest for polished reports.

But not nothing transfers:

- A card body that includes a colored kanban diagram, a state
  diagram, a graph of `advances` edges, or a side-by-side
  before/after of code — those would benefit from HTML
  exactly the way the article describes.
- Decision cards (this card!) sometimes carry a comparison
  matrix, a table of options, or an embedded screenshot. HTML
  could make those richer.
- Two-way interaction (the article's most novel claim) could be
  used in `human_gate: decision` cards: an embedded form the
  human fills out to record the decision. That's a real
  workflow improvement, not just aesthetics.

## The "leave it flexible" option

A third path: enforce no specific body format. Dispatch by file
extension:

| File on disk | Renderer |
|---|---|
| `README.md` | markdown (today's behavior, default) |
| `card.html` | HTML |
| `card.txt` | plain text |
| (others) | declined; use one of the supported set |

`goc new` accepts `--body-format md|html|txt`. Engine `goc show`
detects extension. Schema documents the contract. Per-project
preference becomes a one-line config (`config.yaml: body_format:
html`).

This option becomes substantially cheaper if
`split-card-frontmatter-from-body` lands "split" — body file is
already separate, extension detection is trivial. Without the
split, body format flexibility means the parser has to fence-aware
detect "where does the frontmatter end" for non-markdown bodies
too, which complicates the vendored YAML parser's scope.

## Three candidate answers

1. **Keep markdown enforced.** Status quo. No work, no breaking
   changes. Markdown is universal, agent-readable, and renders
   inline on `github.com`. The article's argument is about
   end-user-facing artifacts, not work-ticket cards — the framing
   doesn't fully transfer. Closes this card `disproved` with the
   reasoning recorded.

2. **Switch to HTML enforced.** All cards become HTML. One-shot
   migration tool converts every existing card body. Templates,
   `goc new`, `goc show` all update. Breaking change for every
   consumer repo. Adopts the article's case wholesale and bets
   that the visual-density / interactivity / sharing arguments
   apply to cards too. Loses the inline-render-on-GitHub UX.

3. **Leave it flexible.** Engine accepts multiple body formats
   via extension dispatch. Default stays `README.md` (markdown,
   no migration, agent-friendly, GitHub-rendered). Projects or
   individual cards opt in to `card.html` when the body really
   benefits from visual density or interactive forms (e.g. a
   decision card with an embedded answer form, a card carrying
   a colored state diagram, a card with side-by-side comparison
   tables). `goc show` detects extension and renders accordingly.
   Cost: doubled test matrix (each format must work end-to-end);
   schema documents the supported set; `--body-format` flag on
   `goc new`.

Recommendation framing (not a verdict): option 3 captures the
interesting parts of the article's argument *without* forcing
every work-ticket-style card to pay the HTML cost. The
"interactive decision form" use case in particular maps cleanly
onto `human_gate: decision` cards — that's a workflow win, not
just aesthetics. But it doubles the engine's responsibilities
and cost has to be weighed.

## Interaction with `split-card-frontmatter-from-body`

If that decision lands "split", body format flexibility costs
one line of engine logic (extension dispatch on the body file).
If it lands "stay", flexibility means the YAML fence parser has
to handle non-markdown bodies — much more complex. So the order
of decisions matters: decide split-frontmatter first, then this
card.

## Decision needed

Capture the X-post argument in your own words first (so a future
reader doesn't depend on the paywalled link), then choose:
markdown / HTML / flexible. If flexible, also confirm the
supported extensions and the per-project config knob.

## Decision

*Resolved 2026-05-09:* keep markdown for README.md; rich artifacts (HTML, SVG, interactive forms) ship as sibling files in the card directory referenced from the README — same bundle shape as reproduce.py; close as disproved

*Reasoning:* article's strongest cases (interactive decision-gate forms, colored option matrices, state diagrams) genuinely transfer for ~10–20% of cards but are best served by per-card artifact bundling, not a body_format dispatch field; pattern documented in card-skills-document-html-as-sibling-artifact-pattern; preserves GitHub inline rendering of READMEs and avoids coupling to the split-frontmatter decision
