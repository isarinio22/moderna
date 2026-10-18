"""A short animation of the whole pipeline, for social posts.

Shows the real counts, not a stylised approximation: every mutation and every
candidate fragment from the actual run is a dot on screen. The narrowing is the
story, so nothing is exaggerated to make it look more dramatic.

Portrait 1080x1350 to match the carousel, under twenty seconds, H.264 in a
yuv420p pixel format so it plays everywhere rather than showing a black frame.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FFMpegWriter, FuncAnimation

from neoag.figures import theme
from neoag.figures.carousel import BG, DIM, FG, RULE

W_IN, H_IN, DPI = 10.8, 13.5, 100
FPS = 24
SEED = 20261018


class Stage:
    """One labelled beat of the animation."""

    def __init__(self, start: float, end: float, title: str, subtitle: str):
        self.start, self.end, self.title, self.subtitle = start, end, title, subtitle

    def progress(self, t: float) -> float:
        if t <= self.start:
            return 0.0
        if t >= self.end:
            return 1.0
        return (t - self.start) / (self.end - self.start)


def _ease(x: float) -> float:
    """Smooth start and stop, so motion does not look mechanical."""
    return x * x * (3 - 2 * x)


def build(data_dir: Path, out: Path, duration: float = 17.0) -> Path:
    """Render the animation to MP4."""
    theme.apply()
    manifest = json.loads((data_dir / "manifest.json").read_text())
    counts = manifest["counts"]

    n_mut = counts["mutations_validated"]
    n_frag = counts["candidates"]
    n_sel = counts["selected"]
    rng = np.random.default_rng(SEED)

    # Mutation dots: a loose cluster.
    mut_xy = np.column_stack([
        rng.uniform(0.12, 0.88, n_mut),
        rng.uniform(0.40, 0.72, n_mut),
    ])

    # Every fragment belongs to a mutation and starts where that mutation sits.
    owner = rng.integers(0, n_mut, n_frag)
    angle = rng.uniform(0, 2 * np.pi, n_frag)
    radius = rng.uniform(0.01, 0.075, n_frag)
    frag_xy = mut_xy[owner] + np.column_stack([
        np.cos(angle) * radius, np.sin(angle) * radius * 0.8
    ])
    frag_xy[:, 0] = np.clip(frag_xy[:, 0], 0.06, 0.94)
    frag_xy[:, 1] = np.clip(frag_xy[:, 1], 0.30, 0.80)

    chosen = rng.choice(n_frag, n_sel, replace=False)
    is_chosen = np.zeros(n_frag, dtype=bool)
    is_chosen[chosen] = True

    # Where the chosen fragments end up: a single strand.
    strand_x = np.linspace(0.10, 0.90, n_sel)
    strand_y = np.full(n_sel, 0.50)

    stages = [
        Stage(0.0, 3.4, f"{n_mut} mutations", "changes this tumor made to its own proteins"),
        Stage(3.4, 7.4, f"{n_frag:,} fragments", "every short piece that spans a mutation"),
        Stage(7.4, 11.4, f"{n_sel} targets", "the ones the immune system could actually see"),
        # Finishes before the clip ends, so the final composition holds for two
        # seconds instead of only existing on the last frame.
        Stage(11.4, 15.0, "one message", "written into a single strand of mRNA"),
    ]

    fig = plt.figure(figsize=(W_IN, H_IN), dpi=DPI, facecolor=BG)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    frag_scatter = ax.scatter(frag_xy[:, 0], frag_xy[:, 1], s=6,
                              c=theme.GREY, alpha=0.0, linewidths=0, zorder=2)
    mut_scatter = ax.scatter(mut_xy[:, 0], mut_xy[:, 1], s=70,
                             c=theme.SKY, alpha=0.0, linewidths=0, zorder=3)
    strand_line, = ax.plot([], [], color=theme.GREEN, lw=3, alpha=0.0, zorder=1)

    eyebrow = ax.text(0.08, 0.93, "HOW A PERSONALIZED CANCER VACCINE IS DESIGNED",
                      color=theme.GREEN, fontsize=11, fontweight="bold")
    title = ax.text(0.08, 0.855, "", color=FG, fontsize=50, fontweight="bold", va="top")
    subtitle = ax.text(0.08, 0.79, "", color=DIM, fontsize=21, va="top")
    footer = ax.text(0.08, 0.06, "github.com/isarinio22/moderna", color=DIM, fontsize=15)
    note = ax.text(0.08, 0.11, "Educational project. Not medical advice.",
                   color=theme.AMBER, fontsize=14)
    ax.plot([0.08, 0.92], [0.09, 0.09], color=RULE, lw=1)

    n_frames = int(duration * FPS)

    def frame(i: int):
        t = i / FPS
        current = stages[0]
        for stage in stages:
            if t >= stage.start:
                current = stage
        title.set_text(current.title)
        subtitle.set_text(current.subtitle)

        # Stage 1: mutations fade in.
        p1 = _ease(stages[0].progress(t))
        # Stage 2: fragments burst out of their mutation.
        p2 = _ease(stages[1].progress(t))
        # Stage 3: everything unselected fades away.
        p3 = _ease(stages[2].progress(t))
        # Stage 4: the survivors line up.
        p4 = _ease(stages[3].progress(t))

        mut_scatter.set_alpha(max(0.0, p1 * (1 - p2) * 0.95))
        # Cube the fade so the discarded fragments clear quickly and the
        # survivors are legible well before the stage ends.
        frag_alpha = np.where(is_chosen, p2, p2 * (1 - p3) ** 3 * 0.45)
        frag_scatter.set_alpha(np.clip(frag_alpha, 0, 1))

        colours = np.where(is_chosen & (p3 > 0.15), theme.COMBO, theme.GREY)
        frag_scatter.set_color(colours)
        sizes = np.where(is_chosen, 6 + 74 * p3, 6)
        frag_scatter.set_sizes(sizes)

        positions = frag_xy.copy()
        if p4 > 0:
            target = np.column_stack([strand_x, strand_y])
            positions[chosen] = frag_xy[chosen] * (1 - p4) + target * p4
        frag_scatter.set_offsets(positions)

        if p4 > 0.35:
            a = min(1.0, (p4 - 0.35) / 0.4)
            strand_line.set_data([0.10, 0.90], [0.50, 0.50])
            strand_line.set_alpha(a * 0.9)
            strand_line.set_linewidth(3 + 3 * a)
        else:
            strand_line.set_alpha(0.0)

        return frag_scatter, mut_scatter, strand_line, title, subtitle

    anim = FuncAnimation(fig, frame, frames=n_frames, interval=1000 / FPS, blit=False)

    out.parent.mkdir(parents=True, exist_ok=True)
    writer = FFMpegWriter(
        fps=FPS, codec="libx264", bitrate=3200,
        # yuv420p is required for playback in Safari and most social apps;
        # without it the video shows as a black frame.
        extra_args=["-pix_fmt", "yuv420p", "-profile:v", "high", "-movflags", "+faststart"],
    )
    # Pin the dpi: the shared style sets savefig.dpi to 200 for print-quality
    # stills, which would render every frame at twice the intended size.
    anim.save(out, writer=writer, dpi=DPI, savefig_kwargs={"facecolor": BG})
    plt.close(fig)
    _ = (eyebrow, footer, note)
    return out
