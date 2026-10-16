"""Plan view of the internal layout (for review and the CAD doc)."""
import sys
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import params as P  # noqa: E402
from layout import Layout  # noqa: E402


def draw(lay, path, room=True):
    fig, ax = plt.subplots(figsize=(13, 8.6))
    if room:
        xs = np.arange(-30, 64, 0.5)
        ys = np.arange(-30, 30.5, 0.5)
        X, Y = np.meshgrid(xs, ys)
        Z = lay.ceiling(X.ravel(), Y.ravel()).reshape(X.shape) - (lay.zp + P.PCB_T)
        Z = np.where(np.array([[lay.cavity_at_pcb.contains(__import__("shapely").geometry.Point(x, y))
                                for x in xs] for y in ys]), Z, np.nan)
        cs = ax.contourf(X, Y, Z, levels=[0, 1, 2, 3, 4, 5, 6, 8, 10, 12, 14, 16, 18], cmap="Greys", alpha=0.55)
        plt.colorbar(cs, label="room above PCB top (mm)", shrink=0.8)
    B = lay.sk.st.boundary
    ax.plot(*np.vstack([B, B[:1]]).T, "k-", lw=1.0, label="skin silhouette")

    def poly(g, **kw):
        for gg in getattr(g, "geoms", [g]):
            ax.plot(*np.asarray(gg.exterior.coords).T, **kw)
            for r in gg.interiors:
                ax.plot(*np.asarray(r.coords).T, **kw)
    poly(lay.cavity_at_pcb, color="0.4", lw=0.8, ls="--")
    poly(lay.pcb, color="tab:green", lw=1.4)
    poly(lay.batt_cut, color="tab:orange", lw=1)
    poly(lay.mask_2d, color="k", lw=1)
    poly(lay.slot_2d, color="gold", lw=1.2)
    for f in lay.bridge_feet:
        poly(f, color="tab:purple", lw=1.2)
    for l in lay.leds:
        c = "tab:red" if l["bank"] == "660" else "tab:orange"
        ax.plot(l["x"], l["y"], "s", ms=6, mfc="none" if not l["fits"] else c, mec=c)
    ax.plot(lay.ntc["x"], lay.ntc["y"], "b^", ms=5)
    for s in lay.seam_leds:
        ax.plot(s["x"], s["y"], "y*", ms=7)
    for m in lay.magnets:
        ax.add_patch(plt.Circle((m["x"], m["y"]), P.MAG_D / 2, fill=False, ec="tab:blue", lw=1.2))
    from skin import BUTTON_XY
    ax.add_patch(plt.Circle(BUTTON_XY, 2, fill=False, ec="tab:cyan"))
    ax.add_patch(matplotlib.patches.Ellipse(BUTTON_XY, 2 * P.BUTTON_AXES[0], 2 * P.BUTTON_AXES[1], fill=False, ec="tab:cyan", ls=":"))
    u = lay.usb
    ax.add_patch(plt.Rectangle((u["x_back"], -P.USB_W / 2), P.USB_L, P.USB_W, fill=False, ec="m"))
    ax.set_aspect("equal")
    ax.set_xlim(-31, 65)
    ax.set_ylim(-31, 31)
    ax.grid(alpha=0.25)
    ax.set_xticks(range(-30, 66, 5))
    ax.set_yticks(range(-30, 31, 5))
    plt.tight_layout()
    plt.savefig(path, dpi=110)


if __name__ == "__main__":
    lay = Layout()
    draw(lay, sys.argv[1] if len(sys.argv) > 1 else "layout.png")
