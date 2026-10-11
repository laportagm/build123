"""
Curvature-continuity checks on the fitted OCC B-spline skin.

ring_test   : principal curvatures on small rings around each parametric pole.  On a
              G2 surface they converge to one value pair as the ring shrinks (the
              spread over the ring -> 0); on a G1-only pole they stay scattered.
seam_test   : curvature on both sides of the periodic u-seam (C2 by construction).
equator_test: curvature jump across v = 1/2, where the top and underside height
              branches meet (G2 by the r_b matching in `Stone.edge_terms`).
Lengths mm, curvature 1/mm.
"""
import numpy as np
from OCP.GeomLProp import GeomLProp_SLProps
from OCP.gp import gp_Pnt


def _props(surf, u, v):
    pr = GeomLProp_SLProps(surf, float(u), float(v), 2, 1e-9)
    if not pr.IsCurvatureDefined():
        return None
    p = pr.Value()
    return np.array([p.X(), p.Y(), p.Z()]), pr.MinCurvature(), pr.MaxCurvature(), pr.MeanCurvature()


def ring_test(surf, which="top", vs=(0.0005, 0.001, 0.002, 0.004, 0.008, 0.016), n_u=96):
    """Spread of mean / principal curvature on rings v = const around a pole."""
    pole_v = 1.0 if which == "top" else 0.0
    P0 = np.array(surf.Value(0.0, pole_v).Coord())
    out = []
    for dv in vs:
        v = pole_v - dv if which == "top" else pole_v + dv
        H, k1, k2, r = [], [], [], []
        for u in np.linspace(0, 1, n_u, endpoint=False):
            res = _props(surf, u, v)
            if res is None:
                continue
            p, kmin, kmax, km = res
            H.append(km)
            k1.append(kmin)
            k2.append(kmax)
            r.append(np.linalg.norm(p - P0))
        H, k1, k2 = map(np.asarray, (H, k1, k2))
        out.append(dict(dv=dv, ring_r_mm=float(np.mean(r)),
                        H_mean=float(H.mean()), H_spread=float(H.max() - H.min()),
                        kmin_spread=float(k1.max() - k1.min()), kmax_spread=float(k2.max() - k2.min())))
    return out


def seam_test(surf, n_v=40, du=1e-7):
    worst = 0.0
    for v in np.linspace(0.02, 0.98, n_v):
        a = _props(surf, 1.0 - du, v)
        b = _props(surf, du, v)
        if a is None or b is None:
            continue
        worst = max(worst, abs(a[3] - b[3]))
    return worst


def equator_test(surf, n_u=96, dv=1e-6):
    worst = 0.0
    for u in np.linspace(0, 1, n_u, endpoint=False):
        a = _props(surf, u, 0.5 - dv)
        b = _props(surf, u, 0.5 + dv)
        if a is None or b is None:
            continue
        worst = max(worst, abs(a[3] - b[3]))
    return worst
