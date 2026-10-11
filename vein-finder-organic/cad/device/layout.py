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
        self.batt_cut = box(x0 - c, -y1 - c, x1 + c, y1 + c).buffer(0.6, join_style=1).buffer(-0.6, join_style=1)
        self.batt_z = (self.zp + P.BATT_FOAM, self.zp + P.BATT_FOAM + P.BATT_T)

    def _leds(self):
        """Ring radius from the board's inner edge behind the window; LEDs spread evenly
        (mirror-symmetric, alternating banks) over the widest angle whose pads still fit."""
        env = self.pcb_env
        wt, wr = P.LED_PKG
        inner = []
        for th in np.radians(np.arange(-110, 111, 2.0)):
            ray = LineString([(0, 0), (30 * math.cos(th), 30 * math.sin(th))])
            hit = ray.intersection(env)
            if hit.is_empty:
                continue
            inner.append(min(Point(0, 0).distance(g) for g in getattr(hit, "geoms", [hit])))
        self.pcb_inner_r = float(np.max(inner))
        self.led_r = self.pcb_inner_r + P.LED_EDGE_MARGIN + wr / 2 + P.LED_PAD_MARGIN + 0.02
        pad = (wt + 2 * P.LED_PAD_MARGIN, wr + 2 * P.LED_PAD_MARGIN)
        shrunk = env.buffer(-P.LED_EDGE_MARGIN)

        def fits(a):
            cx, cy = self.led_r * math.cos(math.radians(a)), self.led_r * math.sin(math.radians(a))
            return shrunk.contains(_rect(cx, cy, pad[0], pad[1], a))

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
                leds.append(dict(angle=aa, x=cx, y=cy, bank="660" if k % 2 == 0 else "620", fits=bool(fits(aa))))
        self.leds = leds

    def _ntc(self):
        a = 0.0
        r = self.led_r
        self.ntc = dict(x=r, y=0.0, angle=a)

    def _magnets(self):
        mags = []
        for (x, y) in P.MAGNETS:
            boss_r = P.MAG_D / 2 + P.MAG_BOSS_WALL
            hole = Point(x, y).buffer(P.MAG_PCB_HOLE / 2)
            mags.append(dict(x=x, y=y, hole_in_pcb=bool(self.pcb_env.buffer(-0.3).contains(hole)),
                             pcb_ring_min=float(self.pcb_env.exterior.distance(hole)),
                             clear_of_battery=float(hole.distance(self.batt_cut)),
                             boss_room_above_pcb=float(np.nanmin(self.ceiling(
                                 x + boss_r * np.cos(np.linspace(0, 6.28, 16)),
                                 y + boss_r * np.sin(np.linspace(0, 6.28, 16))))) - (self.zp + P.PCB_T)))
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
        pin_a = a1 + cap_deg / 2
        self.mask_pins = [(r_mid * math.cos(math.radians(s * pin_a)), r_mid * math.sin(math.radians(s * pin_a)))
                          for s in (1, -1)]
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
        self.usb = dict(x_face=x_face, x_back=x_face - P.USB_L, z_c=zc,
                        z_bottom=zc - P.USB_H / 2, z_top=zc + P.USB_H / 2,
                        x_land=x_face + P.USB_LAND_DX)
        self.usb_notch = box(x_face - P.USB_PCB_NOTCH[0], -P.USB_PCB_NOTCH[1], 70.0, P.USB_PCB_NOTCH[1])

    def _board(self):
        b = self.pcb_env.difference(self.batt_cut).difference(self.usb_notch)
        b = b.buffer(-P.PCB_CORNER_R, join_style=1).buffer(P.PCB_CORNER_R, join_style=1)
        holes = [Point(m["x"], m["y"]).buffer(P.MAG_PCB_HOLE / 2) for m in self.magnets]
        holes += [Point(*p).buffer(P.PIN_HOLE_PCB / 2) for p in self.mask_pins]
        holes += [Point(*p).buffer(P.PIN_HOLE_PCB / 2) for p in self.bridge_pins]
        self.pcb_holes = holes
        self.pcb = b.difference(unary_union(holes))

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
        solid_board = self.pcb_env.difference(self.batt_cut)
        rep["bridge_feet_on_pcb"] = [bool(solid_board.contains(f)) for f in self.bridge_feet]
        rep["led_a_max_deg"] = round(self.led_a_max, 1)
        rep["led_pitch_deg"] = round(self.led_step, 2)
        rep["usb"] = {k: round(v, 2) for k, v in self.usb.items()}
        rep["usb_clear_of_battery_mm"] = round(self.usb["x_back"] - (P.BATT_X0 + P.BATT_W) - P.BATT_CLEAR, 2)
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
            usb=self.usb, pcb_holes=[list(h.centroid.coords)[0] for h in self.pcb_holes], battery=dict(x0=P.BATT_X0, x1=P.BATT_X0 + P.BATT_W, y=P.BATT_L / 2,
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
