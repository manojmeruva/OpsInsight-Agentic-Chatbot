"""
plot_theme.py
=============
Chart theme for server-rendered (matplotlib) plots, matching the web UI
(frontend/src/styles.css, light tokens — charts are shown on a white card in
both UI themes).

`apply_plot_theme()` is called before every generated plotting snippet runs, so
charts are on-brand even when the generated code sets no styling. `THEME` is
exposed to the generated code for semantic colors (e.g. credits vs debits).

Palette validated with the dataviz palette checker against #ffffff:
categorical order passes lightness, chroma, CVD (worst adjacent ΔE 9.1) and
normal-vision (ΔE 19.6) gates; slots 3–5 are below 3:1 contrast, so value
labels on marks are required (the prompt already mandates them).
"""

import matplotlib as mpl
from cycler import cycler
from matplotlib import font_manager
from matplotlib.colors import LinearSegmentedColormap

THEME = {
    # UI tokens
    "accent":         "#1d4ed8",   # --accent; single-series charts
    "text":           "#0f172a",   # --text; titles
    "text_secondary": "#475569",   # --text-2; axis labels, value labels
    "muted":          "#64748b",   # --muted; tick labels
    "grid":           "#e2e8f0",   # --border; gridlines, axis lines
    "surface":        "#ffffff",   # chart card background
    # Money direction (UI accent blue / UI negative red)
    "inflow":         "#1d4ed8",   # credits
    "outflow":        "#b91c1c",   # debits, negative values
    # Categorical series — fixed order, never cycled past 8 (fold extras into "Other")
    "series": [
        "#1d4ed8",  # blue (UI accent)
        "#eb6834",  # orange
        "#1baf7a",  # aqua
        "#eda100",  # yellow
        "#e87ba4",  # magenta
        "#008300",  # green
        "#4a3aa7",  # violet
        "#e34948",  # red
    ],
    # Sequential (magnitude) — single blue hue, light → dark
    "sequential": ["#dbeafe", "#bfdbfe", "#93c5fd", "#60a5fa", "#3b82f6", "#2563eb", "#1d4ed8", "#1e40af", "#1e3a8a"],
    "cmap": "opsinsight",
}

_CMAP = LinearSegmentedColormap.from_list(THEME["cmap"], THEME["sequential"])
if THEME["cmap"] not in mpl.colormaps:
    mpl.colormaps.register(_CMAP)

_UI_FONTS = ["Inter", "Segoe UI", "Helvetica Neue", "Arial", "DejaVu Sans"]
_available = {f.name for f in font_manager.fontManager.ttflist}
_FONT_STACK = [f for f in _UI_FONTS if f in _available] or ["DejaVu Sans"]

RC_PARAMS = {
    # Canvas
    "figure.facecolor": THEME["surface"],
    "axes.facecolor": THEME["surface"],
    "savefig.facecolor": THEME["surface"],
    "figure.figsize": (10, 5.5),
    "figure.dpi": 110,
    "savefig.dpi": 150,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.25,
    # Type
    "font.family": "sans-serif",
    "font.sans-serif": _FONT_STACK,
    "font.size": 10,
    "text.color": THEME["text"],
    "axes.titlesize": 13,
    "axes.titleweight": "semibold",
    "axes.titlecolor": THEME["text"],
    "axes.titlelocation": "left",
    "axes.titlepad": 14,
    "axes.labelsize": 10,
    "axes.labelcolor": THEME["text_secondary"],
    "axes.labelpad": 8,
    "xtick.color": THEME["muted"],
    "ytick.color": THEME["muted"],
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    # Recessive axes & grid
    "axes.edgecolor": THEME["grid"],
    "axes.linewidth": 1,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.spines.left": False,
    "axes.grid": True,
    "axes.grid.axis": "y",
    "axes.axisbelow": True,
    # Headroom inside the axes so value labels at bar ends don't collide with
    # tick labels or the title
    "axes.xmargin": 0.12,
    "axes.ymargin": 0.1,
    "grid.color": THEME["grid"],
    "grid.linewidth": 0.8,
    "xtick.major.size": 0,
    "ytick.major.size": 0,
    # Marks
    "axes.prop_cycle": cycler(color=THEME["series"]),
    "lines.linewidth": 2,
    "lines.markersize": 6,
    "patch.edgecolor": THEME["surface"],   # 1px surface gap between adjacent fills
    "patch.linewidth": 1,
    "image.cmap": THEME["cmap"],
    # Legend
    "legend.frameon": False,
    "legend.fontsize": 9,
    "legend.labelcolor": THEME["text_secondary"],
    # Large numbers: no "1e7" offset text on axes
    "axes.formatter.useoffset": False,
    "axes.formatter.limits": (-5, 12),
}


def inr_compact(value) -> str:
    """Compact Indian-notation rupees for chart labels: ₹1.48 Cr, ₹9.57 L, ₹12.4 K."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return ""
    sign, v = ("-" if v < 0 else ""), abs(v)
    for unit, size in (("Cr", 1e7), ("L", 1e5), ("K", 1e3)):
        if v >= size:
            return f"{sign}₹{v / size:.2f} {unit}".replace(".00 ", " ")
    return f"{sign}₹{v:,.0f}"


def inr_axis():
    """Matplotlib tick formatter using inr_compact: ax.yaxis.set_major_formatter(inr_axis())."""
    from matplotlib.ticker import FuncFormatter
    return FuncFormatter(lambda v, _pos: "₹0" if v == 0 else inr_compact(v))


def apply_plot_theme() -> None:
    """Reset matplotlib to defaults, then apply the UI theme."""
    import matplotlib.pyplot as plt

    plt.close("all")
    mpl.rcdefaults()
    mpl.rcParams.update(RC_PARAMS)
