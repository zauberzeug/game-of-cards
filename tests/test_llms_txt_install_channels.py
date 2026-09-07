"""`site/llms.txt` must present every install channel it lists as available.

`site/llms.txt` is the document LLMs ingest (llmstxt.org convention) to learn
how to recommend this project, and it is what `game-of-cards.com/llms.txt`
serves. It is also the one install surface with no human reader in the loop: a
stale recipe there propagates into model answers without anyone noticing.

That is how `llms-txt-still-presents-the-clawhub-install-as-unpublished`
happened. The `## Install (OpenClaw)` section was authored while the ClawHub
publish was genuinely pending, and the "Once the plugin is published" /
"Until publish lands" caveat outlived the publish by ten releases — while
README.md, ABOUT.md, goc.md and site/index.html all printed the same install
command with no caveat at all.

Detection is precision-first, in the posture `scripts/check_card_language.py`
takes: `PENDING_PUBLISH_MARKERS` holds phrasings that are *claims about publish
state*, not stylistic preferences. A caveat spelled some other way still slips
through; the point is to make the realistic regression fail CI instead of
shipping. Nothing here is goc semantics — it guards this project's own website
copy — so it lives in `tests/`, not in the engine or a template.
"""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

LLMS_TXT = Path("site/llms.txt")

# Phrasings that tell the reader a listed channel is not installable yet.
PENDING_PUBLISH_MARKERS = (
    "Once the plugin is published",
    "Until publish lands",
    "once published",
    "not yet published",
    "once the package is published",
)

# Surfaces that advertise the OpenClaw install to humans. llms.txt is the
# machine-facing summary of these, so the command must not drift between them.
SIBLING_SURFACES = (
    Path("README.md"),
    Path("ABOUT.md"),
    Path("goc.md"),
    Path("site/index.html"),
)

CLAWHUB_INSTALL_COMMAND = "openclaw skills install game-of-cards"


class LlmsTxtInstallChannelTest(unittest.TestCase):
    def test_no_channel_is_described_as_pending_publish(self) -> None:
        text = (ROOT / LLMS_TXT).read_text(encoding="utf-8")
        lowered = text.lower()
        for marker in PENDING_PUBLISH_MARKERS:
            self.assertNotIn(
                marker.lower(),
                lowered,
                msg=(
                    f"{LLMS_TXT} describes an install channel as pending publish "
                    f"({marker!r}). Every channel llms.txt lists is live — "
                    f"remove the caveat or remove the channel."
                ),
            )

    def test_clawhub_install_command_matches_sibling_surfaces(self) -> None:
        llms = (ROOT / LLMS_TXT).read_text(encoding="utf-8")
        self.assertIn(
            CLAWHUB_INSTALL_COMMAND,
            llms,
            msg=f"{LLMS_TXT}: OpenClaw/ClawHub install command missing",
        )
        for rel in SIBLING_SURFACES:
            self.assertIn(
                CLAWHUB_INSTALL_COMMAND,
                (ROOT / rel).read_text(encoding="utf-8"),
                msg=(
                    f"{rel} no longer prints {CLAWHUB_INSTALL_COMMAND!r}; "
                    f"{LLMS_TXT} still does — the machine-facing summary has "
                    f"drifted from the human-facing surfaces."
                ),
            )

    def test_llms_txt_does_not_cite_internal_card_slugs(self) -> None:
        """A public document cannot point readers at deck-internal slugs.

        The stale caveat named `publish-openclaw-plugin` as its tracker — a
        card slug that resolves only inside this repo's deck, and which was
        itself out of date. Deck titles belong in cards, not on the website.

        Shipped skill names are exempt: llms.txt legitimately names
        `create-card` / `pull-card` / `finish-card` as product vocabulary, and
        a card slug that collides with one of them is a naming coincidence,
        not a leaked internal reference.
        """
        text = (ROOT / LLMS_TXT).read_text(encoding="utf-8")
        public_names = {
            skill.name
            for skill in (ROOT / "goc" / "templates" / "skills").iterdir()
            if skill.is_dir()
        }
        deck_dir = ROOT / ".game-of-cards" / "deck"
        cited = sorted(
            card.name
            for card in deck_dir.iterdir()
            if card.is_dir()
            and card.name not in public_names
            and f"`{card.name}`" in text
        )
        self.assertEqual(
            [],
            cited,
            msg=f"{LLMS_TXT} cites deck card slug(s) a public reader cannot resolve",
        )


if __name__ == "__main__":
    unittest.main()
