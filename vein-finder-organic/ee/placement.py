"""
Component placement (gate 3), in the device frame of the CAD (mm, window centre at the
origin, +x toward the tail, +y to the left; angles CCW).

Blocks:
  * underside: the 12 ring LEDs (tangential) and the NTC, exactly where the CAD put their
    sole pockets (build/device/layout.json);
  * +y front arc: MCU, its decoupling, programming/debug pads;
  * -y front arc: boost LED driver (TPS61169, inductor, Schottky, output caps, sense
    resistor, bank FETs) -- the strings start next to it, so VOUT stays short;
  * +y side arm: charger and the battery / button wire pads; -y side arm: USB-C CC and
    VBUS-sense resistors;
  * status seam: five 0603 LEDs inside the mask channel, their resistors just outside it.

The big parts are placed by hand.  Small passives are placed by a spiral search around an
anchor (next to the pin they serve), and every courtyard is proved by `room.Room.check`:
inside the free top area, clear of the mask, magnet bosses, bridge feet and the USB-C
receptacle, and at most (shell headroom - 0.3 mm) tall.
"""
from __future__ import annotations

import functools
import math
import re
from pathlib import Path

from shapely import affinity
from shapely.geometry import box

import design as D
from room import LAYOUT, Room
from sexp import first, parse

HERE = Path(__file__).resolve().parent
FPDIRS = [HERE.parent / "build" / "kicadlib" / "fp", HERE / "lib"]


@functools.lru_cache(maxsize=None)
def courtyard_local(fp):
    """Courtyard rectangle of a footprint in its own frame (KiCad axes, y down): the bounds
    of its F.CrtYd lines and rectangles, read with the S-expression parser."""
    lib, name = fp.split(":")
    for d in FPDIRS:
        f = d / f"{lib}.pretty" / f"{name}.kicad_mod"
        if f.exists():
            xs, ys = [], []
            for g in parse(f.read_text())[0]:
                if not (isinstance(g, list) and g and g[0] in ("fp_line", "fp_rect")):
                    continue
                layer = first(g, "layer")
                if layer is None or str(layer[1]) != "F.CrtYd":
                    continue
                for key in ("start", "end"):
                    pt = first(g, key)
                    xs.append(float(pt[1]))
                    ys.append(float(pt[2]))
            if not xs:
                raise ValueError(f"{fp}: no F.CrtYd lines or rectangles")
            return min(xs), min(ys), max(xs), max(ys)
    raise FileNotFoundError(fp)


def courtyard(part, x, y, ang, side):
    """Courtyard polygon in the device frame.  KiCad local (u, v) with v down maps to device
    (u, -v); the bottom side mirrors v once more (KiCad flips about the x axis)."""
    u0, v0, u1, v1 = courtyard_local(part.footprint)
    r = box(u0, -v1, u1, -v0) if side == "F" else box(u0, v0, u1, v1)
    return affinity.translate(affinity.rotate(r, ang, origin=(0, 0)), x, y)


def pol(r, a_deg):
    a = math.radians(a_deg)
    return r * math.cos(a), r * math.sin(a)


# ----------------------------------------------------------------------------- manual
def manual():
    P = {}
    u = LAYOUT["usb"]
    P["J1"] = (u["x_face"], 0.0, 0.0, "F")
    # underside ring: footprint x axis (the pads) along the tangent
    for led in LAYOUT["leds"]:
        P[D.LED_REF[round(led["angle"], 1)]] = (led["x"], led["y"], led["angle"] + 90.0, "B")
    n = LAYOUT["ntc"]
    P["RT1"] = (n["x"], n["y"], n["angle"], "B")              # pads along the tangent, outside the ring
    # status LEDs in the mask channel, tangential
    for i, s in enumerate(LAYOUT["seam_leds"]):
        P[f"D{14 + i}"] = (s["x"], s["y"], s["angle"] + 90.0, "F")
    # locating pins (positions from the CAD)
    for p in D.PARTS:
        if p.ref.startswith("H"):
            x, y, a = p.place
            P[p.ref] = (x, y, a, "F")
    # MCU on the +y front arc, long axis tangential; pins 1/14 (supply) face -x
    P["U1"] = (2.0, 22.0, 90.0, "F")
    for i, ref in enumerate(("TP3", "TP4", "TP5")):           # UPDI, VBAT, GND: 2.54 mm row
        P[ref] = (8.6 + 2.54 * i, 21.6, 0.0, "F")
    P["TP6"] = (8.6, 24.4, 0.0, "F")
    P["TP7"] = (11.14, 24.4, 0.0, "F")
    # boost driver on the -y front arc: inductor, IC, then diode and output caps.  U3 turned
    # 180 deg: VIN (pin 5) faces C7 and L1, SW (pin 1) faces D1 and L1's SW pad, FB faces R9
    P["L1"] = (-1.0, -22.8, 0.0, "F")
    P["U3"] = (3.4, -20.2, 180.0, "F")
    # charger on the wide front part of the +y arm
    P["U2"] = (25.0, 24.0, 0.0, "F")
    # wire pads on the +y arm behind the bridge foot: button, then battery
    P["TP8"] = (41.0, 24.0, 0.0, "F")
    P["TP9"] = (43.0, 24.0, 0.0, "F")
    P["TP1"] = (45.9, 23.4, 90.0, "F")
    P["TP2"] = (49.6, 22.9, 90.0, "F")
    return P


# anchors for the spiral search: (ref, (x, y)[, angles to try]) in priority order.  D1 at
# 180 deg puts its cathode (VOUT) toward C5/C6 and its anode (SW) toward L1; C7 at 180 deg
# puts its VBAT pad next to U3's VIN.
AUTO = [
    ("D1", (4.0, -24.0), (180.0, 90.0)), ("C7", (-1.0, -19.0), (180.0, 90.0)),
    ("C5", (8.6, -23.4)), ("C6", (11.2, -23.4)),
    ("R9", (6.8, -18.2)), ("R10", (-4.5, -24.0)),
    ("Q1", (8.6, -19.6)), ("Q2", (12.3, -19.6)), ("R11", (5.5, -16.8)), ("R12", (15.0, -19.0)),
    ("C3", (-4.3, 20.5)), ("C4", (-4.3, 23.4)), ("R8", (-4.5, 25.5)),
    ("C1", (21.6, 23.6)), ("C2", (28.6, 23.0)), ("R3", (28.6, 25.2)), ("R4", (21.6, 25.6)),
    ("R1", (44.0, -23.0)), ("R2", (47.5, -23.0)), ("R5", (40.5, -23.4)), ("R6", (42.5, -25.0)), ("R7", (46.0, -24.5)),
]


def seam_resistor_anchors():
    out = []
    for i, s in enumerate(LAYOUT["seam_leds"]):
        a = s["angle"]
        out.append((f"R{13 + i}", pol(22.5, a if abs(a) > 20 else math.copysign(28.0, a) if a else 26.0)))
    return out


EXEMPT = ("J1", "D14", "D15", "D16", "D17", "D18", "H1", "H2", "H3", "H4", "H5", "H6")


def place(verbose=True):
    room = Room()
    parts = {p.ref: p for p in D.PARTS if p.on_board}
    P = manual()
    polys = {r: (courtyard(parts[r], *P[r]), parts[r].h, P[r][3]) for r in P}
    probs = room.check(polys, EXEMPT)
    if probs and verbose:
        print("manual placement problems:", probs)
    for entry in AUTO + seam_resistor_anchors():
        ref, (ax, ay) = entry[:2]
        angles = entry[2] if len(entry) > 2 else (0.0, 90.0)
        part = parts[ref]
        done = False
        for rad in [0.0] + [0.25 * k for k in range(1, 60)]:
            n = max(1, int(2 * math.pi * rad / 0.5))
            for k in range(n):
                t = 2 * math.pi * k / n
                x, y = ax + rad * math.cos(t), ay + rad * math.sin(t)
                for ang in angles:
                    pg = courtyard(part, x, y, ang, "F")
                    cand = (pg, part.h, "F")
                    if not room.check({ref: cand}, EXEMPT) and not any(
                            pg.intersects(v[0]) for r, v in polys.items() if v[2] == "F"):
                        P[ref] = (round(x, 2), round(y, 2), ang, "F")
                        polys[ref] = cand
                        done = True
                        break
                if done:
                    break
            if done:
                break
        if not done:
            raise RuntimeError(f"no place found for {ref} near {(ax, ay)}")
    missing = set(parts) - set(P)
    if missing:
        raise RuntimeError(f"unplaced: {sorted(missing)}")
    probs = room.check(polys, EXEMPT)
    return P, polys, probs


def plot(P, polys, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    room = Room()
    fig, ax = plt.subplots(figsize=(16, 10))
    for g in getattr(room.board, "geoms", [room.board]):
        ax.plot(*g.exterior.xy, "k-", lw=0.8)
        for i in g.interiors:
            ax.plot(*i.xy, "k-", lw=0.8)
    for k in room.keepouts.values():
        for g in getattr(k, "geoms", [k]):
            ax.fill(*g.exterior.xy, fc="tab:red", alpha=0.15)
    for r, (pg, h, side) in polys.items():
        ax.fill(*pg.exterior.xy, fc="tab:blue" if side == "F" else "tab:orange", alpha=0.35, ec="k", lw=0.4)
        c = pg.centroid
        ax.text(c.x, c.y, r, fontsize=5, ha="center", va="center")
    ax.set_aspect("equal")
    ax.grid(alpha=0.25)
    fig.savefig(path, dpi=130, bbox_inches="tight")


if __name__ == "__main__":
    P, polys, probs = place()
    print("problems:", probs or "none")
    plot(P, polys, HERE.parent / "build" / "device" / "placement.png")
    for r in sorted(P, key=lambda s: (re.sub(r"\d", "", s), int(re.sub(r"\D", "", s) or 0))):
        print(f"{r:5s} {P[r]}")
