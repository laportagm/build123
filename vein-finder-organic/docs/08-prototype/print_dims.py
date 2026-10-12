"""
First-article reference dimensions for the print packet (print-packet.md), read from the
committed print meshes (docs/02-cad/3mf/*.3mf, written by cad/device/build.py in print
orientation, each sitting on z = 0) and from cad/device/params.py.

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

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "cad" / "device"))
import params as P  # noqa: E402

MESHES = ROOT / "docs" / "02-cad" / "3mf"
PARTS = ("sole", "top_shell", "bridge", "seam_mask")


def vertices(path: Path):
    with zipfile.ZipFile(path) as z:
        name = next(n for n in z.namelist() if n.endswith(".model"))
        root = ET.fromstring(z.read(name))
    out = []
    for v in root.iter():
        if v.tag.endswith("}vertex") or v.tag == "vertex":
            out.append((float(v.get("x")), float(v.get("y")), float(v.get("z"))))
    return out


def stadium_width(w, h, dz):
    """Width along y of a stadium (overall w along y, h along z) at height dz from its centre."""
    r = h / 2
    if abs(dz) >= r:
        return 0.0
    return round(2 * (w / 2 - r + (r * r - dz * dz) ** 0.5), 3)


def bbox(vs):
    lo = [min(v[i] for v in vs) for i in range(3)]
    hi = [max(v[i] for v in vs) for i in range(3)]
    return [round(h - l, 3) for l, h in zip(lo, hi)]


def main():
    lay = json.loads((ROOT / "docs" / "02-cad" / "pcb" / "layout.json").read_text())
    zp = lay["z_part"]
    out = {"source": "docs/02-cad/3mf/*.3mf (print orientation), cad/device/params.py, "
                     "docs/02-cad/pcb/layout.json, cad/device/parts.py",
           "bbox_print_xyz_mm": {}}
    for n in PARTS:
        out["bbox_print_xyz_mm"][n] = bbox(vertices(MESHES / f"{n}.3mf"))

    # Fit features, nominal = mating part + the clearance params.py designs in.
    out["features"] = {
        "magnet_pocket_d": round(P.MAG_D + P.MAG_POCKET_CLEAR, 3),
        "dowel_counterbore_d": round(P.MAG_D + P.MAG_DOWEL_CLEAR, 3),
        "magnet_d": P.MAG_D,
        "pcb_magnet_hole_d": P.MAG_PCB_HOLE,
        "horn_sole_pocket_depth": round(3.18 - 2.0 + 0.05, 3),          # parts.sole(): sole_h - proud + 0.05
        "tail_sole_pocket_depth": round(1.59 - (P.PCB_T + 0.15) + 0.05, 3),
        "magnet_centre_dist_horns_y": round(2 * abs(P.MAGNETS[0]["y"]), 3),
        "magnet_centre_dist_tails_y": round(2 * abs(P.MAGNETS[2]["y"]), 3),
        "magnet_centre_dist_horn_tail_x": round(P.MAGNETS[2]["x"] - P.MAGNETS[0]["x"], 3),
        # per magnet: hole play minus pocket play; a pair may differ by twice that
        "magnet_centre_dist_tol": round(2 * ((P.MAG_PCB_HOLE - P.MAG_D) / 2 - P.MAG_POCKET_CLEAR / 2), 3),
        "led_channel_radial": round(P.LED_PKG[1] + 2 * P.LED_POCKET_CLEAR, 3),
        "led_channel_tangential": round(P.LED_LAND[0] + 2 * P.LED_POCKET_LAND, 3),
        "led_body_radial_max": round(P.LED_PKG[1] + P.LED_TOL, 3),
        "ntc_pocket": [round(P.NTC_LAND[0] + 0.3, 3), round(P.NTC_LAND[1] + 0.3, 3)],
        "ntc_pocket_depth": round(P.NTC_PKG[2] + 0.15, 3),
        "ntc_body_max": list(P.NTC_PKG),
        "usb_opening": [round(P.USB_W + 2 * P.USB_CLEAR, 3), round(P.USB_H + 2 * P.USB_CLEAR, 3)],
        "usb_shell": [P.USB_W, P.USB_H],
        "usb_opening_below_waterline": round(zp - (lay["usb"]["z_c"] - (P.USB_H + 2 * P.USB_CLEAR) / 2), 3),
        # the opening and the shell are stadiums (rounded ends along y) centred at z_c, above the
        # waterline: the sole holds only their lower segments, so at its waterline face they are
        # narrower than their full widths (which the top shell holds, at z_c)
        "usb_opening_width_at_waterline": stadium_width(P.USB_W + 2 * P.USB_CLEAR, P.USB_H + 2 * P.USB_CLEAR,
                                                        zp - lay["usb"]["z_c"]),
        "usb_shell_width_at_waterline": stadium_width(P.USB_W, P.USB_H, zp - lay["usb"]["z_c"]),
        "usb_centre_above_waterline": round(lay["usb"]["z_c"] - zp, 3),
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
    # Bridge heights above its feet (the PCB top), from the same formulae as parts.bridge_geometry()
    z_pcb = zp + P.PCB_T
    z_deck0 = z_pcb + P.BATT_FOAM + P.BATT_T + P.BATT_TOP_CLEAR
    out["features"]["bridge_deck_underside_above_feet"] = round(z_deck0 - z_pcb, 3)
    out["features"]["bridge_deck_top_above_feet"] = round(z_deck0 + 2.5 - z_pcb, 3)
    # the pedestal top is the print bbox along x (the bridge prints on its +x face, device z -> print x)
    out["features"]["bridge_pedestal_top_above_feet"] = out["bbox_print_xyz_mm"]["bridge"][0]
    out["features"]["sole_height_print"] = out["bbox_print_xyz_mm"]["sole"][2]
    (HERE / "print_dims.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
