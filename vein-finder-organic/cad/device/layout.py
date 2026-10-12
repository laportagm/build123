"""
Internal layout derived from the real cavity (gate 2).

Everything that has to fit inside the hollow top shell is placed here from the
measured cavity sections, not from guesses: the PCB outline, the LED ring, the NTC,
magnet holes, the seam mask and the button bridge footprints, the USB-C tongue and the
battery cut-out.  `Layout.check()` lists every clearance; `export()` writes
build/device/layout.json and the KiCad-ready Edge.Cuts DXF.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from shapely import affinity
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

import params as P
from skin import BUTTON_XY, Skin

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "build" / "device"


def _rect(cx, cy, w_t, w_r, ang_deg):
    """Rectangle centred at (cx, cy): w_t along the tangent of angle ang, w_r along the radius."""
    r = box(-w_r / 2, -w_t / 2, w_r / 2, w_t / 2)
    return affinity.translate(affinity.rotate(r, ang_deg, origin=(0, 0)), cx, cy)


def _sector(r0, r1, a0_deg, a1_deg, n=120):
    a = np.radians(np.linspace(a0_deg, a1_deg, n))
    outer = np.c_[r1 * np.cos(a), r1 * np.sin(a)]
    inner = np.c_[r0 * np.cos(a[::-1]), r0 * np.sin(a[::-1])]
    return Polygon(np.vstack([outer, inner]))


class Layout:
    def __init__(self, skin: Skin | None = None):
        self.sk = skin or Skin(verbose=False)
        self.zp = self.sk.z_part
        us, vs, Pn, _ = self.sk.cavity_samples(P.WALL, self.zp - 1.2)
        self.net = Pn                     # (rows, n_u, 3) inner wall + ceiling samples
        self.items = {}
        self._pcb()
        self._battery()
        self._leds()
        self._ntc()
        self._magnets()
        self._seam()
        self._bridge()
        self._usb()
        self._board()

    # ---------------------------------------------------------------- cavity sections
    def section(self, z):
        """Cavity cross-section at height z as a polygon (first crossing of each meridian)."""
        Pn = self.net
        z_all = Pn[..., 2]
        pts = []
        for j in range(Pn.shape[1]):
            zc = z_all[:, j]
            k = np.where((zc[:-1] < z) & (zc[1:] >= z))[0]
            if len(k) == 0:
                continue
            k = k[0]
            f = (z - zc[k]) / (zc[k + 1] - zc[k])
            pts.append(Pn[k, j, :2] + f * (Pn[k + 1, j, :2] - Pn[k, j, :2]))
        poly = Polygon(np.asarray(pts)).buffer(0)
        return poly

    def ceiling(self, x, y):
        """Inner-surface height above (x, y): highest net point within 0.35 mm in plan."""
        from scipy.spatial import cKDTree
        if not hasattr(self, "_ck"):
            pts = self.net[2:].reshape(-1, 3)
            up = pts[pts[:, 2] > self.zp + 0.05]
            self._ck = (cKDTree(up[:, :2]), up[:, 2])
        tree, z = self._ck
        idx = tree.query_ball_point(np.c_[np.atleast_1d(x), np.atleast_1d(y)], 0.35)
        return np.array([z[i].max() if len(i) else np.nan for i in idx])

    def skin_floor(self, x, y):
        """Height of the sole's skin face below (x, y), from the downward-facing skin."""
        from scipy.interpolate import LinearNDInterpolator
        if not hasattr(self, "_floor"):
            S, N = self.sk.outer(np.linspace(0, 1, 1344, endpoint=False), np.linspace(0.0, 0.6, 900))
            m = (N[..., 2] < -0.05) & (S[..., 2] < self.zp)
            self._floor = LinearNDInterpolator(S[m][:, :2], S[m][:, 2])
        return self._floor(np.atleast_1d(x), np.atleast_1d(y))

    def under_part(self, cx, cy, w_t, w_r, ang, n=7):
        """Lowest sole thickness (waterline to skin face) under a w_t x w_r footprint."""
        a = math.radians(ang)
        er, et = np.array([math.cos(a), math.sin(a)]), np.array([-math.sin(a), math.cos(a)])
        s, t = np.meshgrid(np.linspace(-0.5, 0.5, n), np.linspace(-0.5, 0.5, n))
        pts = np.array([cx, cy]) + (s.ravel()[:, None] * w_r) * er + (t.ravel()[:, None] * w_t) * et
        return float(np.nanmin(self.zp - self.skin_floor(pts[:, 0], pts[:, 1])))

    def under_disc(self, cx, cy, r, n=24):
        """Lowest sole thickness under a disc of radius r (centre and two rings)."""
        th = np.linspace(0, 2 * np.pi, n, endpoint=False)
        xs = np.r_[cx, cx + 0.5 * r * np.cos(th), cx + r * np.cos(th)]
        ys = np.r_[cy, cy + 0.5 * r * np.sin(th), cy + r * np.sin(th)]
        return float(np.nanmin(self.zp - self.skin_floor(xs, ys)))

    # ---------------------------------------------------------------- items
    def _pcb(self):
        secs = [self.section(self.zp + dz) for dz in P.PCB_LEVELS]
        env = secs[0]
        for s in secs[1:]:
            env = env.intersection(s)
        self.cavity_at_pcb = env
        self.pcb_env = env.buffer(-P.PCB_CLEAR, join_style=1)

    def _battery(self):
        x0, x1 = P.BATT_X0, P.BATT_X0 + P.BATT_W
        y1 = P.BATT_L / 2
        c = P.BATT_CLEAR
        self.batt_rect = box(x0, -y1, x1, y1)
        # component keep-out on the board top (the cell sits on the board on foam tape)
        self.batt_cut = box(x0 - c, -y1 - c, x1 + c, y1 + c).buffer(0.6, join_style=1).buffer(-0.6, join_style=1)
        z0 = self.zp + P.PCB_T + P.BATT_FOAM
        self.batt_z = (z0, z0 + P.BATT_T)

    def _inner_r(self, th_deg):
        """Distance from the window centre to the board's inner (window) edge along angle th."""
        th = math.radians(th_deg)
        ray = LineString([(0, 0), (30 * math.cos(th), 30 * math.sin(th))])
        hit = ray.intersection(self.pcb_env)
        if hit.is_empty:
            return float("nan")
        return min(Point(0, 0).distance(g) for g in getattr(hit, "geoms", [hit]))

    def _leds(self):
        """Ring radius from the board's inner edge behind the window; LEDs spread evenly
        (mirror-symmetric, alternating banks) over the widest angle whose land patterns
        still fit on the board."""
        env = self.pcb_env
        lt, lr = P.LED_LAND
        self.pcb_inner_r = float(np.nanmax([self._inner_r(a) for a in np.arange(-110, 111, 2.0)]))
        self.led_r = self.pcb_inner_r + P.LED_EDGE_MARGIN + lr / 2 + 0.02
        shrunk = env.buffer(-P.LED_EDGE_MARGIN)

        def fits(a):
            cx, cy = self.led_r * math.cos(math.radians(a)), self.led_r * math.sin(math.radians(a))
            return shrunk.contains(_rect(cx, cy, lt, lr, a))

        a_max = 90.0
        while a_max < 179 and fits(a_max + 0.5):
            a_max += 0.5
        self.led_a_max = a_max
        n_half = P.LED_COUNT // 2
        step = 2 * a_max / (2 * n_half - 1)
        self.led_step = step
        leds = []
        for k in range(n_half):
            a = (k + 0.5) * step
            for sgn in (1, -1):
                aa = sgn * a
                cx, cy = self.led_r * math.cos(math.radians(aa)), self.led_r * math.sin(math.radians(aa))
                bank = P.LED_BANK_ORDER[k % 2]
                leds.append(dict(angle=aa, x=cx, y=cy, bank=bank, h=P.LED_H[bank], fits=bool(fits(aa))))
        self.leds = leds
        self.led_lands = [_rect(l["x"], l["y"], lt, lr, l["angle"]) for l in leds]

    def _ntc(self):
        """0603 NTC on the underside at theta = 0, lying tangentially just outside the LED ring
        (between and behind the two first LEDs): both pads face open board, so both can be
        routed.  (Lying radially inside the ring, its inner pad was boxed in by the window
        edge and the neighbouring LED lands.)"""
        lt, lr = P.NTC_LAND
        r = self.led_r + P.LED_LAND[1] / 2 + 0.2 + lr / 2 + 0.45     # + 0.45: courtyards clear the LEDs
        self.ntc = dict(x=r, y=0.0, angle=90.0)          # angle: direction of the pad axis
        self.ntc_land = _rect(r, 0.0, lt, lr, 0.0)

    def _magnets(self):
        mags = []
        for spec in P.MAGNETS:
            x, y = spec["x"], spec["y"]
            boss_r = P.MAG_D / 2 + P.MAG_BOSS_WALL
            hole = Point(x, y).buffer(P.MAG_PCB_HOLE / 2)
            m = dict(spec)
            m.update(hole_in_pcb=bool(self.pcb_env.buffer(-0.3).contains(hole)),
                     pcb_ring_min=float(self.pcb_env.exterior.distance(hole)),
                     clear_of_battery=float(hole.distance(self.batt_cut)),
                     boss_room_above_pcb=float(np.nanmin(self.ceiling(
                         x + boss_r * np.cos(np.linspace(0, 6.28, 16)),
                         y + boss_r * np.sin(np.linspace(0, 6.28, 16))))) - (self.zp + P.PCB_T),
                     sole=self.under_disc(x, y, (P.MAG_D + P.MAG_POCKET_CLEAR) / 2))
            m["sole_floor"] = m["sole"] - (m["sole_h"] - m["proud"] + 0.05)
            m["top_cover"] = m["boss_room_above_pcb"] - (m["proud"] - P.PCB_T + P.MAG_GAP + m["top_h"] + 0.06)
            mags.append(m)
        self.magnets = mags

    def _seam(self):
        """Seam mask = a closed black frame around a 1 mm channel under the slot; its end
        caps are wide enough to carry the locating-pin holes."""
        r_mid = P.SEAM_R
        h = P.MASK_CHANNEL / 2
        a0, a1 = -P.SEAM_HALF_DEG - P.MASK_END_DEG, P.SEAM_HALF_DEG + P.MASK_END_DEG
        cap_deg = math.degrees(P.MASK_CAP_W / r_mid)
        frame = _sector(r_mid - h - P.MASK_T, r_mid + h + P.MASK_T, a0 - cap_deg, a1 + cap_deg)
        self.mask_channel_2d = _sector(r_mid - h, r_mid + h, a0, a1)
        self.mask_2d = frame.difference(self.mask_channel_2d)
        # the locating pins sit in ears outside the caps, clear of the underside LED lands
        pin_a = a1 + cap_deg / 2
        r_out = r_mid + h + P.MASK_T
        ew, el, _ = P.MASK_EAR
        r_pin = r_out + el / 2
        ears = []
        for s_ in (1, -1):
            ears.append(_rect(r_pin * math.cos(math.radians(s_ * pin_a)), r_pin * math.sin(math.radians(s_ * pin_a)),
                              ew, el + 0.6, s_ * pin_a))
        self.mask_ears_2d = [e.difference(_sector(0, r_out - 0.3, -180, 180, 360)) for e in ears]
        self.mask_pins = [(r_pin * math.cos(math.radians(s_ * pin_a)), r_pin * math.sin(math.radians(s_ * pin_a)))
                          for s_ in (1, -1)]
        self.seam_leds = [dict(x=r_mid * math.cos(math.radians(a)), y=r_mid * math.sin(math.radians(a)), angle=a)
                          for a in np.linspace(-P.SEAM_HALF_DEG * 0.8, P.SEAM_HALF_DEG * 0.8, P.SEAM_LED_COUNT)]
        self.slot_2d = _sector(P.SEAM_R - P.SEAM_SLOT_W / 2, P.SEAM_R + P.SEAM_SLOT_W / 2,
                               -P.SEAM_HALF_DEG, P.SEAM_HALF_DEG).buffer(P.SEAM_SLOT_W / 2 - 1e-3)

    def _bridge(self):
        x = BUTTON_XY[0]
        feet = []
        for s in (1, -1):
            fp = box(x - P.BRIDGE_LEG[0] / 2, s * P.BRIDGE_LEG_Y - P.BRIDGE_LEG[1] / 2,
                     x + P.BRIDGE_LEG[0] / 2, s * P.BRIDGE_LEG_Y + P.BRIDGE_LEG[1] / 2)
            feet.append(fp)
        self.bridge_x = x
        self.bridge_feet = feet
        self.bridge_pins = [(x - 2.8, s * P.BRIDGE_LEG_Y) for s in (1, -1)] + [(x + 2.8, s * P.BRIDGE_LEG_Y) for s in (1, -1)]

    def _usb(self):
        x_face = P.USB_X_FACE
        zc = self.zp + P.USB_ZC
        self.usb = dict(x_face=x_face, x_back=x_face - P.USB_L, x_tails=x_face - P.USB_TAILS,
                        x_cut=x_face - P.USB_PCB_NOTCH[0], board_edge=x_face - P.USB_FACE_PROUD, z_c=zc,
                        z_bottom=zc - P.USB_H / 2, z_top=zc + P.USB_H / 2,
                        x_land=x_face + P.USB_LAND_DX)
        self.usb_notch = box(x_face - P.USB_PCB_NOTCH[0], -P.USB_PCB_NOTCH[1], 70.0, P.USB_PCB_NOTCH[1])

    def _board(self):
        b = self.pcb_env.difference(self.usb_notch)
        b = b.buffer(-P.PCB_CORNER_R, join_style=1).buffer(P.PCB_CORNER_R, join_style=1)
        mag_holes = [Point(m["x"], m["y"]).buffer(P.MAG_PCB_HOLE / 2, 64) for m in self.magnets]
        pin_holes = [Point(*p).buffer(P.PIN_HOLE_PCB / 2) for p in self.mask_pins + self.bridge_pins]
        self.pcb_holes = mag_holes + pin_holes
        # Edge.Cuts = outline with the magnet holes (the tail ones break the edge);
        # the locating pins are soldered into plated 1.0 mm holes (pad 1.7)
        self.board_outline = b.difference(unary_union(mag_holes))
        self.drills = [dict(x=float(p[0]), y=float(p[1]), d=P.PIN_HOLE_PCB, pad=P.PIN_PAD_PCB, plated=True)
                       for p in self.mask_pins + self.bridge_pins]
        self.pcb = b.difference(unary_union(self.pcb_holes))

    # ---------------------------------------------------------------- report
    def check(self):
        env = self.pcb_env
        rep = {}
        rep["pcb_area_mm2"] = round(self.pcb.area, 1)
        rep["pcb_bbox"] = [round(v, 2) for v in self.pcb.bounds]
        rep["pcb_inner_r_at_window"] = round(self.pcb_inner_r, 2)
        rep["led_ring_r"] = round(self.led_r, 2)
        rep["leds_fit"] = all(l["fits"] for l in self.leds)
        rep["led_angles"] = sorted(round(l["angle"], 1) for l in self.leds)
        rep["leds_not_fitting"] = [round(l["angle"], 1) for l in self.leds if not l["fits"]]
        # LED heights against the sole: the dome must not stand proud of the skin face
        wt, wr = P.LED_PKG
        prot = []
        for l in self.leds:
            th = self.under_part(l["x"], l["y"], wt + 2 * P.LED_TOL, wr + 2 * P.LED_TOL, l["angle"])
            prot.append(dict(angle=round(l["angle"], 1), bank=l["bank"], sole=round(th, 2),
                             recess=round(th - l["h"], 2)))
        rep["led_recess"] = prot
        rep["led_recess_min"] = min(p_["recess"] for p_ in prot)
        lands = self.led_lands
        rep["led_land_gap_min"] = round(min(a.distance(b) for i, a in enumerate(lands) for b in lands[i + 1:]), 2)
        rep["ntc_land_fits"] = bool(env.buffer(-P.LED_EDGE_MARGIN).contains(self.ntc_land))
        rep["ntc_to_led_land"] = round(min(self.ntc_land.distance(l) for l in lands), 2)
        rep["ntc_sole"] = round(self.under_part(self.ntc["x"], self.ntc["y"], P.NTC_LAND[0], P.NTC_LAND[1], 0.0), 2)
        rep["ntc_floor"] = round(rep["ntc_sole"] - P.NTC_PKG[2] - 0.15, 2)
        pads = [Point(*q).buffer(P.PIN_PAD_PCB / 2) for q in self.mask_pins + self.bridge_pins]
        rep["pin_pad_to_led_land"] = round(min(a.distance(b) for a in pads for b in lands + [self.ntc_land]), 2)
        rep["pin_pads_on_board"] = [bool(env.buffer(-0.3).contains(q) and not q.intersects(self.batt_cut)) for q in pads]
        rep["mask_ears_on_board"] = [bool(env.contains(e) and not e.intersects(self.batt_cut)) for e in self.mask_ears_2d]
        # battery: cut-out must lie inside the cavity with clearance at the cell's height range
        z0, z1 = self.batt_z
        cav = self.section(z0).intersection(self.section(z1))
        rep["battery_inside_cavity"] = bool(cav.buffer(-P.BATT_CLEAR).contains(self.batt_rect))
        xs, ys = np.meshgrid(np.linspace(P.BATT_X0, P.BATT_X0 + P.BATT_W, 31), np.linspace(-P.BATT_L / 2, P.BATT_L / 2, 43))
        c = self.ceiling(xs.ravel(), ys.ravel())
        rep["battery_top_clearance_min"] = round(float(np.nanmin(c) - z1), 2)
        rep["magnets"] = [{k: (round(v, 2) if isinstance(v, float) else v) for k, v in m.items()} for m in self.magnets]
        rep["mask_on_pcb"] = bool(env.contains(self.mask_2d))
        rep["mask_clear_of_battery"] = bool(not self.mask_2d.intersects(self.batt_cut))
        solid_board = self.pcb_env.difference(self.batt_cut)          # feet stay off the cell's keep-out
        rep["bridge_feet_on_pcb"] = [bool(solid_board.contains(f)) for f in self.bridge_feet]
        rep["led_a_max_deg"] = round(self.led_a_max, 1)
        rep["led_pitch_deg"] = round(self.led_step, 2)
        rep["usb"] = {k: round(v, 2) for k, v in self.usb.items()}
        legs = [box(self.usb["x_face"] - xb - pl / 2, s_ * yl - 0.55, self.usb["x_face"] - xb + pl / 2, s_ * yl + 0.55)
                for (xb, yl, sl, pl) in P.USB_LEGS for s_ in (1, -1)]
        rep["usb_leg_pads_on_board"] = [bool(env.buffer(-0.15).contains(l_)) for l_ in legs]
        rep["usb_clear_of_battery_mm"] = round(self.usb["x_tails"] - 0.3 - (P.BATT_X0 + P.BATT_W) - P.BATT_CLEAR, 2)
        rep["usb_clear_of_magnets_mm"] = round(min(
            box(self.usb["x_back"], -P.USB_W / 2, self.usb["x_face"], P.USB_W / 2).distance(Point(m["x"], m["y"]))
            - P.MAG_D / 2 for m in self.magnets), 2)
        return rep

    def export(self):
        OUT.mkdir(parents=True, exist_ok=True)
        data = dict(
            units="mm", frame="device (window centre origin, +x tail); PCB bottom face at z_part",
            z_part=self.zp, pcb_t=P.PCB_T,
            leds=self.leds, ntc=self.ntc, seam_leds=self.seam_leds,
            magnets=self.magnets, mask_pins=self.mask_pins, bridge_pins=self.bridge_pins,
            usb=self.usb, pcb_holes=[list(h.centroid.coords)[0] for h in self.pcb_holes],
            board_outline=[[list(map(list, r.coords)) for r in [g.exterior] + list(g.interiors)]
                           for g in getattr(self.board_outline, "geoms", [self.board_outline])],
            drills=self.drills, bridge_x=self.bridge_x,
            bridge_feet=[list(map(list, f.exterior.coords)) for f in self.bridge_feet],
            mask_outline=[[list(map(list, r.coords)) for r in [g.exterior] + list(g.interiors)]
                          for g in getattr(self.mask_2d, "geoms", [self.mask_2d])],
            mask_ears=[list(map(list, e.exterior.coords)) for e in self.mask_ears_2d],
            battery=dict(x0=P.BATT_X0, x1=P.BATT_X0 + P.BATT_W, y=P.BATT_L / 2,
                                       z=list(self.batt_z)),
            button=dict(x=BUTTON_XY[0], y=BUTTON_XY[1]), check=self.check())
        (OUT / "layout.json").write_text(json.dumps(data, indent=1, default=float))
        self.export_dxf(OUT / "pcb_edge_cuts.dxf")
        return data

    def export_dxf(self, path):
        import ezdxf
        doc = ezdxf.new("R2000")
        doc.units = ezdxf.units.MM
        msp = doc.modelspace()
        geoms = getattr(self.pcb, "geoms", [self.pcb])
        for g in geoms:
            for ring in [g.exterior] + list(g.interiors):
                pts = np.asarray(ring.coords)
                # KiCad frame: y down. Mirror y so the board reads from the top side.
                msp.add_lwpolyline([(float(x), float(-y)) for x, y in pts], close=True,
                                   dxfattribs={"layer": "Edge.Cuts"})
        doc.saveas(path)


if __name__ == "__main__":
    import time
    t = time.time()
    lay = Layout()
    print(json.dumps(lay.check(), indent=1, default=float))
    lay.export()
    print("exported", round(time.time() - t, 1), "s")
