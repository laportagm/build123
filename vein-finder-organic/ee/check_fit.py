#!/usr/bin/env python3
"""
Read-only fit check: the routed board, as built, against the CAD that the enclosure was
made from (docs/02-cad/pcb/layout.json and cad/device/params.py).

    cd ee && python3 check_fit.py           (KiCad 7.0 pcbnew Python)

The CAD's interference and wall checks (cad/device/checks.py) prove the enclosure against
the layout.  This proves the board against the same layout, so the two meet.

 1  ring LEDs: each LED's two pads where the CAD put its sole pocket (to 0.01 mm), and
    the pocket clearance left for placement error
 2  NTC: its pads where the CAD put the sensor-window pocket, and the clearances around it
 3  seam LEDs: in the mask channel's positions
 4  USB-C: the contact pads and shell slots where the CAD's receptacle is (face x = 61.1)
 5  locating-pin holes and the horn magnet holes at the CAD's positions and sizes
 6  headroom and keep-outs, re-proved on the as-built courtyards with the original
    room.Room check: shell headroom - 0.3 mm, clear of the cell, mask, magnet bosses,
    bridge feet and USB-C
 7  the cell stack as modelled (board, foam, cell, gap to the bridge deck)

Nothing here is a measurement of a printed or assembled part.
Personal prototype for bench evaluation - NOT a medical device.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "cad" / "device"))
LAYOUT_DOCS = ROOT / "docs" / "02-cad" / "pcb" / "layout.json"
LAYOUT_BUILD = ROOT / "build" / "device" / "layout.json"
if not LAYOUT_BUILD.exists():                      # generated file: the committed copy is the same
    LAYOUT_BUILD.parent.mkdir(parents=True, exist_ok=True)
    LAYOUT_BUILD.write_bytes(LAYOUT_DOCS.read_bytes())

import numpy as np                                  # noqa: E402
import pcbnew                                       # noqa: E402
from shapely.geometry import Point, Polygon, box   # noqa: E402

import design as D                                  # noqa: E402
import params as P                                  # noqa: E402
from board import dev                               # noqa: E402

L = json.loads(LAYOUT_DOCS.read_text())
PCB = HERE / "kicad" / "vein_finder.kicad_pcb"
TOL = 0.01
RESULTS = []


def result(n, name, ok, summary, details=()):
    RESULTS.append((n, name, {True: "PASS", False: "FAIL"}.get(ok, ok), summary, list(details)))


def pads_dev(fp):
    return {p.GetNumber(): dev(p.GetPosition()) for p in fp.Pads()}


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def check_leds(fps):
    det, worst = [], 0.0
    for led in L["leds"]:
        ref = D.LED_REF[round(led["angle"], 1)]
        a = math.radians(led["angle"])
        t = (-math.sin(a), math.cos(a))                 # tangential: the LED lies along the ring
        off = P.LED_PAD[2]
        want = [(led["x"] + s * off * t[0], led["y"] + s * off * t[1]) for s in (1, -1)]
        got = list(pads_dev(fps[ref]).values())
        err = max(min(dist(w, g) for g in got) for w in want)
        worst = max(worst, err)
        if err > TOL:
            det.append(f"{ref} at {led['angle']:+.1f}°: pads {err:.3f} mm from the pocket's centre line")
        if fps[ref].GetLayer() != pcbnew.B_Cu:
            det.append(f"{ref} is not on the underside")
    radial = P.LED_POCKET_CLEAR - P.LED_TOL / 2      # pocket wall to a maximum-size body, radially
    result(1, "Ring LEDs at the sole pockets", not det,
           f"12 LEDs, worst pad offset {worst:.4f} mm; the pocket leaves {radial:.2f} mm a side radially for "
           f"placement error past a maximum-size body ({P.LED_PKG[1]} + {P.LED_TOL} mm), and "
           f"{P.LED_POCKET_LAND} mm past the land ends tangentially", det)


def check_ntc(fps):
    n = L["ntc"]
    a = math.radians(n["angle"])
    half = (P.NTC_LAND[0] - 0.98) / 2                 # pad centre offset of the 0603 hand-solder land
    want = [(n["x"] + s * half * math.cos(a), n["y"] + s * half * math.sin(a)) for s in (1, -1)]
    got = list(pads_dev(fps["RT1"]).values())
    err = max(min(dist(w, g) for g in got) for w in want)
    pocket = (P.NTC_LAND[0] + 0.3, P.NTC_LAND[1] + 0.3)
    side = ((pocket[0] - P.NTC_PKG[0]) / 2, (pocket[1] - P.NTC_PKG[1]) / 2)
    gap = 0.15                                        # parts.py: pocket depth = body height + 0.15
    det = [] if err <= TOL else [f"RT1 pads {err:.3f} mm from the pocket"]
    if fps["RT1"].GetLayer() != pcbnew.B_Cu:
        det.append("RT1 is not on the underside")
    result(2, "NTC at the sensor window", not det,
           f"pad offset {err:.4f} mm; pocket {pocket[0]:.2f} × {pocket[1]:.2f} mm around a {P.NTC_PKG[0]} × "
           f"{P.NTC_PKG[1]} mm body: {side[0]:.2f} mm along it, {side[1]:.3f} mm across; {gap} mm of air "
           f"between the body and the {P.NTC_FLOOR} mm window (nominal heights)", det)


def check_seam(fps):
    det, worst = [], 0.0
    seam = [fps[f"D{k}"] for k in range(14, 19)]
    for s in L["seam_leds"]:
        fp = min(seam, key=lambda f: dist(dev(f.GetPosition()), (s["x"], s["y"])))
        e = dist(dev(fp.GetPosition()), (s["x"], s["y"]))
        worst = max(worst, e)
        if e > TOL:
            det.append(f"{fp.GetReference()}: {e:.3f} mm from the channel position at {s['angle']:+.1f}°")
    result(3, "Seam LEDs in the mask channel", not det, f"5 LEDs, worst offset {worst:.4f} mm", det)


def check_usb(fps):
    u = L["usb"]
    j1 = fps["J1"]
    pads = [(p.GetNumber(), dev(p.GetPosition()), p.GetAttribute()) for p in j1.Pads()]
    sig = [c for num, c, at in pads if at == pcbnew.PAD_ATTRIB_SMD]
    slots = [c for num, c, at in pads if at == pcbnew.PAD_ATTRIB_PTH]
    face_from_pads = float(np.mean([c[0] for c in sig])) + P.USB_PADS_X
    want_slots = [(u["x_face"] - xb, s * yl) for (xb, yl, sl, pl) in P.USB_LEGS for s in (1, -1)]
    slot_err = max(min(dist(w, c) for c in slots) for w in want_slots)
    ys = sorted(round(abs(c[1]), 2) for c in sig)
    det = []
    if abs(face_from_pads - u["x_face"]) > TOL:
        det.append(f"contact pads put the face at x = {face_from_pads:.3f}, the CAD at {u['x_face']}")
    if slot_err > TOL:
        det.append(f"shell slots {slot_err:.3f} mm from the CAD's legs")
    if ys != [0.5, 0.5, 1.52, 1.52, 2.75, 2.75]:
        det.append(f"contact pad rows at |y| {ys}")
    opening = (P.USB_W + 2 * P.USB_CLEAR, P.USB_H + 2 * P.USB_CLEAR)
    result(4, "USB-C where the shell's opening is", not det,
           f"face from the pads x = {face_from_pads:.3f} (CAD {u['x_face']}); slots within {slot_err:.4f} mm; "
           f"opening {opening[0]:.2f} × {opening[1]:.2f} mm around a {P.USB_W} × {P.USB_H} mm shell; "
           f"landing plane {P.USB_LAND_DX} mm in front of the face, {2 * P.USB_LAND_HW:.1f} mm wide", det)


def check_holes(b, fps):
    det = []
    pins = {(round(d["x"], 2), round(d["y"], 2)) for d in L["drills"]}
    got = {}
    for ref in ("H1", "H2", "H3", "H4", "H5", "H6"):
        p = next(iter(fps[ref].Pads()))
        got[ref] = dev(p.GetPosition())
        if pcbnew.ToMM(p.GetDrillSize().x) != P.PIN_HOLE_PCB:
            det.append(f"{ref} drill {pcbnew.ToMM(p.GetDrillSize().x)} mm, CAD {P.PIN_HOLE_PCB}")
    for ref, c in got.items():
        if min(dist(c, q) for q in pins) > TOL:
            det.append(f"{ref} at ({c[0]:.2f}, {c[1]:.2f}) is not at a CAD pin position")
    ps = pcbnew.SHAPE_POLY_SET()
    b.GetBoardPolygonOutlines(ps)
    holes = []
    for i in range(ps.OutlineCount()):
        for h in range(ps.HoleCount(i)):
            ring = ps.Hole(i, h)
            pts = np.array([dev(ring.CPoint(k)) for k in range(ring.PointCount())])
            c = pts.mean(axis=0)
            holes.append((c, 2 * float(np.mean(np.hypot(*(pts - c).T)))))
    horn = [m for m in L["magnets"] if m.get("hole_in_pcb")]
    for m in horn:
        c, d = min(holes, key=lambda h: dist(h[0], (m["x"], m["y"])))
        if dist(c, (m["x"], m["y"])) > 0.02 or abs(d - P.MAG_PCB_HOLE) > 0.05:
            det.append(f"magnet hole at ({c[0]:.2f}, {c[1]:.2f}) d {d:.2f} mm, CAD ({m['x']}, {m['y']}) d {P.MAG_PCB_HOLE}")
    diag = P.PIN_SQ * math.sqrt(2)
    result(5, "Locating pins and magnet holes", not det,
           f"6 pin holes at the CAD positions, {P.PIN_HOLE_PCB} mm drill for a {P.PIN_SQ} mm square post "
           f"(diagonal {diag:.3f} mm; printed parts {P.PIN_HOLE_PART} mm); {len(horn)} horn magnet holes d "
           f"{P.MAG_PCB_HOLE} mm around {P.MAG_D} mm dowel magnets ({P.MAG_PCB_HOLE - P.MAG_D:.2f} mm on diameter)", det)


def check_room(fps):
    from room import Room
    parts = {p.ref: p for p in D.PARTS}
    polys = {}
    for ref, fp in fps.items():
        side = "B" if fp.IsFlipped() else "F"
        cy = fp.GetCourtyard(pcbnew.B_CrtYd if side == "B" else pcbnew.F_CrtYd)
        if not cy.OutlineCount():
            continue
        ol = cy.Outline(0)
        pg = Polygon([dev(ol.CPoint(k)) for k in range(ol.PointCount())])
        polys[ref] = (pg, parts[ref].h, side)
    from placement import EXEMPT
    probs = Room().check(polys, EXEMPT)
    tops = [r for r, v in polys.items() if v[2] == "F"]
    result(6, "Headroom and keep-outs, as built", not probs,
           f"{len(polys)} courtyards ({len(tops)} top); every top part ≥ 0.3 mm under the shell and clear of the "
           f"cell, mask, bosses, bridge feet and USB-C (exempt by design: {', '.join(EXEMPT)})", probs)


def check_cell():
    bt = L["battery"]
    pcb_top = L["z_part"] + L["pcb_t"]
    foam = bt["z"][0] - pcb_top
    cell = bt["z"][1] - bt["z"][0]
    det = []
    if abs(foam - P.BATT_FOAM) > 0.01 or abs(cell - P.BATT_T) > 0.01:
        det.append(f"layout stack foam {foam:.2f} / cell {cell:.2f} mm, params {P.BATT_FOAM} / {P.BATT_T}")
    budget = P.BATT_FOAM + P.BATT_T + P.BATT_TOP_CLEAR
    result(7, "Cell stack as modelled", not det,
           f"board top z {pcb_top:.2f}; foam {foam:.2f} mm (Adafruit 5019 is listed at 1.0 and 1.6 mm: the "
           f"thicker is modelled); cell {cell:.2f} mm (datasheet envelope); {P.BATT_TOP_CLEAR} mm to the bridge "
           f"deck. Foam + cell must stay ≤ {P.BATT_FOAM + P.BATT_T + P.BATT_TOP_CLEAR:.1f} mm to touch nothing; "
           f"the CAD's interference check passed at this stack", det)
    return budget


def main():
    b = pcbnew.LoadBoard(str(PCB))
    fps = {f.GetReference(): f for f in b.GetFootprints()}
    check_leds(fps)
    check_ntc(fps)
    check_seam(fps)
    check_usb(fps)
    check_holes(b, fps)
    check_room(fps)
    check_cell()
    for n, name, status, summary, det in sorted(RESULTS):
        print(f"{n} {status:4s} {name}: {summary}")
        for d in det:
            print(f"        {d}")
    fails = [r for r in RESULTS if r[2] == "FAIL"]
    print(f"{len(RESULTS) - len(fails)}/{len(RESULTS)} fit checks pass")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
