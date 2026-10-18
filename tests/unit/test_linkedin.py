"""The LinkedIn assets, and an honesty lint over every word this project ships.

The lint is the point of this file. It is easy to be careful in the code and
then overstate the result in a caption, a slide or a social post, which is
exactly where most people will encounter it.
"""

from __future__ import annotations

import re

import pytest

from neoag.evidence.honesty import BANNED_PHRASES, check_text
from neoag.paths import Paths

ROOT = Paths().root
POST = ROOT / "linkedin" / "post.md"
POST_LIMIT = 1300


def post_body() -> str:
    """The text that would actually be pasted into LinkedIn."""
    return POST.read_text().split("---", 1)[1].strip()


class TestPost:
    def test_fits_the_character_limit(self):
        assert len(post_body()) <= POST_LIMIT

    def test_has_a_hook_takeaways_a_caveat_and_a_link(self):
        body = post_body()
        assert re.search(r"^\s*1\.", body, re.M), "no numbered takeaways"
        assert len(re.findall(r"^\s*\d\.", body, re.M)) >= 3
        assert "caveat" in body.lower()
        assert "github.com/isarinio22/moderna" in body

    def test_states_the_disclaimer(self):
        body = post_body().lower()
        assert "not medical advice" in body
        assert "not affiliated" in body

    def test_does_not_claim_phase_3_numbers(self):
        """No Phase 3 efficacy figure is public, so none may appear."""
        body = post_body().lower()
        assert "published no numbers" in body or "has published no numbers" in body

    def test_quotes_the_two_sided_p_value_alongside_the_trial_bar(self):
        """The one-sided bar must never be stated without its conventional form."""
        body = post_body()
        assert "one-sided" in body
        assert "0.053" in body


#: Every file whose words reach a reader.
PUBLIC_COPY = [
    ROOT / "README.md",
    ROOT / "DISCLAIMER.md",
    ROOT / "linkedin" / "post.md",
    ROOT / "site" / "index.html",
    ROOT / "site" / "app.js",
    ROOT / "src" / "neoag" / "figures" / "carousel.py",
    ROOT / "research" / "sources.md",
]


class TestHonestyLintOverAllCopy:
    """Every word that reaches a reader, checked for overstatement."""

    @pytest.mark.parametrize("path", PUBLIC_COPY, ids=lambda p: p.name)
    def test_no_banned_phrases(self, path):
        if not path.exists():
            pytest.skip(f"{path.name} not present")
        found = check_text(path.read_text())
        assert found == [], f"{path.name} contains {found}"

    def test_the_lint_would_catch_an_overstatement(self):
        """Guards the guard."""
        assert check_text("a breakthrough cure for cancer") == [
            p for p in BANNED_PHRASES if p in "a breakthrough cure for cancer"
        ]
        assert check_text("this is a cure for cancer")

    def test_every_public_document_carries_the_disclaimer(self):
        for path in (ROOT / "README.md", ROOT / "site" / "index.html",
                     ROOT / "linkedin" / "post.md"):
            assert "not medical advice" in path.read_text().lower(), path.name


class TestCarousel:
    def test_has_between_seven_and_nine_slides(self):
        from neoag.figures.carousel import SLIDES, TOTAL

        assert 7 <= len(SLIDES) <= 9
        assert len(SLIDES) == TOTAL

    def test_renders_at_the_linkedin_portrait_size(self, tmp_path):
        """1080x1350 is the 4:5 ratio LinkedIn renders largest in the feed."""
        from neoag.figures.carousel import DPI, H_IN, W_IN, build_pngs

        assert round(W_IN * DPI) == 1080
        assert round(H_IN * DPI) == 1350
        data = ROOT / "site" / "data"
        if not (data / "manifest.json").exists():
            pytest.skip("site/data not built")
        from PIL import Image

        first = build_pngs(data, tmp_path)[0]
        assert Image.open(first).size == (1080, 1350)

    def test_last_slide_links_the_repository(self):
        from neoag.figures import carousel

        source = (ROOT / "src" / "neoag" / "figures" / "carousel.py").read_text()
        assert carousel.SLIDES[-1].__name__ == "slide_9_repo"
        assert "github.com/isarinio22/moderna" in source

    def test_builds_a_pdf(self, tmp_path):
        from neoag.figures.carousel import build

        data = ROOT / "site" / "data"
        if not (data / "manifest.json").exists():
            pytest.skip("site/data not built")
        out = build(data, tmp_path / "carousel.pdf")
        assert out.stat().st_size > 20_000
        assert out.read_bytes()[:4] == b"%PDF"


class TestAnimation:
    def test_targets_a_playable_format(self):
        """yuv420p or social apps show a black frame instead of the video."""
        source = (ROOT / "src" / "neoag" / "figures" / "animation.py").read_text()
        assert "yuv420p" in source
        assert "faststart" in source

    def test_is_short_enough_for_a_feed(self):
        import inspect

        from neoag.figures import animation

        signature = inspect.signature(animation.build)
        assert signature.parameters["duration"].default <= 30
