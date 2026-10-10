"""
Build a concept option: fit the G2 skin, make the OCC solid, split it at the waterline
into the stone-coloured top and the black sole, export STEP, and render review views.

usage:  python build_concept.py A [--views hero,side,top] [--spp 64] [--res 1000x720]
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE.parent / "stone"))
sys.path.insert(0, str(ROOT / "render"))

import build123d as bd  # noqa: E402
from options import OPTIONS, Z_PART  # noqa: E402
from organic import Stone  # noqa: E402

OUT = ROOT / "build" / "concepts"


def build(key, verbose=True):
    spec = OPTIONS[key]
    t0 = time.time()
    st = Stone(spec, verbose=verbose)
    st.sample()
    dz = st.normalise()
    st.fit()
    so, ok = st.occ_solid()
    solid = bd.Solid(so)
    zp = Z_PART + dz
    top = solid.split(bd.Plane.XY.offset(zp), keep=bd.Keep.TOP)
    sole = solid.split(bd.Plane.XY.offset(zp), keep=bd.Keep.BOTTOM)
    bb = solid.bounding_box()
    info = dict(option=key, name=spec.name, valid=bool(ok),
                size=[round(bb.size.X, 2), round(bb.size.Y, 2), round(bb.size.Z, 2)],
                volume_cm3=round(solid.volume / 1000, 2), z_part=round(zp, 2),
                fit_err_max=round(float(st.fit_err[0]), 4), fit_err_rms=round(float(st.fit_err[1]), 4),
                build_s=round(time.time() - t0, 1))
    if verbose:
        print(json.dumps(info))
    return st, solid, top, sole, info


def export(key, st, solid, top, sole, info):
    d = OUT / key
    d.mkdir(parents=True, exist_ok=True)
    bd.export_step(solid, str(d / f"{key}_outer.step"))
    (d / "info.json").write_text(json.dumps(info, indent=2))
    from studio import tessellate, write_ply
    plys = {}
    for nm, shp in [("top", top), ("sole", sole)]:
        V, N, F = tessellate(shp)
        plys[nm] = write_ply(d / f"{nm}.ply", V, N, F)
    return plys


def review(key, plys, views, spp, res, solid):
    from studio import VIEWS, render, studio_scene
    bb = solid.bounding_box()
    tgt = np.array([(bb.min.X + bb.max.X) / 2, 0.0, bb.size.Z * 0.42])
    outs = []
    for v in views:
        cfg = VIEWS[v]
        org = tgt + np.array(cfg["offset"])
        sc = studio_scene([(plys["top"], "stone"), (plys["sole"], "sole")], org, tgt,
                          fov=cfg["fov"], res=res, spp=spp, up=cfg.get("up", (0, 0, 1)))
        out = OUT / key / f"review_{v}.png"
        render(sc, out)
        outs.append(out)
    return outs


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("key")
    ap.add_argument("--views", default="hero,side,top,front")
    ap.add_argument("--spp", type=int, default=48)
    ap.add_argument("--res", default="900x640")
    a = ap.parse_args()
    st, solid, top, sole, info = build(a.key)
    plys = export(a.key, st, solid, top, sole, info)
    w, h = map(int, a.res.split("x"))
    t = time.time()
    outs = review(a.key, plys, a.views.split(","), a.spp, (w, h), solid)
    print("rendered", [str(o) for o in outs], f"{time.time() - t:.1f}s")
