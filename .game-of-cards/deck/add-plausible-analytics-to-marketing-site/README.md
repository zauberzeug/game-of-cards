---
title: add-plausible-analytics-to-marketing-site
summary: Inject Plausible privacy-friendly analytics snippet into site/index.html so visits to the marketing page are tracked without cookies or PII.
status: done
stage: null
contribution: low
created: 2026-05-05
closed_at: 2026-05-05
human_gate: none
advances: []
advanced_by: []
tags: []
definition_of_done: |
  - [x] Plausible loader + init shim added inside `<head>` of `site/index.html`
  - [x] data-domain / script src match the user-provided snippet (pa-BeDjiXGZwVeJ1mhrWfx0W.js)
  - [x] Page still renders (visual check) and no console errors from the snippet
---

# add-plausible-analytics-to-marketing-site

Add the Plausible analytics snippet (privacy-friendly, no cookies) to the
marketing site so we can see traffic on the GoC landing page.

The user supplied the exact snippet to use:

```html
<!-- Privacy-friendly analytics by Plausible -->
<script async src="https://plausible.io/js/pa-BeDjiXGZwVeJ1mhrWfx0W.js"></script>
<script>
  window.plausible=window.plausible||function(){(plausible.q=plausible.q||[]).push(arguments)},plausible.init=plausible.init||function(i){plausible.o=i||{}};
  plausible.init()
</script>
```

Insert just before `</head>` in `site/index.html`.
