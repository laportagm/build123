"""
Gate-2 parts (build123d / OpenCascade).

Printed:
  top_shell   warm-grey PETG, 1.8 mm wall; thin spots: light seam (0.7) and button skin (0.45)
  sole        black PETG, light-tight optical sole with LED pockets, NTC and magnet pockets
  seam_mask   black PETG, light channel from the status LEDs to the seam slot
  bridge      black PETG, carries the tact switch under the button skin, stands on the PCB
Bought / stand-ins (for the assembly, interference checks and renders):
  pcb, battery, magnets, leds, ntc, switch, usb receptacle, seam LEDs

Every boolean result is checked for validity; `build_all()` returns a dict of shapes.
"""
from __future__ import annotations

import math
import time

import build123d as bd
import numpy as np
from build123d import Align, Keep, Plane, Pos, Rot

import params as P
from layout import Layout
from skin import BUTTON_XY, Skin

C3 = (Align.CENTER, Align.CENTER, Align.MIN)


def smoothstep5(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * t * (t * (6 * t - 15) + 10)


def wall_thickness(x, y):
    """Top-shell wall: 1.8 mm, thinning smoothly to 0.45 mm inside the button ellipse."""
    a, b = P.BUTTON_AXES
    rho = np.sqrt(((x - BUTTON_XY[0]) / a) ** 2 + ((y - BUTTON_XY[1]) / b) ** 2)
    s = (rho - 1.0) * min(a, b) / P.MEMBRANE_TAPER
    w = 1.0 - smoothstep5(s)
    return P.WALL - (P.WALL - P.MEMBRANE_WALL) * w


def _check(shape, name):
    ok = shape.is_valid
    if not ok:
        raise RuntimeError(f"{name}: invalid solid")
    return shape


def _poly_face(poly, z):
    """shapely Polygon (holes allowed) -> build123d Face on the plane z."""
    def ring(r):
        return bd.Wire.make_polygon([bd.Vector(x, y, z) for x, y in list(r.coords)[:-1]], close=True)
    return bd.Face(ring(poly.exterior), [ring(r) for r in poly.interiors])


def _stadium_yz(w, h, x0, x1, zc):
    """Stadium (rounded-end slot, w along y, h along z) extruded along +x from x0 to x1."""
    sk = bd.Plane.YZ.offset(x0) * bd.SlotOverall(w, h)
    sol = bd.extrude(sk, amount=x1 - x0)
    return Pos(0, 0, zc) * sol


class Parts:
    def __init__(self, sk: Skin | None = None, lay: Layout | None = None, verbose=True):
        t0 = time.time()
        self.verbose = verbose
        self.sk = sk or Skin(verbose=False)
        self.lay = lay or Layout(self.sk)
        self.zp = self.sk.z_part
        self.cav = {}
        self.info = {}
        self.log(f"skin + layout {time.time() - t0:.1f}s")

    def log(self, msg):
        if self.verbose:
            print("[parts]", msg, flush=True)

    # ---------------------------------------------------------------- cavities
    def cavity(self, key):
        if key not in self.cav:
            t0 = time.time()
            t = wall_thickness if key == "wall" else float(key)
            sol, info = self.sk.cavity_solid(t, key=key)
            self.cav[key] = sol
            self.info[f"cavity_{key}"] = info
            self.log(f"cavity {key}: fit max {info['fit_err_max_above_waterline']:.3f} mm, {time.time() - t0:.1f}s")
        return self.cav[key]

    # ---------------------------------------------------------------- shared cutters
    def usb_cutters(self):
        u = self.lay.usb
        # landing: everything beyond x_land inside |y| < LAND_HW (rounded plan corners)
        hw, r = P.USB_LAND_HW, P.USB_LAND_R
        sk = bd.Pos(u["x_land"] + 10.0, 0) * bd.RectangleRounded(20.0, 2 * hw, r)
        land = bd.extrude(Plane.XY.offset(-5) * sk, amount=40)
        c, fc = P.USB_CLEAR, P.USB_FLOOR_CLEAR
        x_open = u["x_face"] - P.USB_OPEN_DEPTH
        # the plug's way in: full clearance all round
        opening = _stadium_yz(P.USB_W + 2 * c, P.USB_H + 2 * c, x_open, 75.0, u["z_c"])
        # behind it the body pocket keeps the side/top clearance but rests the shell on the sole
        x_cut = u["x_face"] - P.USB_PCB_NOTCH[0]          # the shell hangs below the board only here
        body = _stadium_yz(P.USB_W + 2 * c, P.USB_H + c + fc, x_cut - 0.3, x_open + 0.01,
                           u["z_c"] + (c - fc) / 2)
        return land, opening + body

    # ---------------------------------------------------------------- top shell
    def top_shell(self):
        zp = self.zp
        t0 = time.time()
        outer_top = self.sk.solid.split(Plane.XY.offset(zp), keep=Keep.TOP)
        shell = _check(outer_top - self.cavity("wall"), "shell")
        # magnet bosses: columns from just above the PCB that sink 0.5 mm into the wall.  They
        # are clipped by the 1.3 mm offset surface (not the inner surface itself) so the fuse
        # never sees two coincident B-spline faces -- OCC fuses of coincident faces were
        # unreliable here (mirror-image bosses added different volumes).
        dock = self.cavity(round(P.WALL - 0.5, 3))
        for m in self.lay.magnets:
            z0 = zp + P.PCB_T + P.BOSS_PCB_GAP
            col = Pos(m["x"], m["y"], z0) * bd.Cylinder(P.MAG_D / 2 + P.MAG_BOSS_WALL, 40, align=C3)
            shell = shell.fuse(col & dock)
        shell = _check(shell.clean(), "shell+bosses")
        for m in self.lay.magnets:
            z0 = zp + P.PCB_T + P.BOSS_PCB_GAP
            z_mag = zp + m["proud"] + P.MAG_GAP
            cb = Pos(m["x"], m["y"], z0 - 0.05) * bd.Cylinder((P.MAG_D + P.MAG_DOWEL_CLEAR) / 2, z_mag - z0 + 0.05, align=C3)
            pk = Pos(m["x"], m["y"], z_mag - 0.01) * bd.Cylinder((P.MAG_D + P.MAG_POCKET_CLEAR) / 2, m["top_h"] + 0.06, align=C3)
            shell = shell - cb - pk
        shell = _check(shell, "shell-magnet pockets")
        # seam slot: vertical prism through the wall down to 0.7 mm
        slot = bd.extrude(_poly_face(self.lay.slot_2d, zp), amount=30, dir=(0, 0, 1))
        shell = _check(shell - (slot & self.cavity(P.SEAM_WALL)), "shell-seam")
        # USB-C landing and opening
        land, tunnel = self.usb_cutters()
        shell = _check(shell - land - tunnel, "shell-usb")
        self.log(f"top shell {time.time() - t0:.1f}s, volume {shell.volume / 1000:.2f} cm3")
        return shell

    # ---------------------------------------------------------------- sole
    def sole(self):
        zp = self.zp
        t0 = time.time()
        sole = self.sk.solid.split(Plane.XY.offset(zp), keep=Keep.BOTTOM)
        # LED light channels: through, the body + clearance radially, the land + 0.15 tangentially
        pt = P.LED_LAND[0] + 2 * P.LED_POCKET_LAND
        pr = P.LED_PKG[1] + 2 * P.LED_POCKET_CLEAR
        for led in self.lay.leds:
            pk = Pos(led["x"], led["y"], -3.0) * Rot(0, 0, led["angle"]) * bd.Box(pr, pt, zp + 3.01, align=C3)
            sole = sole - pk
        sole = _check(sole, "sole-leds")
        # NTC: blind pocket over its land, lying radially; the floor left is the sensor window
        n = self.lay.ntc
        ntc_d = P.NTC_PKG[2] + 0.15
        sole = sole - Pos(n["x"], n["y"], zp - ntc_d) * Rot(0, 0, n["angle"]) * bd.Box(
            P.NTC_LAND[0] + 0.3, P.NTC_LAND[1] + 0.3, ntc_d + 0.01, align=C3)
        for m in self.lay.magnets:
            depth = m["sole_h"] - m["proud"] + 0.05
            if depth > 0.01:
                sole = sole - Pos(m["x"], m["y"], zp - depth) * bd.Cylinder((P.MAG_D + P.MAG_POCKET_CLEAR) / 2, depth + 0.01, align=C3)
        sole = _check(sole, "sole-magnets")
        # locating pins: a shallow pocket under each soldered, flush-cut pin
        dia, dep = P.PIN_SOLE_RELIEF
        for (x, y) in self.lay.mask_pins + self.lay.bridge_pins:
            sole = sole - Pos(x, y, zp - dep) * bd.Cylinder(dia / 2, dep + 0.01, align=C3)
        sole = _check(sole, "sole-pins")
        land, tunnel = self.usb_cutters()
        sole = _check(sole - land - tunnel, "sole-usb")
        self.log(f"sole {time.time() - t0:.1f}s, volume {sole.volume / 1000:.2f} cm3")
        return sole

    # ---------------------------------------------------------------- seam mask
    def _pin_holes(self, body, pins, z_bottom):
        """Blind slip-fit holes for the header-pin posts, with a shallow counterbore over the
        top pad's solder meniscus."""
        rd, rdep = P.PIN_FILLET_RELIEF
        for (x, y) in pins:
            body = body - Pos(x, y, z_bottom - 0.01) * bd.Cylinder(P.PIN_HOLE_PART / 2, P.PIN_HOLE_DEPTH + 0.01, align=C3)
            body = body - Pos(x, y, z_bottom - 0.01) * bd.Cylinder(rd / 2, rdep + 0.01, align=C3)
        return body

    def seam_mask(self):
        zp = self.zp
        z0 = zp + P.PCB_T
        body = bd.extrude(_poly_face(self.lay.mask_2d, z0), amount=20, dir=(0, 0, 1))
        body = _check(body & self.cavity(round(P.WALL + P.MASK_GAP, 3)), "mask")
        for ear in self.lay.mask_ears_2d:
            e = bd.extrude(_poly_face(ear, z0), amount=P.MASK_EAR[2], dir=(0, 0, 1))
            body = body + (e & self.cavity(round(P.WALL + P.MASK_GAP, 3)))
        body = _check(body.clean(), "mask+ears")
        body = self._pin_holes(body, self.lay.mask_pins, z0)
        return _check(body, "mask-pin holes")

    # ---------------------------------------------------------------- button bridge
    def bridge_geometry(self):
        zp = self.zp
        bx = self.lay.bridge_x
        z_batt_top = zp + P.PCB_T + P.BATT_FOAM + P.BATT_T
        z_deck0 = z_batt_top + P.BATT_TOP_CLEAR
        z_deck1 = z_deck0 + 2.5
        # membrane underside on the button axis: outer skin minus the thin wall, along the normal
        # membrane underside = skin offset inward by the thin wall; the actuator (3.5 mm disc)
        # must clear its LOWEST point over the disc (the dish floor is tilted ~4 deg)
        S, N = self.sk.outer(np.linspace(0, 1, 1344, endpoint=False), np.linspace(0.85, 1.0, 400))
        U = S - P.MEMBRANE_WALL * N
        d = np.hypot(U[..., 0] - BUTTON_XY[0], U[..., 1] - BUTTON_XY[1])
        disc = d <= 1.75 + 0.3
        under_min = float(U[..., 2][disc].min())
        i = np.unravel_index(np.argmin(d), d.shape)
        z_ped = under_min - P.SWITCH_GAP - P.SWITCH_H
        return dict(x=bx, z_deck0=z_deck0, z_deck1=z_deck1, z_ped=z_ped,
                    membrane_underside_z_centre=float(U[i][2]), membrane_underside_z_min=under_min,
                    skin_z=float(S[i][2]))

    def bridge(self):
        zp = self.zp
        g = self.bridge_geometry()
        bx = g["x"]
        z_pcb = zp + P.PCB_T
        ly = P.BRIDGE_LEG_Y
        lx, lw = P.BRIDGE_LEG
        parts = []
        for s in (1, -1):
            parts.append(Pos(bx, s * ly, z_pcb) * bd.Box(lx, lw, g["z_deck1"] - z_pcb, align=C3))
        y_half = ly + lw / 2
        parts.append(Pos(bx, 0, g["z_deck0"]) * bd.Box(P.BRIDGE_X_W, 2 * y_half, g["z_deck1"] - g["z_deck0"], align=C3))
        parts.append(Pos(bx, 0, g["z_deck1"] - 0.1) * bd.Box(P.BRIDGE_X_W, 9.0, g["z_ped"] - g["z_deck1"] + 0.1, align=C3))
        body = parts[0]
        for p_ in parts[1:]:
            body = body + p_
        body = _check(body & self.cavity(round(P.WALL + P.BRIDGE_GAP, 3)), "bridge clip")
        # switch seat: shallow locating pocket + four THT leg holes (6.5 x 4.5 mm pitch)
        sw, sh = P.SWITCH_BODY[0] + 0.3, P.SWITCH_BODY[1] + 0.3
        body = body - Pos(bx, 0, g["z_ped"] - 0.6) * bd.Box(sw, sh, 0.61, align=C3)
        for dx in (-3.25, 3.25):
            for dy in (-2.25, 2.25):
                body = body - Pos(bx + dx, dy, g["z_deck0"] - 0.1) * bd.Cylinder(0.6, 20, align=C3)
        body = self._pin_holes(body, self.lay.bridge_pins, z_pcb)
        self.info["bridge"] = g
        return _check(body, "bridge")

    # ---------------------------------------------------------------- stand-ins
    def pcb(self):
        poly = self.lay.pcb
        polys = getattr(poly, "geoms", [poly])
        out = None
        for pg in polys:
            f = bd.Face(bd.Wire.make_polygon([bd.Vector(x, y, self.zp) for x, y in list(pg.exterior.coords)[:-1]], close=True))
            for ring in pg.interiors:
                h = bd.Face(bd.Wire.make_polygon([bd.Vector(x, y, self.zp) for x, y in list(ring.coords)[:-1]], close=True))
                f = f - h
            sol = bd.extrude(f, amount=P.PCB_T, dir=(0, 0, 1))
            out = sol if out is None else out + sol
        return out

    def stand_ins(self):
        zp = self.zp
        d = {}
        d["pcb"] = self.pcb()
        z0 = zp + P.PCB_T + P.BATT_FOAM
        d["battery"] = Pos(P.BATT_X0 + P.BATT_W / 2, 0, z0) * bd.Box(P.BATT_W, P.BATT_L, P.BATT_T, align=C3)
        mags = None
        for m in self.lay.magnets:
            ms = Pos(m["x"], m["y"], zp + m["proud"] - m["sole_h"]) * bd.Cylinder(P.MAG_D / 2, m["sole_h"], align=C3)
            mt = Pos(m["x"], m["y"], zp + m["proud"] + P.MAG_GAP) * bd.Cylinder(P.MAG_D / 2, m["top_h"], align=C3)
            mags = (ms + mt) if mags is None else mags + ms + mt
        d["magnets"] = mags
        leds = None
        wt, wr = P.LED_PKG
        for led in self.lay.leds:
            # 1206 dome LED: body block plus the 1.6 mm dome, at the bank's maximum height
            h, hb = led["h"], 0.8
            b = Pos(led["x"], led["y"], zp - hb) * Rot(0, 0, led["angle"]) * bd.Box(wr, wt, hb, align=C3)
            b = b + Pos(led["x"], led["y"], zp - h) * bd.Cylinder(0.8, h - hb + 0.01, align=C3)
            leds = b if leds is None else leds + b
        d["leds"] = leds
        n = self.lay.ntc
        d["ntc"] = Pos(n["x"], n["y"], zp - P.NTC_PKG[2]) * Rot(0, 0, n["angle"]) * bd.Box(P.NTC_PKG[0], P.NTC_PKG[1], P.NTC_PKG[2], align=C3)
        pins = None
        for (x, y) in self.lay.mask_pins + self.lay.bridge_pins:
            pn = Pos(x, y, zp) * Rot(0, 0, 45) * bd.Box(P.PIN_SQ, P.PIN_SQ, P.PCB_T + P.PIN_ABOVE, align=C3)
            pins = pn if pins is None else pins + pn
        d["pins"] = pins
        g = self.bridge_geometry()
        sw = Pos(g["x"], 0, g["z_ped"]) * bd.Box(*P.SWITCH_BODY, align=C3)
        sw = sw + Pos(g["x"], 0, g["z_ped"] + P.SWITCH_BODY[2]) * bd.Cylinder(1.75, P.SWITCH_H - P.SWITCH_BODY[2], align=C3)
        d["switch"] = sw
        u = self.lay.usb
        x_notch = u["x_face"] - P.USB_PCB_NOTCH[0]
        front = _stadium_yz(P.USB_W, P.USB_H, x_notch + 0.05, u["x_face"], u["z_c"])
        z_pcb_top = zp + P.PCB_T
        rear = Pos(0.5 * (u["x_back"] + x_notch), 0, z_pcb_top) * bd.Box(x_notch - u["x_back"], P.USB_W - 0.6, u["z_top"] - z_pcb_top, align=C3)
        d["usb"] = front + rear
        sl = None
        for s_ in self.lay.seam_leds:
            b = Pos(s_["x"], s_["y"], zp + P.PCB_T) * Rot(0, 0, s_["angle"]) * bd.Box(0.5, 1.0, 0.4, align=C3)
            sl = b if sl is None else sl + b
        d["seam_leds"] = sl
        return d

    def build_all(self):
        out = dict(top_shell=self.top_shell(), sole=self.sole(), seam_mask=self.seam_mask(), bridge=self.bridge())
        out.update(self.stand_ins())
        return out


if __name__ == "__main__":
    t = time.time()
    pa = Parts()
    parts = pa.build_all()
    for k, v in parts.items():
        print(f"{k:10s} valid={v.is_valid}  volume={v.volume / 1000:7.3f} cm3")
    print("total", round(time.time() - t, 1), "s")
