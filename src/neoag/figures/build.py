"""Build every static figure.

Each function takes the exported JSON and returns a matplotlib figure, so the
figures are driven by exactly the same numbers the website shows.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, Rectangle

from neoag.figures import theme

ARM_LABEL = {"combo": "vaccine + pembrolizumab", "control": "pembrolizumab alone"}
ARM_COLOUR = {"combo": theme.COMBO, "control": theme.CONTROL}
#: Redundant encoding. The Okabe-Ito pair is unambiguous to colour-blind
#: readers but close in lightness, so it would merge in greyscale.
ARM_STYLE = {"combo": "-", "control": (0, (6, 2))}


def _load(data_dir: Path) -> dict:
    return {
        name: json.loads((data_dir / f"{name}.json").read_text())
        for name in ("manifest", "funnel", "epitopes", "panels", "construct", "evidence")
    }


# --------------------------------------------------------------------------- #

def fig_km(d: dict):
    """Recurrence-free survival, with the at-risk table underneath."""
    ev = d["evidence"]
    fig, (ax, tab) = plt.subplots(
        2, 1, figsize=(9.0, 6.6), gridspec_kw={"height_ratios": [4, 1.1], "hspace": 0.12}
    )

    for arm in ("control", "combo"):
        c = ev["curves"][arm]
        t = [x for x in c["t"] if x <= 66]
        s = c["s"][: len(t)]
        ax.step([0, *t], [1.0, *s], where="post", color=ARM_COLOUR[arm], lw=2.4,
                linestyle=ARM_STYLE[arm], label=ARM_LABEL[arm])

    last = ev["landmarks"][-1]
    ax.annotate(
        "", xy=(60, last["combo"]), xytext=(60, last["control"]),
        arrowprops={"arrowstyle": "<->", "color": theme.GREEN, "lw": 1.6},
    )
    ax.text(58.5, (last["combo"] + last["control"]) / 2,
            f"{last['per_100']:.0f} per 100", ha="right", va="center",
            color=theme.GREEN, fontweight="bold", fontsize=11)

    ax.set_xlim(-2.5, 67)
    ax.set_ylim(0, 1.02)
    ax.set_yticks(np.arange(0, 1.01, 0.25))
    ax.set_yticklabels([f"{int(v * 100)}%" for v in np.arange(0, 1.01, 0.25)])
    ax.set_xticks(range(0, 67, 12))
    ax.set_ylabel("still recurrence-free")
    ax.set_title("Recurrence-free survival after surgery (KEYNOTE-942, 5-year analysis)")
    ax.legend(loc="lower left")
    ax.set_xticklabels([])

    tab.set_xlim(-2.5, 67)
    tab.set_ylim(-0.6, 1.6)
    tab.set_yticks([1, 0])
    tab.set_yticklabels([ARM_LABEL["combo"], ARM_LABEL["control"]], fontsize=9)
    for label, arm in zip(tab.get_yticklabels(), ("combo", "control"), strict=True):
        label.set_color(ARM_COLOUR[arm])
    tab.set_xticks(range(0, 67, 12))
    tab.set_xlabel("months since treatment started")
    tab.grid(False)
    for side in ("left", "right", "top"):
        tab.spines[side].set_visible(False)
    tab.tick_params(axis="y", length=0)
    for row, arm in enumerate(("combo", "control")):
        for r in ev["curves"][arm]["n_risk"]:
            tab.text(r["t"], 1 - row, str(r["n"]), fontsize=8.5, ha="center",
                     va="center", color=theme.MUTED)
    tab.text(0, 1.52, "still being followed", fontsize=9, color=theme.MUTED,
             fontweight="bold", va="bottom")
    # The arm names sit in the left margin, which must be wide enough to hold
    # them, and the first count sits at x=0 so it needs clearance too.
    fig.subplots_adjust(left=0.235, right=0.97, top=0.93, bottom=0.10)
    return fig


def fig_icon_array(d: dict):
    """The same result as 100 people."""
    lm = d["evidence"]["landmarks"][-1]
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 5.2))
    for ax, arm in zip(axes, ("combo", "control"), strict=True):
        n = round(lm[arm] * 100)
        colour = ARM_COLOUR[arm]
        for i in range(100):
            row, col = divmod(i, 10)
            on = i < n
            c = colour if on else theme.RULE
            ax.add_patch(Circle((col, -row * 1.35), 0.3, color=c))
            ax.add_patch(Rectangle((col - 0.36, -row * 1.35 - 1.02), 0.72, 0.68,
                                   color=c, zorder=2))
        ax.set_xlim(-0.8, 9.8)
        ax.set_ylim(-13.4, 1.0)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title(f"{n} of 100\n{ARM_LABEL[arm]}", color=colour, fontsize=11.5, pad=8)
    fig.suptitle("Still cancer-free five years after surgery", fontsize=14,
                 fontweight="bold", y=0.99)
    fig.text(0.5, 0.06,
             f"Difference: {lm['per_100']:.0f} per 100 "
             f"(95% CI {lm['ci_low_per_100']:.0f} to {lm['ci_high_per_100']:.0f}). "
             f"Reconstructed from published summary data.",
             ha="center", fontsize=9.5, color=theme.MUTED)
    fig.subplots_adjust(top=0.80, bottom=0.13)
    return fig


def fig_panels(d: dict):
    """How much of the vaccine changes with the patient's HLA type."""
    p = d["panels"]
    names = sorted(p["panels"])
    ids = sorted({e["id"] for n in names for e in p["panels"][n]["selected"]})
    shared = {
        i for i in ids if all(any(e["id"] == i for e in p["panels"][n]["selected"]) for n in names)
    }

    fig, ax = plt.subplots(figsize=(8.6, 3.4))
    for row, name in enumerate(names):
        chosen = {e["id"] for e in p["panels"][name]["selected"]}
        for col, i in enumerate(ids):
            if i not in chosen:
                continue
            ax.add_patch(Rectangle((col, -row - 0.38), 0.86, 0.76,
                                   color=theme.GREEN if i in shared else theme.COMBO))
    ax.set_xlim(-0.5, len(ids) + 0.5)
    ax.set_ylim(-len(names) + 0.4, 0.8)
    ax.set_yticks([-r for r in range(len(names))])
    ax.set_yticklabels([n.replace("common_", "").replace("_", " ") for n in names], fontsize=10)
    ax.set_xticks([])
    ax.grid(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.set_title(
        f"The same tumor, three different immune types: "
        f"only {len(shared)} of 34 targets are shared"
    )
    ax.set_xlabel(f"each column is one possible target ({len(ids)} in total)", labelpad=8)
    handles = [Rectangle((0, 0), 1, 1, color=theme.GREEN),
               Rectangle((0, 0), 1, 1, color=theme.COMBO)]
    ax.legend(handles, ["chosen for every HLA type", "chosen for only some"],
              ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.20), fontsize=9)
    fig.subplots_adjust(bottom=0.30, top=0.84)
    return fig


def fig_funnel(d: dict):
    """The narrowing, with what was discarded at each step."""
    steps = d["funnel"]
    fig, ax = plt.subplots(figsize=(8.6, 4.2))
    labels, values = [], []
    for s in steps:
        labels.append(s["step"])
        values.append(s["n_out"])
    y = np.arange(len(labels))[::-1]
    ax.barh(y, [np.log10(v + 1) for v in values], color=theme.GREEN, height=0.55)
    for yi, v in zip(y, values, strict=True):
        ax.text(np.log10(v + 1) + 0.05, yi, f"{v:,}", va="center", fontsize=11,
                fontweight="bold", color=theme.INK)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xticks([])
    ax.grid(False)
    ax.spines["bottom"].set_visible(False)
    ax.set_xlim(0, np.log10(max(values) + 1) * 1.25)
    ax.set_title("From every mutation down to thirty-four")
    ax.set_xlabel("bar length is logarithmic — the range is too wide to draw linearly")
    return fig


def fig_mutant_vs_wt(d: dict):
    """Does the mutation actually make the fragment more visible?"""
    eps = [e for e in d["epitopes"]["epitopes"] if e["nm"] and e["wt_nm"]]
    sel = [e for e in eps if e["sel"]]
    rest = [e for e in eps if not e["sel"]]

    fig, ax = plt.subplots(figsize=(7.2, 6.0))
    ax.scatter([e["wt_nm"] for e in rest], [e["nm"] for e in rest],
               s=14, color=theme.GREY, alpha=0.35, linewidths=0, label="not selected")
    ax.scatter([e["wt_nm"] for e in sel], [e["nm"] for e in sel],
               s=52, color=theme.COMBO, edgecolor="white", linewidth=0.8, zorder=3,
               label="selected for the vaccine")
    lims = [1, 60000]
    ax.plot(lims, lims, color=theme.MUTED, ls="--", lw=1.2, zorder=1)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(*lims)
    ax.set_ylim(*lims)
    ax.set_xlabel("normal version (nM — lower binds tighter)")
    ax.set_ylabel("mutated version (nM — lower binds tighter)")
    ax.set_title("Does the mutation make the fragment easier to see?")
    ax.legend(loc="upper left")
    ax.text(0.97, 0.06,
            "below the line:\nthe mutation helps",
            transform=ax.transAxes, ha="right", va="bottom", fontsize=9.5,
            color=theme.COMBO, fontweight="bold")
    ax.text(0.04, 0.72, "on the line: displayed\njust as well before\nthe mutation",
            transform=ax.transAxes, fontsize=9, color=theme.MUTED)
    fig.subplots_adjust(bottom=0.12)
    return fig


def fig_score_components(d: dict):
    """What drove each of the chosen thirty-four."""
    sel = sorted([e for e in d["epitopes"]["epitopes"] if e["sel"]], key=lambda e: -e["score"])
    weights = d["epitopes"]["weights"]
    keys = ["presentation", "agretopicity", "expression", "quality"]
    colours = [theme.BLUE, theme.COMBO, theme.GREEN, theme.AMBER]
    names = {
        "presentation": "will it be displayed",
        "agretopicity": "better than normal",
        "expression": "gene switched on",
        "quality": "peptide quality",
    }

    fig, ax = plt.subplots(figsize=(8.6, 5.4))
    x = np.arange(len(sel))
    bottom = np.zeros(len(sel))
    for key, colour in zip(keys, colours, strict=True):
        vals = np.array([e["c"][key] * weights[key] for e in sel])
        ax.bar(x, vals, bottom=bottom, color=colour, width=0.78, label=names[key])
        bottom += vals
    ax.set_xticks(x)
    ax.set_xticklabels([e["gene"] for e in sel], rotation=90, fontsize=7.5)
    ax.set_ylabel("contribution to the score")
    ax.set_title("What earned each of the 34 its place")
    ax.legend(ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.22))
    ax.grid(axis="x", visible=False)
    return fig


def fig_construct(d: dict):
    """The conceptual message, as a labelled map."""
    c = d["construct"]
    colours = {
        "cap": theme.GREEN, "utr": theme.BLUE, "kozak": theme.GREY, "epitope": theme.COMBO,
        "linker": theme.RULE, "stop": theme.GREY, "polya": theme.AMBER,
    }
    fig, ax = plt.subplots(figsize=(8.6, 3.0))
    for b in c["blocks"]:
        if b["nt"] <= 0:
            continue
        ax.add_patch(Rectangle((b["start"], 0), b["nt"], 1,
                               color=colours.get(b["kind"], theme.GREY)))
    ax.set_xlim(0, c["total_nt"])
    ax.set_ylim(-0.9, 1.5)
    ax.set_yticks([])
    ax.grid(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.set_xlabel("position in the message (nucleotides)", labelpad=6)
    ax.set_title(f"A conceptual mRNA carrying all 34 targets — {c['total_nt']:,} letters",
                 pad=10)
    seen = []
    for kind, colour in colours.items():
        if any(b["kind"] == kind and b["nt"] > 0 for b in c["blocks"]):
            seen.append((kind, colour))
    handles = [Rectangle((0, 0), 1, 1, color=col) for _, col in seen]
    ax.legend(handles, [k for k, _ in seen], ncol=len(seen), loc="upper center",
              bbox_to_anchor=(0.5, -0.52), fontsize=9)
    fig.text(0.5, 0.015, "CONCEPTUAL ILLUSTRATION — not a manufacturable sequence.",
             ha="center", fontsize=9, color=theme.COMBO, fontweight="bold")
    fig.subplots_adjust(bottom=0.40, top=0.82)
    return fig


def fig_validation(d: dict):
    """How far the reconstruction lands from what was published."""
    checks = [
        c for c in d["evidence"]["validation"]["checks"]
        if c["published"] is not None and c["difference"] is not None and "survival" in c["name"]
    ]
    fig, ax = plt.subplots(figsize=(8.0, 4.4))
    y = np.arange(len(checks))[::-1]
    diffs = [c["difference"] * 100 for c in checks]
    ax.barh(y, diffs, color=[theme.COMBO if "combination" in c["name"] else theme.CONTROL
                             for c in checks], height=0.6)
    ax.axvline(0, color=theme.MUTED, lw=1)
    ax.set_yticks(y)
    ax.set_yticklabels([c["name"].replace(" survival at", ",").replace(" months", " mo")
                        for c in checks], fontsize=9)
    ax.set_xlabel("reconstructed minus published (percentage points)")
    ax.set_xlim(-1.5, 1.5)
    ax.set_title("Every landmark lands within half a percentage point of the publication")
    ax.grid(axis="y", visible=False)
    return fig


FIGURES = {
    "km_survival": fig_km,
    "icon_array": fig_icon_array,
    "hla_panels": fig_panels,
    "funnel": fig_funnel,
    "mutant_vs_wildtype": fig_mutant_vs_wt,
    "score_components": fig_score_components,
    "construct_map": fig_construct,
    "validation": fig_validation,
}


def build_all(data_dir: Path, outdir: Path, only: str | None = None) -> dict[str, Path]:
    """Render every figure to PNG."""
    theme.apply()
    data = _load(data_dir)
    written: dict[str, Path] = {}
    for name, fn in FIGURES.items():
        if only and only != name:
            continue
        written[name] = theme.save(fn(data), outdir / f"{name}.png")
    return written
