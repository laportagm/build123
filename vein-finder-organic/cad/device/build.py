"""
Gate-2 build driver.

  python build.py            build every part, write BREP cache + STEP (+ assembly) + PLY
  python build.py --checks   also run checks.py (walls, overhang, interference, mass,
                             button force, magnet pull) -> build/device/checks.json
  python build.py --3mf      also write the print-ready 3MF files

Outputs in build/device/ (gitignored); the release copies go to docs/02-cad/.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import build123d as bd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "render"))
OUT = ROOT / "build" / "device"

PRINTED = ("top_shell", "sole", "seam_mask", "bridge")
COLOURS = {"top_shell": (0.86, 0.83, 0.78), "sole": (0.08, 0.08, 0.09), "seam_mask": (0.1, 0.1, 0.1),
           "bridge": (0.1, 0.1, 0.1), "pcb": (0.05, 0.12, 0.08), "battery": (0.55, 0.57, 0.6),
           "magnets": (0.75, 0.75, 0.78), "leds": (0.95, 0.95, 0.9), "ntc": (0.2, 0.2, 0.2),
           "switch": (0.2, 0.2, 0.22), "usb": (0.8, 0.8, 0.82), "seam_leds": (1.0, 0.85, 0.5)}


def load_or_build(force=False, only=()):
    from parts import Parts
    cache = OUT / "brep"
    names = list(COLOURS)
    if only:
        pa = Parts()
        shapes = {n: bd.import_brep(str(cache / f"{n}.brep")) for n in names}
        stand = pa.stand_ins()
        for n in only:
            shapes[n] = stand[n] if n in stand else getattr(pa, n)()
            bd.export_brep(shapes[n], str(cache / f"{n}.brep"))
        return pa, shapes
    if not force and all((cache / f"{n}.brep").exists() for n in names):
        shapes = {n: bd.import_brep(str(cache / f"{n}.brep")) for n in names}
        return None, shapes
    pa = Parts()
    shapes = pa.build_all()
    cache.mkdir(parents=True, exist_ok=True)
    for n, s in shapes.items():
        bd.export_brep(s, str(cache / f"{n}.brep"))
    (OUT / "parts_info.json").write_text(json.dumps(pa.info, indent=1, default=float))
    return pa, shapes


def export_step(shapes):
    d = OUT / "step"
    d.mkdir(parents=True, exist_ok=True)
    for n, s in shapes.items():
        if n in PRINTED:
            bd.export_step(s, str(d / f"{n}.step"))
    children = []
    for n, s in shapes.items():
        s = bd.Compound([s]) if not isinstance(s, bd.Compound) else s
        s.label = n
        s.color = bd.Color(*COLOURS[n])
        children.append(s)
    asm = bd.Compound(children=children, label="vein_finder_organic")
    bd.export_step(asm, str(d / "assembly.step"))
    return d


def export_ply(shapes):
    from studio import tessellate, write_ply
    d = OUT / "ply"
    d.mkdir(parents=True, exist_ok=True)
    for n, s in shapes.items():
        V, N, F = tessellate(s, lin_defl=0.02, ang_defl=0.12)
        write_ply(d / f"{n}.ply", V, N, F)
    return d


def export_3mf(shapes, zp):
    """One 3MF per printed part, in print orientation, sitting on z = 0."""
    d = OUT / "3mf"
    d.mkdir(parents=True, exist_ok=True)
    orient = {
        "top_shell": lambda s: bd.Pos(0, 0, -zp) * s,                              # waterline down
        "sole": lambda s: bd.Pos(0, 0, zp) * bd.Rot(180, 0, 0) * s,                # flipped, waterline down
        "seam_mask": lambda s: s,                                                   # base (PCB face) down
        "bridge": lambda s: bd.Rot(0, -90, 0) * s,                                 # on its +x face
    }
    for n in PRINTED:
        s = orient[n](shapes[n])
        bb = s.bounding_box()
        s = bd.Pos(-bb.center().X, -bb.center().Y, -bb.min.Z) * s
        m = bd.Mesher()
        m.add_shape(s, linear_deflection=0.01, angular_deflection=0.1)
        m.write(str(d / f"{n}.3mf"))
    return d


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--checks", action="store_true")
    ap.add_argument("--3mf", dest="mf", action="store_true")
    ap.add_argument("--only", default="", help="rebuild only these parts (comma list), reuse the cache")
    a = ap.parse_args()
    t = time.time()
    pa, shapes = load_or_build(a.force, tuple(x for x in a.only.split(",") if x))
    import checks
    vols = {}
    for k, v in shapes.items():
        vols[k] = checks.mesh_volume(v) / 1000
        print(f"{k:10s} valid={v.is_valid}  volume={vols[k]:7.3f} cm3 (mesh)", flush=True)
    (OUT / "volumes_cm3.json").write_text(json.dumps(vols, indent=1))
    print("step ->", export_step(shapes), round(time.time() - t, 1), "s", flush=True)
    print("ply  ->", export_ply(shapes), round(time.time() - t, 1), "s", flush=True)
    if a.checks or a.mf:
        if pa is None:
            from parts import Parts
            pa = Parts(verbose=False)
    if a.mf:
        print("3mf  ->", export_3mf(shapes, pa.zp), round(time.time() - t, 1), "s", flush=True)
    if a.checks:
        rep = checks.run(pa, shapes)
        print(json.dumps(rep, indent=1, default=float))
    print("done", round(time.time() - t, 1), "s")
