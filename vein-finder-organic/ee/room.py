"""
Board real estate for gate 3: where top-side parts may go and how tall they may be.

Builds (once, cached in build/device/room.npz) the height of the shell's inner surface
above the PCB top on a 0.25 mm grid, and the keep-out polygons from the CAD layout:
the seam mask and its ears, the four magnet bosses (they land on the board), the bridge
feet, the USB-C receptacle, and the board edge.  `Room.check(part polys)` is used by the
placement to prove every part fits.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from shapely.geometry import Point, Polygon, box, shape
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "cad" / "device"))
CACHE = ROOT / "build" / "device" / "room.npz"
LAYOUT = json.loads((ROOT / "build" / "device" / "layout.json").read_text())
CLEAR_Z = 0.3          # part top to the shell's inner surface
CLEAR_XY = 0.3         # part courtyard to a keep-out


def _polys(rings_list):
    out = []
    for rings in rings_list:
        out.append(Polygon(rings[0], rings[1:]))
    return unary_union(out)


class Room:
    def __init__(self, step=0.25):
        import params as P
        self.P = P
        L = LAYOUT
        self.board = _polys(L["board_outline"])
        self.board_solid = self.board        # outline already has the magnet holes and cut-outs
        mask = _polys(L["mask_outline"]).union(unary_union([Polygon(e) for e in L["mask_ears"]]))
        bosses = unary_union([Point(m["x"], m["y"]).buffer(P.MAG_D / 2 + P.MAG_BOSS_WALL + 0.2) for m in L["magnets"]])
        feet = unary_union([Polygon(f) for f in L["bridge_feet"]])
        u = L["usb"]
        usb = box(u["x_tails"] - 0.6, -P.USB_W / 2 - 1.9, u["x_face"], P.USB_W / 2 + 1.9)   # body, tails, leg pads
        self.keepouts = dict(mask=mask, bosses=bosses, feet=feet, usb=usb)
        self.free_top = self.board.buffer(-0.3).difference(unary_union(list(self.keepouts.values())).buffer(CLEAR_XY))
        if CACHE.exists():
            d = np.load(CACHE)
            self.xs, self.ys, self.room = d["xs"], d["ys"], d["room"]
        else:
            from layout import Layout
            lay = Layout()
            x0, y0, x1, y1 = self.board.bounds
            self.xs = np.arange(x0, x1 + step, step)
            self.ys = np.arange(y0, y1 + step, step)
            X, Y = np.meshgrid(self.xs, self.ys)
            c = lay.ceiling(X.ravel(), Y.ravel()).reshape(X.shape)
            self.room = c - (lay.zp + P.PCB_T)
            np.savez(CACHE, xs=self.xs, ys=self.ys, room=self.room)

    def room_at(self, poly):
        """Lowest inner-surface height above the PCB top over a polygon (grid samples inside
        it, plus its vertices)."""
        x0, y0, x1, y1 = poly.bounds
        ix = (self.xs >= x0 - 0.25) & (self.xs <= x1 + 0.25)
        iy = (self.ys >= y0 - 0.25) & (self.ys <= y1 + 0.25)
        sub = self.room[np.ix_(iy, ix)]
        X, Y = np.meshgrid(self.xs[ix], self.ys[iy])
        inside = np.array([poly.buffer(0.3).contains(Point(a, b)) for a, b in zip(X.ravel(), Y.ravel())],
                          dtype=bool).reshape(X.shape)
        vals = sub[inside]
        return float(np.nanmin(vals)) if vals.size else float("nan")

    def check(self, polys, exempt=()):
        """polys: {ref: (shapely courtyard, height, side)} -> list of problems.  `exempt`:
        parts that ARE a keep-out's reason (USB-C, status LEDs in the mask, locating pins)
        and skip the free-area test; underside courtyards may touch the board edge (the
        lands keep 0.25 mm)."""
        probs = []
        refs = list(polys)
        for r in refs:
            pg, h, side = polys[r]
            if side == "F":
                if r not in exempt and not self.free_top.contains(pg):
                    probs.append(f"{r}: outside the free top area")
                rm = self.room_at(pg)
                if not (rm >= h + CLEAR_Z):
                    probs.append(f"{r}: room {rm:.2f} < height {h:.2f} + {CLEAR_Z}")
            else:
                if not self.board.buffer(0.15).contains(pg):
                    probs.append(f"{r}: off the board")
        for i, a in enumerate(refs):
            for b in refs[i + 1:]:
                if polys[a][2] == polys[b][2] and polys[a][0].intersects(polys[b][0]):
                    probs.append(f"{a} overlaps {b}")
        return probs


if __name__ == "__main__":
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    R = Room()
    fig, ax = plt.subplots(figsize=(14, 9))
    X, Y = np.meshgrid(R.xs, R.ys)
    inb = np.array([R.board.contains(Point(a, b)) for a, b in zip(X.ravel(), Y.ravel())]).reshape(X.shape)
    cs = ax.contourf(X, Y, np.where(inb, R.room, np.nan), levels=[0, 1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 12, 20], cmap="Greys")
    fig.colorbar(cs, label="room above PCB top (mm)")
    for nm, k in R.keepouts.items():
        for g in getattr(k, "geoms", [k]):
            ax.fill(*g.exterior.xy, fc="tab:red", alpha=0.3)
    for g in getattr(R.free_top, "geoms", [R.free_top]):
        ax.plot(*g.exterior.xy, "g-", lw=0.8)
        for i in g.interiors:
            ax.plot(*i.xy, "g-", lw=0.8)
    ax.set_aspect("equal"); ax.grid(alpha=0.3)
    ax.set_xticks(np.arange(-26, 62, 2)); ax.set_yticks(np.arange(-28, 29, 2))
    ax.tick_params(labelsize=6)
    out = ROOT / "build" / "device" / "room.png"
    fig.savefig(out, dpi=110, bbox_inches="tight")
    print(out, "free top area", round(R.free_top.area, 1), "mm2")
