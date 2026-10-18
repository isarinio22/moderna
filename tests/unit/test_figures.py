"""Static figure rendering.

Asserts structure and determinism rather than pixels. Exact pixel comparison
depends on the freetype and matplotlib build, so it fails for the wrong reasons
on a different machine; building the same figure twice and comparing is
platform-independent and still catches real nondeterminism.
"""

from __future__ import annotations

import json

import pytest

from neoag.figures import theme
from neoag.figures.build import FIGURES, build_all
from neoag.paths import Paths

DATA_DIR = Paths().root / "site" / "data"
pytestmark = pytest.mark.skipif(
    not (DATA_DIR / "manifest.json").exists(),
    reason="site/data not built; run `make export` first",
)


def test_agg_backend_is_forced():
    """A GUI backend in CI hangs rather than failing, so it is pinned at import."""
    import matplotlib

    assert matplotlib.get_backend().lower() == "agg"


def test_timestamps_are_suppressed():
    """Matplotlib embeds a creation date by default, which would churn git."""
    assert theme.PNG_METADATA["Software"] is None
    assert theme.PDF_METADATA["CreationDate"] is None


def test_arms_are_encoded_twice_not_just_by_colour():
    """Colour alone is not an accessible encoding.

    The Okabe-Ito pair is unambiguous to colour-blind readers, but vermillion and
    blue sit close in lightness (a contrast ratio of roughly 1.2), so they would
    merge in greyscale or on a monochrome printout. The arms therefore also
    differ in line style.
    """
    from neoag.figures.build import ARM_COLOUR, ARM_STYLE

    assert ARM_COLOUR["combo"] != ARM_COLOUR["control"]
    assert ARM_STYLE["combo"] != ARM_STYLE["control"]


def test_the_arm_colours_really_are_close_in_lightness():
    """Pins the reason the redundant encoding above exists."""
    def luminance(hex_colour: str) -> float:
        r, g, b = (int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5))
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    ratio = (luminance(theme.COMBO) + 0.05) / (luminance(theme.CONTROL) + 0.05)
    assert ratio < 3.0, "if this now exceeds 3:1, the line-style fallback is no longer needed"


def test_every_figure_builds(tmp_path):
    written = build_all(DATA_DIR, tmp_path)
    assert set(written) == set(FIGURES)
    for name, path in written.items():
        assert path.exists(), name
        assert path.stat().st_size > 5_000, f"{name} looks empty"


def test_rendering_is_deterministic(tmp_path):
    """Two builds of the same data must be byte-identical."""
    first = build_all(DATA_DIR, tmp_path / "a", only="funnel")["funnel"]
    second = build_all(DATA_DIR, tmp_path / "b", only="funnel")["funnel"]
    assert first.read_bytes() == second.read_bytes()


def test_figures_are_driven_by_the_exported_data(tmp_path):
    """A figure must reflect the pipeline output, not hard-coded numbers."""
    manifest = json.loads((DATA_DIR / "manifest.json").read_text())
    construct = json.loads((DATA_DIR / "construct.json").read_text())
    assert construct["total_nt"] == manifest["counts"]["construct_nt"]
