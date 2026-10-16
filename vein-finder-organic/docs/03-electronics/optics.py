"""
Gate-3 light budget with the chosen 1206 LEDs, using the concept's tissue model
(calc/concept_budget.py) on the real LED positions from the CAD layout.

The SunLED datasheets give luminous intensity, not radiant power, and the sources
disagree, so the optical power per LED is an ESTIMATE:
  660 nm XZM2MR55W-3: 1095 mcd @ 20 mA (one listing; another says 2890 mcd, which would
    imply > 80 % wall-plug efficiency and is rejected), 40 deg beam -> cos^m beam with
    m = 11.1, flux = 2 pi I0 / (m + 1) = 0.57 lm, / 46 lm/W (660 nm, 20 nm FWHM) = 12 mW,
    scaled to the operating current.
  625 nm XZM2CRK55W-3: intensity not verified; bracketed by a wall-plug efficiency of
    5-15 % (typical of small AlGaInP indicator chips).
Both are bench-verified at gate 5 (photodiode / lux meter at a fixed distance).

    python optics.py  ->  optics.json

Personal prototype for bench evaluation - NOT a medical device.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "calc"))
import concept_budget as C  # noqa: E402

LAYOUT = json.loads((ROOT / "build" / "device" / "layout.json").read_text())


def flux_lm(i0_cd, half_angle_deg):
    m = math.log(0.5) / math.log(math.cos(math.radians(half_angle_deg)))
    return 2 * math.pi * i0_cd / (m + 1)


def main():
    k660 = C.luminous_efficacy(660.0, 20.0)
    p660_20 = flux_lm(1.095, 20.0) / k660                     # W at 20 mA
    p660 = p660_20 * 23.0 / 20.0                             # at the 23 mA cap (linear, small die)
    p625 = (0.05 * 0.0249 * 2.2, 0.15 * 0.0249 * 2.2)        # W at 24.9 mA, WPE 5-15 %
    out = dict(assumptions=dict(p660_mW_at_23mA=round(p660 * 1e3, 1), k660_lm_per_W=round(k660, 1),
                                p625_mW_range=[round(p * 1e3, 1) for p in p625], coupling=C.COUPLING,
                                ambient_lx=C.AMBIENT_LX, shade=C.SHADE), rows=[])
    for bank, wl, plist in (("660", 660, [p660]), ("620", 620, list(p625))):
        src = np.array([[l["x"], l["y"]] for l in LAYOUT["leds"] if l["bank"] == bank]) * C.MM
        K = C.luminous_efficacy(660.0, 20.0) if wl == 660 else C.luminous_efficacy(625.0, 17.0)
        for skin, t in C.SKINS.items():
            L_amb = C.AMBIENT_LX * C.SKIN_VIS_REFL[skin] * C.SHADE / math.pi
            vals = []
            for p in plist:
                w = C.window_exitance(src, p * C.COUPLING, t, wl)
                vals.append(dict(rim=K * w["rim"] / math.pi, centre=K * w["centre"] / math.pi))
            out["rows"].append(dict(bank=bank + (" nm" if bank == "660" else " (625) nm"), skin=skin,
                                    L_rim_nit=[round(v["rim"], 1) for v in vals],
                                    L_centre_nit=[round(v["centre"], 2) for v in vals],
                                    L_ambient_nit=round(L_amb, 1),
                                    rim_over_ambient=[round(v["rim"] / L_amb, 2) for v in vals],
                                    centre_over_ambient=[round(v["centre"] / L_amb, 3) for v in vals]))
    (HERE / "optics.json").write_text(json.dumps(out, indent=1))
    print(out["assumptions"])
    print("| bank | skin | rim / room veil | centre / room veil |")
    print("|---|---|---|---|")
    for r in out["rows"]:
        fmt = lambda a: "-".join(f"{v:g}" for v in a)
        print(f"| {r['bank']} | {r['skin']} | {fmt(r['rim_over_ambient'])} | {fmt(r['centre_over_ambient'])} |")


if __name__ == "__main__":
    main()
