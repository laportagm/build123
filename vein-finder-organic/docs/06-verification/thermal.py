"""
Skin-face temperature at full brightness with the chosen LEDs, using the concept's
thermal model (calc/concept_budget.py: hemispherical spot sources in perfused skin, the
whole lit bank, plus a lumped 1.5 K for the device's own heat at the contact face).
Optical power per LED from docs/03-electronics/optics.py (estimates, see there).

    python thermal.py  ->  thermal.json

Personal prototype for bench evaluation - NOT a medical device.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "calc"))
import concept_budget as C  # noqa: E402

LAYOUT = json.loads((ROOT / "build" / "device" / "layout.json").read_text())
OPT = json.loads((ROOT / "docs" / "03-electronics" / "optics.json").read_text())["assumptions"]


def main():
    rows = []
    for bank, wl, p_list in (("660", 660, [OPT["p660_mW_at_23mA"] * 1e-3]),
                             ("620", 620, [p * 1e-3 for p in OPT["p625_mW_range"]])):
        src = np.array([[l["x"], l["y"]] for l in LAYOUT["leds"] if l["bank"] == bank]) * C.MM
        for skin, t in C.SKINS.items():
            mua = C.mua_per_mm(t, wl) / C.MM
            musp = t.musp_per_mm / C.MM
            f_abs = 1.0 - C.farrell_Rd_total(mua, musp, t.n) * C.epidermis_T(t, wl) ** 2
            per_W = C.spot_rise_self(1.0) + C.spot_rise_neighbours(1.0, src)
            T = [C.SKIN_T0_C + C.DEVICE_SHARE_K + p * C.COUPLING * f_abs * per_W for p in p_list]
            rows.append(dict(bank=bank if bank == "660" else "625", skin=skin, f_abs=round(f_abs, 3),
                             T_face_C=[round(x, 1) for x in T], margin_to_41C=[round(41.0 - x, 1) for x in T]))
    (HERE / "thermal.json").write_text(json.dumps(rows, indent=1))
    for r in rows:
        print(r)


if __name__ == "__main__":
    main()
