"""
First-article reference dimensions for the print packet (print-packet.md), read from the
committed print meshes (docs/02-cad/3mf/*.3mf, written by cad/device/build.py in print
orientation, each sitting on z = 0) and from cad/device/params.py and cad/device/parts.py.

Read-only: it changes nothing in cad/.  Writes print_dims.json next to this file.

    python docs/08-prototype/print_dims.py

Personal prototype for bench evaluation - NOT a medical device.
"""
from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "cad" / "device"))
import params as P  # noqa: E402

MESHES = ROOT / "docs" / "02-cad" / "3mf"
PARTS = ("sole", "top_shell", "bridge", "seam_mask")


def mesh(path: Path):
    with zipfile.ZipFile(path) as z:
        name = next(n for n in z.namelist() if n.endswith(".model"))
        root = ET.fromstring(z.read(name))
    V, T = [], []
    for e in root.iter():
        tag = e.tag.split("}")[-1]
        if tag == "vertex":
            V.append((float(e.get("x")), float(e.get("y")), float(e.get("z"))))
        elif tag == "triangle":
            T.append((int(e.get("v1")), int(e.get("v2")), int(e.get("v3"))))
    return np.array(V), np.array(T)


def size(V):
    """L x W x H in print orientation.  Each mesh sits on z = 0 by construction (build.py
    export_3mf moves the exact solid's bounding box there); the tessellation leaves a few
    vertices up to 0.03 mm below it, which are not material, so the height is measured from 0."""
    return [round(float(np.ptp(V[:, 0])), 3), round(float(np.ptp(V[:, 1])), 3), round(float(V[:, 2].max()), 3)]


def ray_z(V, T, x, y):
    """Heights where a vertical line at (x, y) crosses the mesh surface (Moller-Trumbore)."""
    o, d = np.array([x, y, -1.0]), np.array([0.0, 0.0, 1.0])
    v0, v1, v2 = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
    e1, e2 = v1 - v0, v2 - v0
    p = np.cross(d, e2)
    det = (e1 * p).sum(1)
    ok = np.abs(det) > 1e-12
    inv = np.where(ok, 1 / np.where(ok, det, 1), 0)
    s = o - v0
    u = (s * p).sum(1) * inv
    q = np.cross(s, e1)
    v = (q * d).sum(1) * inv
    t = (e2 * q).sum(1) * inv
    hit = ok & (u >= -1e-9) & (v >= -1e-9) & (u + v <= 1 + 1e-9)
    return np.sort(t[hit]) - 1.0


def lip_profile(V, T):
    """USB-C lip of the sole (N19) on the centre line y = 0, near the landing face.  Upside
    down, the opening is a notch at the plate and the lip is the material over it, from the
    notch roof to the skin.  Returns the lip thickness at given distances in from the face."""
    x = V[:, 0].max() - 1.8
    face = None
    while x < V[:, 0].max():                       # walk to the last x with material at y = 0
        h = ray_z(V, T, x, 0.0)
        if len(h) < 2:
            break
        face = x
        x += 0.005
    out = {}
    for back in (0.0, 0.1, 0.2, 0.5, 1.0):
        h = ray_z(V, T, face - back, 0.0)
        out[f"{back:.1f}"] = round(float(h[1] - h[0]), 3)
    return out


def mask_vertical_room(V, T, gap):
    """The mask is clipped to MASK_GAP measured normal to the shell's inner surface
    (parts.seam_mask: cavity(WALL + MASK_GAP)).  On a top sloping at angle a, that leaves
    gap / cos(a) vertically; the smallest slope leaves the least room."""
    v0, v1, v2 = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
    n = np.cross(v1 - v0, v2 - v0)
    n /= np.linalg.norm(n, axis=1)[:, None] + 1e-15
    up_sloped = (n[:, 2] > 0.05) & (n[:, 2] < 0.95)
    a = np.degrees(np.arccos(n[up_sloped, 2]))
    a_min, a_max = float(a.min()), float(a.max())
    return round(a_min, 1), round(a_max, 1), round(gap / np.cos(np.radians(a_min)), 3)


def main():
    lay = json.loads((ROOT / "docs" / "02-cad" / "pcb" / "layout.json").read_text())
    checks = json.loads((ROOT / "docs" / "02-cad" / "checks.json").read_text())
    zp = lay["z_part"]
    meshes = {n: mesh(MESHES / f"{n}.3mf") for n in PARTS}
    out = {"source": "docs/02-cad/3mf/*.3mf (print orientation), cad/device/params.py, cad/device/parts.py, "
                     "docs/02-cad/pcb/layout.json, docs/02-cad/checks.json",
           "size_print_xyz_mm": {n: size(V) for n, (V, T) in meshes.items()}}

    horn, tail = P.MAGNETS[0], P.MAGNETS[2]
    f = {
        "magnet_pocket_d": round(P.MAG_D + P.MAG_POCKET_CLEAR, 3),
        "dowel_counterbore_d": round(P.MAG_D + P.MAG_DOWEL_CLEAR, 3),
        "magnet_d": P.MAG_D,
        "pcb_magnet_hole_d": P.MAG_PCB_HOLE,
        # parts.sole(): pocket depth sole_h - proud + 0.05, so a magnet seated dry on the floor
        # stands at proud - 0.05.  parts.top_shell(): top pocket from z_mag - 0.01, top_h + 0.06
        # tall (z_mag = proud + MAG_GAP), so a top magnet pressed to its ceiling has its face at
        # proud + MAG_GAP + 0.05.  The CAD's MAG_GAP assumes each magnet 0.05 off its pocket.
        "horn_sole_pocket_depth": round(horn["sole_h"] - horn["proud"] + 0.05, 3),
        "tail_sole_pocket_depth": round(tail["sole_h"] - tail["proud"] + 0.05, 3),
        "sole_magnet_top_dry": [round(horn["proud"] - 0.05, 3), round(tail["proud"] - 0.05, 3)],
        "sole_magnet_top_cad": [horn["proud"], tail["proud"]],
        "top_magnet_face_seated": [round(horn["proud"] + P.MAG_GAP + 0.05, 3), round(tail["proud"] + P.MAG_GAP + 0.05, 3)],
        "top_pocket_ceiling": [round(horn["proud"] + P.MAG_GAP + horn["top_h"] + 0.05, 3),
                               round(tail["proud"] + P.MAG_GAP + tail["top_h"] + 0.05, 3)],
        "magnet_gap_cad": P.MAG_GAP,
        "magnet_gap_both_seated": round(P.MAG_GAP + 0.10, 3),
        "magnet_centre_dist_horns_y": round(2 * abs(horn["y"]), 3),
        "magnet_centre_dist_tails_y": round(2 * abs(tail["y"]), 3),
        "magnet_centre_dist_horn_tail": round(float(np.hypot(tail["x"] - horn["x"], abs(horn["y"]) - abs(tail["y"]))), 3),
        # per magnet: the board hole's play less the pocket's own play; a pair may differ by twice that
        "magnet_centre_dist_tol": round(2 * ((P.MAG_PCB_HOLE - P.MAG_D) / 2 - P.MAG_POCKET_CLEAR / 2), 3),
        "led_channel_radial": round(P.LED_PKG[1] + 2 * P.LED_POCKET_CLEAR, 3),
        "led_channel_tangential": round(P.LED_LAND[0] + 2 * P.LED_POCKET_LAND, 3),
        "led_body_radial_max": round(P.LED_PKG[1] + P.LED_TOL, 3),
        "ntc_pocket": [round(P.NTC_LAND[0] + 0.3, 3), round(P.NTC_LAND[1] + 0.3, 3)],
        "ntc_pocket_depth": round(P.NTC_PKG[2] + 0.15, 3),
        "ntc_body_max": list(P.NTC_PKG),
        "ntc_window": checks["sole_floors"]["ntc (sensor window)"],
        "usb_opening": [round(P.USB_W + 2 * P.USB_CLEAR, 3), round(P.USB_H + 2 * P.USB_CLEAR, 3)],
        "usb_shell": [P.USB_W, P.USB_H],
        "usb_opening_below_waterline": round(zp - (lay["usb"]["z_c"] - (P.USB_H + 2 * P.USB_CLEAR) / 2), 3),
        "usb_centre_above_waterline": round(lay["usb"]["z_c"] - zp, 3),
        "usb_lip_checks_json": checks["sole_floors"]["usb opening lip"],
        "usb_lip_from_landing_face": lip_profile(*meshes["sole"]),
        "boss_underside_above_waterline": round(P.PCB_T + P.BOSS_PCB_GAP, 3),
        "pin_hole_part": P.PIN_HOLE_PART,
        "pin_post_diagonal": round(P.PIN_SQ * 2 ** 0.5, 3),
        "mask_channel": P.MASK_CHANNEL,
        "mask_fence": P.MASK_T,
        "mask_gap_to_shell": P.MASK_GAP,
        "mask_ear_height": P.MASK_EAR[2],
        "bridge_width_x": P.BRIDGE_X_W,
        "bridge_leg_y_span": round(2 * (P.BRIDGE_LEG_Y + P.BRIDGE_LEG[1] / 2), 3),
        "switch_seat": [round(P.SWITCH_BODY[0] + 0.3, 3), round(P.SWITCH_BODY[1] + 0.3, 3), 0.6],
        "switch_h": P.SWITCH_H,
        "switch_gap": P.SWITCH_GAP,
    }
    # the opening and the shell are stadiums (rounded ends along y) centred at z_c, above the
    # waterline: the sole holds only their lower segments, narrower than their full widths
    dz = zp - lay["usb"]["z_c"]
    f["usb_opening_width_at_waterline"] = stadium_width(P.USB_W + 2 * P.USB_CLEAR, P.USB_H + 2 * P.USB_CLEAR, dz)
    f["usb_shell_width_at_waterline"] = stadium_width(P.USB_W, P.USB_H, dz)
    # mask: vertical room above the highest point
    a_min, a_max, room = mask_vertical_room(*meshes["seam_mask"], P.MASK_GAP)
    f["mask_top_slope_deg"] = [a_min, a_max]
    f["mask_vertical_room"] = room
    # bridge heights above its feet (the board top), as parts.bridge_geometry() builds them;
    # the pedestal top is the print size along x (it prints on its +x face: device z -> print x)
    z_pcb = zp + P.PCB_T
    z_deck0 = z_pcb + P.BATT_FOAM + P.BATT_T + P.BATT_TOP_CLEAR
    f["bridge_deck_underside_above_feet"] = round(z_deck0 - z_pcb, 3)
    f["bridge_pedestal_top_above_feet"] = out["size_print_xyz_mm"]["bridge"][0]
    out["features"] = f

    # cross-checks against the meshes: the top pockets' ceilings and the bridge seat floor
    V, T = meshes["top_shell"]
    v0, v1, v2 = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
    nz = np.cross(v1 - v0, v2 - v0)[:, 2]
    zc = (v0[:, 2] + v1[:, 2] + v2[:, 2]) / 3
    flat_down = set(np.round(zc[nz < 0], 2))
    for c in f["top_pocket_ceiling"]:
        assert round(c, 2) in flat_down, f"top pocket ceiling {c} not in top_shell.3mf"
    V, _ = meshes["bridge"]
    h = V[:, 0].max() - V[:, 0]
    assert np.any(np.abs(h - (f["bridge_pedestal_top_above_feet"] - 0.6)) < 1e-3), "seat floor not in bridge.3mf"

    (HERE / "print_dims.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))


def stadium_width(w, h, dz):
    """Width along y of a stadium (overall w along y, h along z) at height dz from its centre."""
    r = h / 2
    if abs(dz) >= r:
        return 0.0
    return round(2 * (w / 2 - r + (r * r - dz * dz) ** 0.5), 3)


if __name__ == "__main__":
    main()
