"""
Gate-2 figures, drawn from the built model (not redrawn by hand):

  fig_layout.png    plan view of everything inside the stone, with the room above the PCB
  fig_section.png   true centre-line section (y = 0) through every part

Palette: dataviz reference instance, light surface #fcfcfb.  Categorical slots in fixed
order -- blue (660 nm bank), orange (620 nm bank), aqua (PCB), yellow (seam) -- validated
with validate_palette.js (all checks pass; aqua/yellow are below 3:1 on the surface, so
every element is also direct-labelled).  The room-above-PCB shading is a one-hue grey ramp.
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from matplotlib.patches import Ellipse, FancyBboxPatch  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "cad" / "device"))
sys.path.insert(0, str(ROOT / "render"))

SURFACE, INK, INK2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#9a9993", "#e6e5e1"
BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
DARK, STONE = "#2b2b2b", "#cfc9bf"
FIG = HERE / "figures"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": MUTED, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "text.color": INK, "font.size": 9, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
})


def _poly(ax, g, **kw):
    for gg in getattr(g, "geoms", [g]):
        ax.plot(*np.asarray(gg.exterior.coords).T, **kw)
        for r in gg.interiors:
            ax.plot(*np.asarray(r.coords).T, **kw)


def _fill(ax, g, **kw):
    for gg in getattr(g, "geoms", [g]):
        ax.fill(*np.asarray(gg.exterior.coords).T, **kw)


def fig_layout(lay, path):
    import params as P
    from shapely.geometry import Point
    from skin import BUTTON_XY, DISH
    fig, ax = plt.subplots(figsize=(11.5, 8.4))
    xs = np.arange(-30, 64, 0.5)
    ys = np.arange(-30, 30.5, 0.5)
    X, Y = np.meshgrid(xs, ys)
    Z = lay.ceiling(X.ravel(), Y.ravel()).reshape(X.shape) - (lay.zp + P.PCB_T)
    inside = np.array([[lay.cavity_at_pcb.contains(Point(x, y)) for x in xs] for y in ys])
    Z = np.where(inside, Z, np.nan)
    cmap = LinearSegmentedColormap.from_list("room", ["#f4f3f0", "#8f8e88"])
    cs = ax.contourf(X, Y, Z, levels=[0, 2, 4, 6, 8, 12, 16, 20], cmap=cmap, zorder=0)
    cb = plt.colorbar(cs, ax=ax, shrink=0.72, pad=0.015)
    cb.set_label("room above the PCB top (mm)", color=INK2)
    B = lay.sk.st.boundary
    ax.plot(*np.vstack([B, B[:1]]).T, color=INK, lw=1.1, zorder=2)
    _poly(ax, lay.cavity_at_pcb, color=MUTED, lw=0.8, ls=(0, (4, 3)), zorder=2)
    _poly(ax, lay.pcb, color=AQUA, lw=1.6, zorder=3)
    bx0, bx1, by = P.BATT_X0, P.BATT_X0 + P.BATT_W, P.BATT_L / 2
    ax.add_patch(plt.Rectangle((bx0, -by), P.BATT_W, P.BATT_L, fc="#ffffff", ec=INK, lw=1.0, zorder=3))
    ax.text(0.5 * (bx0 + bx1), -15.5, "LiPo 600 mAh\n(on foam tape, on the sole)", ha="center", va="center",
            fontsize=8, color=INK2, zorder=6)
    # thumb dish and button skin
    ax.add_patch(Ellipse(BUTTON_XY, 2 * DISH["a"], 2 * DISH["b"], fc="none", ec=INK2, lw=0.9, ls=(0, (2, 2)), zorder=5))
    ax.add_patch(Ellipse(BUTTON_XY, 2 * P.BUTTON_AXES[0], 2 * P.BUTTON_AXES[1], fc="none", ec=INK2, lw=0.9, zorder=5))
    ax.plot(*BUTTON_XY, "+", color=INK, ms=9, mew=1.2, zorder=6)
    ax.text(BUTTON_XY[0], 8.6, "button skin 0.40 mm\n(in the thumb dish)", ha="center", fontsize=8, color=INK2, zorder=6)
    for f in lay.bridge_feet:
        _fill(ax, f, color=DARK, zorder=4)
    ax.annotate("button-bridge feet", xy=(lay.bridge_x, -P.BRIDGE_LEG_Y - 1.2), xytext=(lay.bridge_x + 8, -32.6),
                fontsize=8, color=INK2, ha="center", arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.7), zorder=6)
    _fill(ax, lay.mask_2d, color=DARK, zorder=4)
    _poly(ax, lay.slot_2d, color=YELLOW, lw=2.0, zorder=5)
    for s in lay.seam_leds:
        ax.plot(s["x"], s["y"], "o", ms=3.2, mfc=YELLOW, mec=INK, mew=0.5, zorder=6)
    ax.annotate("seam slot (0.7 mm wall)\n+ black mask, 5 status LEDs", xy=(13.8, -12.7), xytext=(-2, -9.6),
                fontsize=8, color=INK2, ha="center", arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.7), zorder=6)
    for l in lay.leds:
        c, mk = (BLUE, "s") if l["bank"] == "660" else (ORANGE, "D")
        ax.plot(l["x"], l["y"], mk, ms=6.2 if mk == "s" else 5.4, mfc=c, mec=SURFACE, mew=0.8, zorder=6)
    ax.plot(lay.ntc["x"], lay.ntc["y"], "^", ms=6, mfc=INK, mec=SURFACE, zorder=6)
    ax.annotate("NTC (underside)", xy=(lay.ntc["x"], lay.ntc["y"]), xytext=(8.5, 4.0), fontsize=8, color=INK2,
                ha="center", arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.7), zorder=6)
    for m in lay.magnets:
        ax.add_patch(plt.Circle((m["x"], m["y"]), P.MAG_D / 2, fc="#ffffff", ec=INK2, lw=1.0, zorder=5))
    ax.annotate("magnet dowels ×4 (Ø6.35, N42)", xy=(-12, -23.9), xytext=(-8, -32.6), fontsize=8, color=INK2,
                ha="center", arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.7), zorder=6)
    u = lay.usb
    ax.add_patch(FancyBboxPatch((u["x_back"], -P.USB_W / 2), P.USB_L, P.USB_W, boxstyle="round,pad=0,rounding_size=1.2",
                                fc="#ffffff", ec=INK2, lw=1.0, zorder=5))
    ax.text(u["x_back"] + 2.6, 0, "USB-C", rotation=90, ha="center", va="center", fontsize=7.5, color=INK2, zorder=6)
    ax.text(2, 0, "window\nØ30", ha="center", va="center", fontsize=9, color=INK2)
    ax.text(-26.5, 27.5, "PCB outline", color=AQUA, fontsize=8.5, fontweight="bold")
    ax.text(-26.5, 25.6, "(2-layer, 1.0 mm)", color=INK2, fontsize=7.5)
    # legend for the two LED banks (identity is also by marker shape)
    ax.plot([], [], "s", mfc=BLUE, mec=SURFACE, ms=6.5, label="660 nm LED, PCB underside (bank A, ×6)")
    ax.plot([], [], "D", mfc=ORANGE, mec=SURFACE, ms=5.5, label="620 nm LED, PCB underside (bank B, ×6)")
    ax.plot([], [], "-", color=INK, lw=1.1, label="skin silhouette")
    ax.plot([], [], ls=(0, (4, 3)), color=MUTED, lw=0.8, label="cavity wall at PCB height")
    leg = ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.11), ncol=2, fontsize=7.5, frameon=False)
    leg.set_zorder(10)
    ax.set_aspect("equal")
    ax.set_xlim(-31, 65)
    ax.set_ylim(-34, 31)
    ax.set_xlabel("x (mm), +x toward the tail")
    ax.set_ylabel("y (mm)")
    ax.set_title(f"Inside the stone — LED ring r = {lay.led_r:.2f} mm over ±{lay.led_a_max:.0f}°, "
                 f"PCB {lay.pcb.area / 100:.1f} cm²", color=INK, fontsize=10.5, loc="left")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def section_polys(shape, y=0.0, eps=0.004):
    """Cross-section of a solid on the plane y = const, as shapely polygons (x, z).

    The solid is intersected with a thin slab; the slab result's face lying on y + eps is
    the section (robust where raw section edges of big B-spline faces do not close)."""
    import build123d as bd
    from shapely.geometry import Polygon
    slab = bd.Pos(0, y, 0) * bd.Box(400, 2 * eps, 200)
    r = shape & slab
    if r is None:
        return []
    out = []
    for f in r.faces():
        c = f.center()
        if abs(c.Y - (y + eps)) > 1e-4 or abs(f.normal_at(c).Y) < 0.99:
            continue
        def ring(w):
            pts = []
            for e in w.edges():
                n = max(6, int(e.length / 0.12))
                pts += [(p.X, p.Z) for p in (e.position_at(t) for t in np.linspace(0, 1, n))]
            return pts
        outer = ring(f.outer_wire())
        holes = [ring(w) for w in f.inner_wires()]
        try:
            out.append(Polygon(outer, holes).buffer(0))
        except Exception:  # noqa: BLE001
            pass
    return out


def fig_section(shapes, path, zp):
    import params as P
    fig, ax = plt.subplots(figsize=(11.5, 4.6))
    style = {"sole": (DARK, "sole (black PETG)"), "top_shell": (STONE, "top shell (warm-grey PETG)"),
             "pcb": (AQUA, "PCB 1.0 mm"), "battery": ("#ffffff", "LiPo"), "bridge": ("#5a5a58", "bridge"),
             "switch": ("#8f8e88", "tact switch"), "seam_mask": ("#5a5a58", "seam mask"),
             "usb": ("#ffffff", "USB-C"), "magnets": ("#ffffff", "magnet"), "ntc": (INK, "NTC")}
    from matplotlib.patches import PathPatch
    from matplotlib.path import Path as MPath
    for name, (col, lab) in style.items():
        for poly in section_polys(shapes[name]):
            for p in getattr(poly, "geoms", [poly]):
                verts, codes = [], []
                for ring in [p.exterior] + list(p.interiors):
                    c = np.asarray(ring.coords)
                    verts += c.tolist()
                    codes += [MPath.MOVETO] + [MPath.LINETO] * (len(c) - 2) + [MPath.CLOSEPOLY]
                ax.add_patch(PathPatch(MPath(verts, codes), fc=col, ec=INK, lw=0.5,
                                       zorder=3 if name != "top_shell" else 2))
    ax.axhline(zp, color=YELLOW, lw=1.0, ls=(0, (5, 3)), zorder=1)
    ax.text(-8, zp + 0.35, "waterline / parting plane", color=INK2, fontsize=8)
    notes = [((54.5, 17.6), (58.0, 24.5), "wall 1.8 mm"), ((35.0, 22.2), (35.0, 28.2), "button skin 0.40 mm"),
             ((18.9, 11.4), (6.0, 18.5), "seam slot: 0.7 mm wall"), ((38.8, 18.0), (46.0, 27.6), "tact switch on the bridge"),
             ((36.0, 7.5), (46.0, 1.0), "LiPo on foam on the sole"), ((61.7, 5.6), (63.0, 12.5), "USB-C landing"),
             ((18.6, 3.8), (9.0, 1.0), "NTC pocket"), ((19.0, 7.0), (6.0, 11.5), "seam mask channel")]
    for xy, xyt, txt in notes:
        ax.annotate(txt, xy=xy, xytext=xyt, fontsize=8, color=INK2, ha="center",
                    arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.7), zorder=6)
    ax.set_aspect("equal")
    ax.set_xlim(-10, 66)
    ax.set_ylim(-1, 30)
    ax.set_xlabel("x along the centre line (mm); the window spans x = −15 … 15")
    ax.set_ylabel("z (mm)")
    ax.set_title("Centre-line section (y = 0), cut from the built parts", color=INK, fontsize=10.5, loc="left")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    import build123d as bd
    from layout import Layout
    FIG.mkdir(parents=True, exist_ok=True)
    lay = Layout()
    fig_layout(lay, FIG / "fig_layout.png")
    shapes = {p.stem: bd.import_brep(str(p)) for p in sorted((ROOT / "build" / "device" / "brep").glob("*.brep"))}
    fig_section(shapes, FIG / "fig_section.png", lay.zp)
    print("figures ->", FIG)
