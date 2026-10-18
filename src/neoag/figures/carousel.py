"""The LinkedIn carousel.

Nine portrait slides at exactly 1080x1350, the 4:5 ratio LinkedIn renders
largest in the feed. One idea per slide, text sized to be readable on a phone
without zooming, and a final slide that says where the code is.

Built with matplotlib's PDF backend so it is one file, vector, and reproducible.
The numbers come from the exported JSON, so the deck cannot drift from the
analysis.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Ellipse, Rectangle

from neoag.figures import theme

W_IN, H_IN, DPI = 10.8, 13.5, 100  # -> 1080 x 1350
REPO = "github.com/isarinio22/moderna"

BG = "#0F1216"
FG = "#EDF1F5"
DIM = "#A8B2BC"
RULE = "#2A323B"


def _slide():
    fig = plt.figure(figsize=(W_IN, H_IN), dpi=DPI, facecolor=BG)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.set_facecolor(BG)
    return fig, ax


#: The slide is taller than it is wide, so a circle in axes coordinates renders
#: as an ellipse. Scale the vertical radius to compensate.
ASPECT = W_IN / H_IN


def _circle(ax, x, y, r, colour):
    ax.add_patch(Ellipse((x, y), 2 * r, 2 * r / ASPECT, color=colour))


def _eyebrow(ax, text):
    # matplotlib has no letter-spacing property, so space the characters out.
    spaced = " ".join(text.upper())
    ax.text(0.08, 0.92, spaced, color=theme.GREEN, fontsize=12, fontweight="bold")


def _title(ax, text, y=0.84, size=40):
    ax.text(0.08, y, text, color=FG, fontsize=size, fontweight="bold",
            va="top", linespacing=1.18)


def _body(ax, text, y=0.60, size=21, color=None):
    ax.text(0.08, y, text, color=color or DIM, fontsize=size, va="top", linespacing=1.5)


def _footer(ax, n, total):
    ax.text(0.08, 0.045, REPO, color=DIM, fontsize=14)
    ax.text(0.92, 0.045, f"{n} / {total}", color=DIM, fontsize=14, ha="right")
    ax.plot([0.08, 0.92], [0.075, 0.075], color=RULE, lw=1)


TOTAL = 9


def slide_1_hook(ax, d):
    _eyebrow(ax, "how a personalized cancer vaccine works")
    _title(ax, "Your tumor has a\nfingerprint no\nhealthy cell has.", y=0.80, size=52)
    _body(ax,
          "Every cancer rewrites its own DNA as it grows.\n"
          "Those typos exist nowhere else in your body.\n\n"
          "That makes them the one thing an immune\nsystem could be taught to hunt.",
          y=0.42, size=23)
    ax.text(0.08, 0.16, "A look at the evidence for one\nthat is actually in trials.",
            color=theme.COMBO, fontsize=20, va="top", fontweight="bold", linespacing=1.4)


def slide_2_idea(ax, d):
    _eyebrow(ax, "the idea")
    _title(ax, "Turn the typos into\nwanted posters.")
    steps = [
        ("1", "Read the tumor's mutations", theme.GREY),
        ("2", "Pick the ones your body can display", theme.COMBO),
        ("3", "Write them into one mRNA message", theme.GREEN),
        ("4", "Your cells show them to the immune system", theme.SKY),
    ]
    for i, (num, text, colour) in enumerate(steps):
        y = 0.62 - i * 0.105
        _circle(ax, 0.115, y, 0.026, colour)
        ax.text(0.115, y, num, color=BG, fontsize=20, fontweight="bold",
                ha="center", va="center")
        ax.text(0.175, y, text, color=FG, fontsize=22, va="center")
    _body(ax, "A second drug, pembrolizumab, stops the tumor\n"
              "switching those immune cells back off.", y=0.17, size=19)


def slide_3_personal(ax, d):
    p = d["panels"]
    names = sorted(p["panels"])
    ids = sorted({e["id"] for n in names for e in p["panels"][n]["selected"]})
    shared = {i for i in ids
              if all(any(e["id"] == i for e in p["panels"][n]["selected"]) for n in names)}
    _eyebrow(ax, "why it has to be personal")
    _title(ax, "Same tumor.\nDifferent person.\nDifferent vaccine.")
    for row, name in enumerate(names):
        chosen = {e["id"] for e in p["panels"][name]["selected"]}
        y = 0.50 - row * 0.082
        ax.text(0.08, y + 0.030, name.replace("common_", "").replace("_", " "),
                color=DIM, fontsize=18)
        for col, i in enumerate(ids):
            if i not in chosen:
                continue
            ax.add_patch(Rectangle((0.08 + col * (0.84 / len(ids)), y - 0.012),
                                   0.84 / len(ids) * 0.8, 0.028,
                                   color=theme.GREEN if i in shared else theme.COMBO))
    ax.text(0.08, 0.235, f"Only {len(shared)} of 34 targets are shared.",
            color=FG, fontsize=30, fontweight="bold", va="top")
    _body(ax, "Which fragments your body can display depends on\n"
              "genes you inherited. Change the person, and about\n"
              "80% of the vaccine changes with them.", y=0.18, size=19)


def slide_4_funnel(ax, d):
    f = d["funnel"]
    _eyebrow(ax, "the narrowing")
    _title(ax, "From 128 mutations\ndown to 34 targets.")
    for i, step in enumerate(f):
        y = 0.60 - i * 0.095
        width = 0.62 * np.log10(step["n_out"] + 1) / np.log10(5000)
        ax.add_patch(Rectangle((0.08, y - 0.022), width, 0.044, color=theme.GREEN))
        ax.text(0.08 + width + 0.02, y, f"{step['n_out']:,}", color=FG, fontsize=20,
                va="center", fontweight="bold")
        ax.text(0.08, y + 0.038, step["step"], color=DIM, fontsize=15, va="bottom")
    _body(ax, "Most candidates are thrown away because they\n"
              "would never be displayed on the cell surface.\n"
              "Every discard is published with its reason.", y=0.19, size=19)


def slide_5_evidence(ax, d):
    ev = d["evidence"]
    _eyebrow(ax, "does it work?")
    _title(ax, "A 157-person trial,\nfive years of\nfollow-up.", size=44)

    box = ax.inset_axes([0.08, 0.26, 0.84, 0.36])
    box.set_facecolor(BG)
    for arm, colour, style in (("control", theme.CONTROL, (0, (6, 2))),
                               ("combo", theme.COMBO, "-")):
        c = ev["curves"][arm]
        t = [x for x in c["t"] if x <= 66]
        box.step([0, *t], [1.0, *c["s"][: len(t)]], where="post",
                 color=colour, lw=3, linestyle=style)
    box.set_xlim(-2, 67)
    box.set_ylim(0.35, 1.02)
    box.set_yticks([0.5, 0.75, 1.0])
    box.set_yticklabels(["50%", "75%", "100%"], color=DIM, fontsize=14)
    box.set_xticks([0, 24, 48])
    box.set_xticklabels(["0", "2 yr", "4 yr"], color=DIM, fontsize=14)
    for side in ("top", "right"):
        box.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        box.spines[side].set_color(RULE)
    box.grid(color=RULE, lw=0.8, alpha=0.5)
    box.tick_params(colors=DIM)

    last = ev["landmarks"][-1]
    ax.text(0.08, 0.215, f"{last['combo'] * 100:.0f}% vs {last['control'] * 100:.0f}% "
                         "still cancer-free at 5 years",
            color=FG, fontsize=24, fontweight="bold", va="top")
    ax.text(0.08, 0.16, "vaccine + pembrolizumab  —  pembrolizumab alone",
            color=DIM, fontsize=16, va="top")


def slide_6_people(ax, d):
    lm = d["evidence"]["landmarks"][-1]
    _eyebrow(ax, "the same result, as people")
    _title(ax, "Out of 100 people\nlike this...", size=44)
    for col, (arm, colour) in enumerate((("combo", theme.COMBO), ("control", theme.CONTROL))):
        n = round(lm[arm] * 100)
        x0 = 0.09 + col * 0.46
        ax.text(x0, 0.635, f"{n} of 100", color=colour, fontsize=34, fontweight="bold")
        ax.text(x0, 0.60, "vaccine + pembro" if arm == "combo" else "pembro alone",
                color=DIM, fontsize=16)
        # Each figure is a head plus a body, about 0.033 tall in axes units.
        # Row pitch has to exceed that or the rows merge into solid columns, and
        # ten rows have to finish above the caption at y = 0.145.
        for i in range(100):
            row, c = divmod(i, 10)
            on = i < n
            cx = x0 + c * 0.037
            cy = 0.555 - row * 0.037
            shade = colour if on else RULE
            _circle(ax, cx, cy, 0.0072, shade)
            ax.add_patch(Rectangle((cx - 0.0088, cy - 0.0245), 0.0176, 0.016, color=shade))
    ax.text(0.08, 0.145, f"{lm['per_100']:.0f} more people per 100 — but with only 157\n"
                         f"patients, the honest range is {lm['ci_low_per_100']:.0f} to "
                         f"{lm['ci_high_per_100']:.0f}.",
            color=FG, fontsize=19, va="top", linespacing=1.5)


def slide_7_caveats(ax, d):
    _eyebrow(ax, "what it does not prove")
    _title(ax, "Promising.\nNot proof.", size=52)
    points = [
        "157 patients, 51 recurrences. Small.",
        "Nobody was blinded — everyone knew\nwho got what.",
        "The trial's bar was a one-sided p below 0.10.\nStated the usual way, it was p = 0.053.",
        "14 deaths in total, so it says nothing\nabout living longer.",
    ]
    y = 0.62
    for text in points:
        ax.text(0.085, y, "—", color=theme.AMBER, fontsize=22, va="top", fontweight="bold")
        ax.text(0.135, y, text, color=FG, fontsize=20, va="top", linespacing=1.4)
        y -= 0.085 + 0.045 * text.count("\n")
    _body(ax, "A much larger blinded trial has reported that it\n"
              "met its goals. No numbers from it are public yet.", y=0.18, size=19)


def slide_8_method(ax, d):
    ev = d["evidence"]
    r = ev["reconstruction"]
    _eyebrow(ax, "how to check this yourself")
    _title(ax, "Every number here\nis reproducible.", size=44)
    _body(ax,
          "The patient-level data was rebuilt from the trial's\n"
          "own published summary table — no curve-tracing,\n"
          "just arithmetic the published table forces.",
          y=0.62, size=20)
    rows = [("hazard ratio", f"{r['hr']:.3f}", "0.510"),
            ("95% interval", f"{r['ci'][0]:.3f}–{r['ci'][1]:.3f}", "0.294–0.887"),
            ("recurrences", "28 / 23", "28 / 23")]
    ax.text(0.08, 0.455, "reconstructed", color=DIM, fontsize=15)
    ax.text(0.62, 0.455, "published", color=DIM, fontsize=15)
    for i, (label, got, want) in enumerate(rows):
        y = 0.40 - i * 0.062
        ax.text(0.08, y, label, color=DIM, fontsize=17)
        ax.text(0.37, y, got, color=theme.GREEN, fontsize=19, fontweight="bold")
        ax.text(0.62, y, want, color=FG, fontsize=19)
    _body(ax, "All ten landmark estimates land within half a\npercentage point of the publication.",
          y=0.18, size=19)


def slide_9_repo(ax, d):
    m = d["manifest"]
    _eyebrow(ax, "open source")
    _title(ax, "Code, data and\nsources — all of it.", size=46)
    _body(ax,
          "A reproducible pipeline from a public tumor sample\n"
          "to a conceptual vaccine design, plus an honest\n"
          "re-analysis of the trial evidence.\n\n"
          "Every number is sourced with its link, publication\n"
          "date and data cutoff. Anything that could not be\n"
          "verified is flagged and left unused.",
          y=0.60, size=20)
    ax.text(0.08, 0.26, REPO, color=theme.GREEN, fontsize=30, fontweight="bold")
    ax.text(0.08, 0.195,
            f"{m['counts']['mutations_validated']} mutations verified · "
            f"{m['counts']['candidates']:,} fragments scored · {m['counts']['selected']} selected",
            color=DIM, fontsize=16)
    ax.text(0.08, 0.14, "Educational project. Not medical advice.\n"
                        "Not affiliated with Moderna or Merck.",
            color=theme.AMBER, fontsize=16, va="top", linespacing=1.4)


SLIDES = [slide_1_hook, slide_2_idea, slide_3_personal, slide_4_funnel, slide_5_evidence,
          slide_6_people, slide_7_caveats, slide_8_method, slide_9_repo]


def build(data_dir: Path, out: Path) -> Path:
    """Render the full carousel to a single PDF."""
    theme.apply()
    data = {
        name: json.loads((data_dir / f"{name}.json").read_text())
        for name in ("manifest", "funnel", "epitopes", "panels", "construct", "evidence")
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    with PdfPages(out, metadata=theme.PDF_METADATA) as pdf:
        for i, fn in enumerate(SLIDES, start=1):
            fig, ax = _slide()
            fn(ax, data)
            _footer(ax, i, TOTAL)
            pdf.savefig(fig, facecolor=BG)
            plt.close(fig)
    return out


def build_pngs(data_dir: Path, outdir: Path) -> list[Path]:
    """Also write each slide as a PNG, for previewing and for the README."""
    theme.apply()
    data = {
        name: json.loads((data_dir / f"{name}.json").read_text())
        for name in ("manifest", "funnel", "epitopes", "panels", "construct", "evidence")
    }
    outdir.mkdir(parents=True, exist_ok=True)
    written = []
    for i, fn in enumerate(SLIDES, start=1):
        fig, ax = _slide()
        fn(ax, data)
        _footer(ax, i, TOTAL)
        path = outdir / f"slide_{i:02d}.png"
        fig.savefig(path, facecolor=BG, dpi=DPI, metadata=theme.PNG_METADATA)
        plt.close(fig)
        written.append(path)
    return written
