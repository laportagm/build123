"""Survey the hollowed skin: cavity outline at the PCB levels and ceiling height map.
Writes build/device/survey.npz and a plot for layout work."""
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
from skin import Skin  # noqa: E402

OUT = ROOT / "build" / "device"
OUT.mkdir(parents=True, exist_ok=True)


def section_xy(solid, z, n=1600):
    import build123d as bd
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Section
    from OCP.gp import gp_Pln, gp_Pnt, gp_Dir
    s = BRepAlgoAPI_Section(solid.wrapped, gp_Pln(gp_Pnt(0, 0, z), gp_Dir(0, 0, 1)))
    s.Build()
    shp = bd.Compound(s.Shape())
    loops = []
    for w in shp.edges():
        pts = np.array([[p.X, p.Y] for p in [w.position_at(t) for t in np.linspace(0, 1, 60)]])
        loops.append(pts)
    return loops


if __name__ == "__main__":
    t0 = time.time()
    sk = Skin(verbose=False)
    cav, info = sk.cavity_solid(1.8)
    print("cavity", info, round(time.time() - t0, 1), "s")
    zp = sk.z_part
    C, tu, tv, P = sk.cavity_net[1.8]
    # ceiling height map from the dense inner samples (upper sheet only: normal z > 0)
    from scipy.interpolate import griddata
    up = P[2:-2]
    pts = up.reshape(-1, 3)
    # keep the part of the inner surface above the PCB top
    sel = pts[:, 2] > zp + 0.2
    xs = np.arange(-32, 66, 0.25)
    ys = np.arange(-32, 32, 0.25)
    X, Y = np.meshgrid(xs, ys)
    Zc = griddata(pts[sel, :2], pts[sel, 2], (X, Y), method="linear")
    # cavity sections at the PCB bottom/top and battery top
    secs = {z: section_xy(cav, z) for z in (zp + 0.01, zp + 1.0, zp + 1.3, zp + 6.2)}
    np.savez(OUT / "survey.npz", X=X, Y=Y, Zc=Zc, zp=zp,
             **{f"sec_{k:.2f}": np.vstack(v) for k, v in secs.items()},
             boundary=sk.st.boundary)
    print("saved", OUT / "survey.npz", round(time.time() - t0, 1), "s")
    for z, loops in secs.items():
        allp = np.vstack(loops)
        print(f"section z={z:.2f}: x [{allp[:,0].min():.2f},{allp[:,0].max():.2f}] y [{allp[:,1].min():.2f},{allp[:,1].max():.2f}]")
