"""G2 verification of the final device skin -> build/device/g2.json.

ring tests at both poles, the u-seam and the equator (see cad/stone/verify_g2.py), the
least-squares fit error, and a curvature scan along the centre line across the thumb dish
(mean curvature must vary continuously through the C2 blend)."""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "cad" / "stone"))
from skin import BUTTON_XY, DISH, Skin  # noqa: E402
from verify_g2 import equator_test, ring_test, seam_test  # noqa: E402

if __name__ == "__main__":
    sk = Skin(verbose=False)
    st = sk.st
    surf = st.occ_surface()
    rep = dict(fit_err_max_mm=float(st.fit_err[0]), fit_err_rms_mm=float(st.fit_err[1]),
               pole_info=st.pole_info, dish=dict(DISH, centre=BUTTON_XY, depth_mm=st.dish_depth))
    rep["ring_top"] = ring_test(surf, "top")
    rep["ring_bottom"] = ring_test(surf, "bot")
    rep["seam_jump_max"] = seam_test(surf)
    rep["equator_jump_max"] = equator_test(surf)
    # centre-line mean-curvature profile across the dish (top branch), from the OCC surface:
    from OCP.GeomLProp import GeomLProp_SLProps
    us = np.linspace(0, 1, 2688, endpoint=False)
    vs = np.linspace(0.5, 1.0, 1200)
    S, N = sk.outer(us, vs)
    prof = []
    for x in np.arange(18.0, 56.0, 0.5):
        d = np.hypot(S[..., 0] - x, S[..., 1])
        i, j = np.unravel_index(np.argmin(d + 100 * (S[..., 2] < 10)), d.shape)
        pr = GeomLProp_SLProps(surf, float(us[j]), float(vs[i]), 2, 1e-9)
        if not pr.IsCurvatureDefined():
            continue
        prof.append((float(x), float(S[i, j, 2]), float(pr.MeanCurvature()), float(pr.MinCurvature()), float(pr.MaxCurvature())))
    prof = np.array(prof)
    rep["centreline"] = prof.round(5).tolist()
    jumps = np.abs(np.diff(prof[:, 2]))
    rep["centreline_mean_curvature_max_step_per_0.5mm"] = float(jumps.max())
    out = ROOT / "build" / "device" / "g2.json"
    out.write_text(json.dumps(rep, indent=1, default=float))
    print(json.dumps({k: v for k, v in rep.items() if k not in ("centreline",)}, indent=1, default=float))
