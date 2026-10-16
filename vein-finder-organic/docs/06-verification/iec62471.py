"""
IEC 62471 (photobiological safety of lamps and lamp systems) assessment for the chosen
LEDs, at the hardware current ceiling (the firmware cannot exceed it).

Method (IEC 62471:2006, as reproduced by secondary sources; the standard itself was not
available here, so every limit below is labelled with that source and must be checked
against the standard before relying on it):
  * Classification distance 200 mm (general lighting service, cl. 5.2.2).
  * Retinal thermal hazard, exempt: L_R <= 28 000 / alpha  W m-2 sr-1, alpha in rad,
    clamped to 0.0017 <= alpha <= 0.1 (Table 6).  R(lambda) = 1.0 for 500-700 nm.
  * Blue-light hazard: B(lambda) = 0.001 for 600-700 nm (Table 4.2).  Small source
    (alpha < 0.011 rad): exempt if E_B <= 0.01 W m-2 (Table 6).
  * Infrared eye (780-3000 nm) and UV hazards: no emission from AlGaInP 625/660 nm LEDs.
  * Skin thermal hazard: in use the face sits on the skin; the skin-surface temperature is
    held <= 41 C by the firmware's NTC limit (gate 4), which is the binding control.
Source model: a bare LED viewed on axis from 200 mm, the dome's image of the die taken as
the apparent source (die 0.25 x 0.25 mm magnified 1.5x by the 1.6 mm dome; smaller
apparent sources give higher radiance, so the area is a conservative lower bound),
cos^m beam fitted to the datasheet viewing angle.  All six LEDs of a bank are summed for
the irradiance limits (worst case: all six in view).

    python iec62471.py  ->  iec62471.json
"""
from __future__ import annotations

import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OPT = json.loads((ROOT / "docs" / "03-electronics" / "optics.json").read_text())["assumptions"]
D = 0.200
DIE = 0.25e-3 * 1.5          # apparent source side, m
A_SRC = DIE ** 2


def lamp(name, p_W, half_angle_deg, n_leds=6):
    m = math.log(0.5) / math.log(math.cos(math.radians(half_angle_deg)))
    I_e = p_W * (m + 1) / (2 * math.pi)                 # W/sr on axis
    L = I_e / A_SRC                                     # W m-2 sr-1
    alpha = DIE / D
    alpha_eff = min(max(alpha, 0.0017), 0.1)
    L_R_lim = 28000.0 / alpha_eff
    E = n_leds * I_e / D ** 2                           # W/m2, all six on axis (worst case)
    E_B = 0.001 * E
    return dict(lamp=name, p_opt_mW=round(p_W * 1e3, 1), beam_half_angle_deg=half_angle_deg, I_e_mW_per_sr=round(I_e * 1e3, 1),
                alpha_mrad=round(alpha * 1e3, 2), radiance_W_m2_sr=round(L), L_R_exempt_limit=round(L_R_lim),
                retinal_thermal_fraction=round(L / L_R_lim, 4), small_source=alpha < 0.011,
                E_B_W_m2=round(E_B, 5), blue_light_fraction=round(E_B / 0.01, 3),
                group="Exempt" if L / L_R_lim < 1 and E_B / 0.01 < 1 else "check")


def main():
    # 660 nm: optics.py's estimate (linear in current), at the 27.1 mA worst-case ceiling
    p660 = OPT["p660_mW_at_23mA"] * 1e-3 * 27.1 / 23.0
    # 625 nm: upper bracket, 15 % wall-plug efficiency at 27.1 mA x 2.5 V (max Vf)
    p625 = 0.15 * 0.0271 * 2.5
    rows = [lamp("SunLED XZM2MR55W-3, 660 nm, 6 lit", p660, 20.0),
            lamp("SunLED XZM2CRK55W-3, 625 nm, 6 lit", p625, 17.5)]
    (HERE / "iec62471.json").write_text(json.dumps(rows, indent=1, default=float))
    for r in rows:
        print(r)


if __name__ == "__main__":
    main()
