import matplotlib

matplotlib.use("Agg")

import matplotlib as mpl
import pytest

from core.plot_theme import THEME, apply_plot_theme, inr_axis, inr_compact


@pytest.mark.parametrize("value, expected", [
    (14826069.73, "₹1.48 Cr"),
    (10000000, "₹1 Cr"),
    (956900.5, "₹9.57 L"),
    (14582.47, "₹14.58 K"),
    (950, "₹950"),
    (-251396476.09, "-₹25.14 Cr"),
    (None, ""),
    ("n/a", ""),
])
def test_inr_compact(value, expected):
    assert inr_compact(value) == expected


def test_inr_axis_formats_zero():
    fmt = inr_axis()
    assert fmt(0, 0) == "₹0"
    assert fmt(2e7, 1) == "₹2 Cr"


def test_apply_plot_theme_resets_generated_overrides():
    mpl.rcParams["axes.facecolor"] = "black"   # e.g. a previous snippet changed styling
    apply_plot_theme()
    assert mpl.rcParams["axes.facecolor"] == THEME["surface"]
    assert mpl.rcParams["axes.prop_cycle"].by_key()["color"][0] == THEME["accent"]
    assert mpl.rcParams["image.cmap"] == THEME["cmap"]
