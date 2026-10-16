"""
Figures of the routed board for the docs (matplotlib, device frame: +x to the tail, +y
to the left, seen from the top; the underside view is seen from below, mirrored).

    python plot_pcb.py  ->  docs/03-electronics/figures/pcb_top.png, pcb_bottom.png

Personal prototype for bench evaluation - NOT a medical device.
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                     # noqa: E402
import numpy as np                                  # noqa: E402
import pcbnew                                       # noqa: E402
from matplotlib.patches import Circle, Polygon as MPoly   # noqa: E402

from board import dev                               # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / "docs" / "03-electronics" / "figures"
MM = pcbnew.ToMM

INK, INK2, MUTED = "#1f2328", "#57606a", "#8c959f"
SURF = "#fcfcfb"
BOARD = "#2d3436"           # black solder mask, seen as charcoal
POUR = {"F.Cu": "#3d4f4a", "B.Cu": "#3d4a55"}
TRACK = {"F.Cu": "#c8a24a", "B.Cu": "#5b8fd6"}
PAD = "#e2c46a"


def poly_xy(shape_poly_set, i=0):
    ol = shape_poly_set.Outline(i)
    return np.array([dev(ol.CPoint(k)) for k in range(ol.PointCount())])


def plot(side="F"):
    b = pcbnew.LoadBoard(str(HERE / "kicad" / "vein_finder.kicad_pcb"))
    layer = pcbnew.F_Cu if side == "F" else pcbnew.B_Cu
    lname = "F.Cu" if side == "F" else "B.Cu"
    fig, ax = plt.subplots(figsize=(13, 8.6))
    fig.patch.set_facecolor(SURF)
    ax.set_facecolor(SURF)
    # board outline polygon(s) from Edge.Cuts
    outline = pcbnew.SHAPE_POLY_SET()
    b.GetBoardPolygonOutlines(outline)
    for i in range(outline.OutlineCount()):
        xy = poly_xy(outline, i)
        ax.add_patch(MPoly(xy, closed=True, fc=BOARD, ec=INK, lw=0.8, zorder=1))
        for h in range(outline.HoleCount(i)):
            hol = outline.Hole(i, h)
            hxy = np.array([dev(hol.CPoint(k)) for k in range(hol.PointCount())])
            ax.add_patch(MPoly(hxy, closed=True, fc=SURF, ec=INK, lw=0.8, zorder=2))
    # filled zones on this layer
    for z in b.Zones():
        if z.GetIsRuleArea() or not z.IsOnLayer(layer):
            continue
        fp = z.GetFilledPolysList(layer)
        for i in range(fp.OutlineCount()):
            ax.add_patch(MPoly(poly_xy(fp, i), closed=True, fc=POUR[lname], ec="none", zorder=3))
            for h in range(fp.HoleCount(i)):
                hol = fp.Hole(i, h)
                hxy = np.array([dev(hol.CPoint(k)) for k in range(hol.PointCount())])
                ax.add_patch(MPoly(hxy, closed=True, fc=BOARD, ec="none", zorder=4))
    # tracks and vias
    for t in b.GetTracks():
        if t.GetClass() == "PCB_VIA":
            x, y = dev(t.GetPosition())
            ax.add_patch(Circle((x, y), MM(t.GetWidth()) / 2, fc="#b9c2cc", ec="none", zorder=6))
            ax.add_patch(Circle((x, y), MM(t.GetDrillValue()) / 2, fc=SURF, ec="none", zorder=7))
        elif t.GetLayer() == layer:
            (x1, y1), (x2, y2) = dev(t.GetStart()), dev(t.GetEnd())
            ax.plot([x1, x2], [y1, y2], color=TRACK[lname], lw=MM(t.GetWidth()) * 72 / 25.4 * 13 / 95 * 8.6,
                    solid_capstyle="round", zorder=5)
    # pads and references
    for fp_ in b.GetFootprints():
        on = fp_.GetLayer() == layer
        for p in fp_.Pads():
            if not (p.IsOnLayer(layer)):
                continue
            poly = pcbnew.SHAPE_POLY_SET()
            p.TransformShapeToPolygon(poly, layer, 0, 10000)
            for i in range(poly.OutlineCount()):
                ax.add_patch(MPoly(poly_xy(poly, i), closed=True, fc=PAD, ec="none", zorder=8))
            if p.GetDrillSize().x > 0:
                x, y = dev(p.GetPosition())
                ax.add_patch(Circle((x, y), MM(p.GetDrillSize().x) / 2, fc=SURF, ec="none", zorder=9))
        if on and not fp_.GetReference().startswith("H"):
            x, y = dev(fp_.GetPosition())
            ax.text(x, y, fp_.GetReference(), fontsize=5.5, color="#ffffff", ha="center", va="center", zorder=10,
                    fontweight="bold")
    ax.set_aspect("equal")
    if side == "B":
        ax.invert_xaxis()
    ax.set_xlim(-28, 64) if side == "F" else ax.set_xlim(64, -28)
    ax.set_ylim(-30, 30)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(colors=MUTED, labelsize=7)
    ax.set_xlabel("x (mm), +x toward the tail" + ("" if side == "F" else " - seen from below"), color=INK2, fontsize=8)
    ax.set_ylabel("y (mm)", color=INK2, fontsize=8)
    title = ("Top: MCU, driver, charger, status seam; " if side == "F" else "Underside: the LED ring and the NTC; ")
    ax.set_title(title + ("gold = top copper" if side == "F" else "blue = bottom copper"), loc="left", color=INK, fontsize=10)
    OUT.mkdir(parents=True, exist_ok=True)
    f = OUT / f"pcb_{'top' if side == 'F' else 'bottom'}.png"
    fig.savefig(f, dpi=150, bbox_inches="tight", facecolor=SURF)
    plt.close(fig)
    return f


if __name__ == "__main__":
    sides = sys.argv[1:] or ["F", "B"]
    for s in sides:
        print(plot(s))
