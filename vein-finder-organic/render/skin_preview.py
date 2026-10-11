"""Quick look at the device skin (no internals): hero / raking / top views.
usage: python skin_preview.py OUT_PREFIX [a b blend k] [--spp N]"""
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "cad" / "device"))

import build123d as bd  # noqa: E402
from studio import render, studio_scene, tessellate, write_ply  # noqa: E402

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    spp = int(sys.argv[sys.argv.index("--spp") + 1]) if "--spp" in sys.argv else 48
    out = Path(args[0])
    import skin as SK
    if len(args) >= 5:
        a, b, bl, k = map(float, args[1:5])
        SK.DISH.update(a=a, b=b, blend=bl, k=k)
    t = time.time()
    sk = SK.Skin(verbose=False)
    top = sk.solid.split(bd.Plane.XY.offset(sk.z_part), keep=bd.Keep.TOP)
    sole = sk.solid.split(bd.Plane.XY.offset(sk.z_part), keep=bd.Keep.BOTTOM)
    plys = []
    for nm, s, m in (("top", top, "stone"), ("sole", sole, "sole")):
        V, N, F = tessellate(s)
        plys.append((write_ply(out.parent / f"{out.name}_{nm}.ply", V, N, F), m))
    tgt = np.array([17.0, 0.0, 10.0])
    views = {"hero": (tgt + [-185, -150, 135], 24, (0, 0, 1)), "rake": (tgt + [-40, -330, 60], 22, (0, 0, 1)),
             "back": (tgt + [230, -120, 120], 24, (0, 0, 1))}
    for v, (org, fov, up) in views.items():
        sc = studio_scene(plys, org, tgt, fov=fov, res=(900, 640), spp=spp, up=up)
        render(sc, f"{out}_{v}.png")
    print("depth", round(sk.st.dish_depth, 2), "done", round(time.time() - t, 1), "s")
