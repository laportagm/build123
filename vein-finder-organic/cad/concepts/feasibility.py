"""
Concept-gate geometric feasibility, measured on the actual G2 surfaces:

  1. Printability: overhang angle (from vertical) of every outer-surface facet,
     top shell printed waterline-down, sole printed inverted (waterline-down).
  2. Battery fit: largest clearance-feasible placement of a pouch cell under the
     top shell (inner surface = outer - wall), resting on the PCB.
  3. Switch fit: room under the index dimple for a 13 mm-stem 6x6 tactile switch.
  4. Mass estimate from measured areas/volumes.

Lengths in mm, masses in g.  Writes build/concepts/feasibility.json
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE.parent / "stone"))
sys.path.insert(0, str(ROOT / "render"))

from build_concept import build  # noqa: E402
from options import Z_PART  # noqa: E402
from studio import tessellate  # noqa: E402

WALL_TOP = 1.8            # top shell wall (>= 1.6 required)
PCB_T = 1.0               # PCB thickness (1.0 mm FR4 keeps mass down)
UNDER_BATT = 1.2          # component keep-out + foam pad between PCB and cell
BAY_FOAM = 0.4            # cell resting on the sole inside a PCB cut-out (battery bay)
CLEAR = 0.4               # air gap to the inner wall
PETG_DENSITY = 1.27       # g/cm3
FR4_DENSITY = 1.85        # g/cm3
OVERHANG_LIMIT_DEG = 45.0

CELLS = {
    # name: (thickness, width, length, mass_g, capacity_mAh)   -- from distributor listings (see BOM gate)
    "Jauch LP503040JH 600 mAh": (5.4, 30.5, 42.0, 12.1, 600),
    "SparkFun PRT-13854 850 mAh": (6.2, 34.0, 43.0, 20.0, 850),
}
SWITCH_H = 7.3            # 6x6 mm tactile switch, 7.3 mm actuator height above PCB (variant to source)
SWITCH_XY = (21.0, 0.0)   # plunger centre: 0.5 mm behind the dimple centre, body clear of the cell bay
PLUNGER_R = 1.75          # 3.5 mm actuator
MEMBRANE_T = 0.8          # flexing membrane thickness under the dimple


def overhang_stats(V, N, F, z_part, part):
    """Overhang of outer facets in print orientation (0 deg = vertical wall, 90 = ceiling).

    Normals come from the triangle winding, oriented outward with the signed volume of
    the closed part mesh (robust to OCC face orientation flags)."""
    tri = V[F]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    area = 0.5 * np.linalg.norm(n, axis=1)
    signed_vol = np.einsum("ij,ij->i", tri[:, 0], np.cross(tri[:, 1], tri[:, 2])).sum() / 6.0
    if signed_vol < 0:
        n = -n
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-15
    on_plane = np.all(np.abs(tri[:, :, 2] - z_part) < 1e-3, axis=1)
    keep = (~on_plane) & (area > 1e-9)
    nz = n[keep, 2] if part == "top" else -n[keep, 2]      # sole printed upside-down
    a = area[keep]
    down = nz < 0
    ang = np.degrees(np.arcsin(np.clip(-nz, 0, 1)))
    over = down & (ang > OVERHANG_LIMIT_DEG)
    return dict(max_overhang_deg=round(float(ang[down].max()) if down.any() else 0.0, 1),
                area_over_limit_mm2=round(float(a[over].sum()), 1),
                outer_area_mm2=round(float(a.sum()), 0),
                closed_mesh_volume_cm3=round(abs(signed_vol) / 1000, 2))


def battery_fit(st, dz, z_part, cell, on_sole=True, x_min=24.0):
    """Best placement of the cell (either orientation) on the centre line behind the window.

    Every footprint sample must be inside the planform and clear of the window wall,
    and the top surface must leave room for cell + clearance + wall above it."""
    from matplotlib.path import Path as MplPath
    t, w, L, m, cap = cell
    z_bot = z_part + (BAY_FOAM if on_sole else PCB_T + UNDER_BATT)
    z_need = z_bot + t + CLEAR + WALL_TOP
    inner = MplPath(st.boundary)
    best = None
    for orient, (lx, ly) in (("along", (L, w)), ("across", (w, L))):
        for x0 in np.arange(x_min, 64.0 - lx + 0.01, 0.5):
            xs = np.linspace(x0, x0 + lx, 25)
            ys = np.linspace(-ly / 2, ly / 2, 17)
            X, Y = np.meshgrid(xs, ys)
            P = np.c_[X.ravel(), Y.ravel()]
            from scipy.spatial import cKDTree
            dist, _ = cKDTree(st.boundary).query(P)
            ok = inner.contains_points(P) & (dist >= WALL_TOP + CLEAR) & \
                (np.hypot(P[:, 0], P[:, 1]) > 15.0 + WALL_TOP + CLEAR)
            if not ok.all():
                margin = -99.0
            else:
                zt, _ = st.probe(P)
                margin = float((zt + dz - z_need).min())
            if best is None or margin > best[2]:
                best = (orient, x0, margin)
    o, x0, mg = best
    lx = L if o == "along" else w
    return dict(orientation=o, x_from=round(x0, 1), x_to=round(x0 + lx, 1), min_margin_mm=round(mg, 2),
                fits=mg >= 0, cell_top_z=round(z_bot + t, 2))


def switch_fit(st, dz, z_part, xy):
    """Clearance between the actuator top and the membrane, checked over the whole plunger."""
    th = np.linspace(0, 2 * np.pi, 24)
    P = np.r_[[list(xy)], np.c_[xy[0] + PLUNGER_R * np.cos(th), xy[1] + PLUNGER_R * np.sin(th)]]
    zt, _ = st.probe(P)
    room = float((zt + dz - MEMBRANE_T - (z_part + PCB_T + SWITCH_H)).min())
    return dict(at=list(xy), top_surface_z=round(float(zt[0] + dz), 2), spare_mm=round(room, 2), fits=room >= 0.2)


def main():
    out = {}
    for k in "ABC":
        st, solid, top, sole, info = build(k, verbose=False)
        zp = Z_PART + st.dz                      # exact plane (info["z_part"] is rounded)
        res = dict(size_mm=info["size"], volume_cm3=info["volume_cm3"], z_part=zp)
        for nm, shp in [("top", top), ("sole", sole)]:
            V, N, F = tessellate(shp, lin_defl=0.03, ang_defl=0.2)
            res[f"print_{nm}"] = overhang_stats(V, N, F, zp, nm)
        res["battery"] = {c: battery_fit(st, st.dz, zp, cell, x_min=24.3) for c, cell in CELLS.items()}
        res["switch"] = switch_fit(st, st.dz, zp, SWITCH_XY)
        # mass: shell ~ outer area x wall (perimeter-dominated print, ~100% dense),
        # sole is a solid plate printed at ~70% effective density (4 walls, 25% gyroid)
        shell_g = res["print_top"]["outer_area_mm2"] * WALL_TOP / 1000 * PETG_DENSITY
        sole_g = sole.volume / 1000 * 0.70 * PETG_DENSITY
        res["mass_estimate_g"] = dict(top_shell=round(shell_g, 1), sole=round(sole_g, 1))
        out[k] = res
        print(k, json.dumps(res))
    p = ROOT / "build" / "concepts" / "feasibility.json"
    p.write_text(json.dumps(out, indent=2))
    print("wrote", p)


if __name__ == "__main__":
    main()
