"""
Shared plotting style for Stage 6 figures. Deliberately plain: white
background, thin axes, default sans-serif font, no gradients/shadows/3D,
minimal on-chart text (a title and axis labels, nothing decorative).
Colourblind-safe (Okabe-Ito) palette, one fixed colour per system used
consistently across every figure.
"""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

SYSTEM_ORDER = ["ChatGPT", "Claude", "Gemini", "MS Copilot Agent", "Perplexity"]

SYSTEM_COLORS = {
    "ChatGPT": "#0072B2",
    "Claude": "#D55E00",
    "Gemini": "#009E73",
    "MS Copilot Agent": "#CC79A7",
    "Perplexity": "#E69F00",
}

TASK_MARKERS = {"ceo": "o", "phipa": "s", "supervisor": "^"}

plt.rcParams.update(
    {
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",
        "font.family": "sans-serif",
        "font.size": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.edgecolor": "#444444",
        "axes.labelcolor": "#222222",
        "text.color": "#222222",
        "xtick.color": "#333333",
        "ytick.color": "#333333",
        "axes.grid": False,
        "legend.frameon": False,
    }
)


def clean_axes(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(length=3)


def savefig(fig, path_no_ext):
    extra = getattr(fig, "savefig_extra_artists", None)
    fig.savefig(path_no_ext + ".png", dpi=300, bbox_inches="tight", bbox_extra_artists=extra)
    fig.savefig(path_no_ext + ".pdf", bbox_inches="tight", bbox_extra_artists=extra)
    plt.close(fig)
