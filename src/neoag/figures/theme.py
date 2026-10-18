"""Shared visual language and deterministic rendering settings.

Colours are from the Okabe-Ito palette, which stays distinguishable under every
common form of colour vision deficiency. The two trial arms are vermillion and
blue, a pair that remains separable in deuteranopia, protanopia and tritanopia,
and that also differs in lightness so it survives being printed in greyscale.

Determinism matters here: matplotlib stamps a creation date into PNG and PDF
metadata by default, which would make every rebuild produce a different file and
fill the repository's history with noise. Those fields are suppressed.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt

# Okabe-Ito
VERMILLION = "#D55E00"
BLUE = "#0072B2"
GREEN = "#009E73"
AMBER = "#E69F00"
SKY = "#56B4E9"
PURPLE = "#CC79A7"
GREY = "#8C8C8C"

COMBO = VERMILLION
CONTROL = BLUE

INK = "#15181C"
MUTED = "#4A5159"
RULE = "#D7DCE1"
PAPER = "#FFFFFF"

#: Suppresses matplotlib's embedded creation timestamp so rebuilds are identical.
PNG_METADATA = {"Software": None}
PDF_METADATA = {"CreationDate": None, "ModDate": None, "Producer": None, "Creator": None}

RCPARAMS = {
    "figure.dpi": 100,
    "savefig.dpi": 200,
    "savefig.facecolor": PAPER,
    "figure.facecolor": PAPER,
    "axes.facecolor": PAPER,
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
    "font.size": 11,
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "axes.labelsize": 11,
    "axes.labelcolor": MUTED,
    "axes.edgecolor": RULE,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.color": RULE,
    "grid.linewidth": 0.8,
    "grid.alpha": 0.7,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "legend.frameon": False,
    "legend.fontsize": 10,
    "text.color": INK,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "path.simplify": False,
    "axes.unicode_minus": False,
}


def apply() -> None:
    """Install the shared style. Call before building any figure."""
    plt.rcParams.update(RCPARAMS)


def save(fig, path: Path) -> Path:
    """Save a figure deterministically.

    Deliberately not ``bbox_inches="tight"``: that re-crops around whatever
    artists exist and silently discards the margins each figure reserves for its
    own footnotes and legends, which is how labels end up overlapping.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, metadata=PNG_METADATA)
    plt.close(fig)
    return path


DISCLAIMER = "Educational project — not medical advice. Not affiliated with Moderna or Merck."
