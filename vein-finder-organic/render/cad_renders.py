"""
Gate-2 (CAD) review renders: assembled views, exploded assembly, sections, underside,
interior, USB landing and a zebra-stripe check of the G2 skin.

usage:  python cad_renders.py [names...] [--spp N] [--scale S]
Inputs: build/device/brep/*.brep (from cad/device/build.py).  Output: build/render/cad/*.png
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "cad" / "device"))

import build123d as bd  # noqa: E402
import mitsuba as mi  # noqa: E402
from studio import MATERIALS, render, studio_scene, tessellate, write_ply  # noqa: E402

BREP = ROOT / "build" / "device" / "brep"
OUT = ROOT / "build" / "render" / "cad"
PLY = ROOT / "build" / "render" / "cad_ply"

MAT = dict(MATERIALS)
MAT.update({
    "black_part": {"type": "principled", "base_color": {"type": "rgb", "value": [0.045, 0.045, 0.05]},
                   "roughness": 0.45, "specular": 0.4},
    "pcb": {"type": "principled", "base_color": {"type": "rgb", "value": [0.03, 0.06, 0.045]},
            "roughness": 0.3, "specular": 0.6},
    "battery": {"type": "principled", "base_color": {"type": "rgb", "value": [0.62, 0.63, 0.66]},
                "roughness": 0.35, "specular": 0.5, "metallic": 0.6},
    "metal": {"type": "principled", "base_color": {"type": "rgb", "value": [0.78, 0.78, 0.8]},
              "roughness": 0.25, "metallic": 1.0},
    "led": {"type": "principled", "base_color": {"type": "rgb", "value": [0.92, 0.9, 0.85]}, "roughness": 0.3},
    "led_red": {"type": "principled", "base_color": {"type": "rgb", "value": [0.75, 0.12, 0.08]}, "roughness": 0.3},
    "switch": {"type": "principled", "base_color": {"type": "rgb", "value": [0.15, 0.15, 0.17]}, "roughness": 0.4},
    "warm": {"type": "principled", "base_color": {"type": "rgb", "value": [0.95, 0.75, 0.4]}, "roughness": 0.3},
    "mirror": {"type": "roughconductor", "material": "Ag", "alpha": 0.004},
})
PART_MAT = {"top_shell": "stone", "sole": "sole", "seam_mask": "black_part", "bridge": "black_part",
            "pcb": "pcb", "battery": "battery", "magnets": "metal", "leds": "led_red", "ntc": "switch",
            "switch": "switch", "usb": "metal", "seam_leds": "warm", "pins": "warm"}


def load():
    return {p.stem: bd.import_brep(str(p)) for p in sorted(BREP.glob("*.brep"))}


def ply_of(name, shape, tag=""):
    path = PLY / f"{name}{tag}.ply"
    V, N, F = tessellate(shape, lin_defl=0.015, ang_defl=0.1)
    return write_ply(path, V, N, F)


def cut(shape, keep_box):
    try:
        r = shape & keep_box
        return r if r.volume > 1e-6 else None
    except Exception:  # noqa: BLE001
        return None


def go(name, meshes, origin, target, fov, res, spp, **kw):
    t = time.time()
    sc = studio_scene(meshes, origin, target, fov=fov, res=res, spp=spp, **kw)
    out = render(sc, OUT / f"{name}.png", exposure=kw.pop("exposure", 0.0) if "exposure" in kw else 0.0)
    print(f"[render] {name} {time.time() - t:.0f}s", flush=True)
    return out


def zebra_env(path, n_stripes=26, w=2048, h=1024):
    v = (np.arange(h) + 0.5) / h                      # 0 (zenith) .. 1 (nadir)
    band = (np.floor(v * n_stripes) % 2).astype(np.float32)
    img = np.repeat(band[:, None], w, axis=1)
    img = 0.03 + 2.2 * img
    rgb = np.stack([img] * 3, axis=2).astype(np.float32)
    mi.Bitmap(rgb).write(str(path))
    return path


def main(names, spp, scale):
    OUT.mkdir(parents=True, exist_ok=True)
    S = load()
    zp = 4.1762
    res = (int(1400 * scale), int(1000 * scale))
    tgt = np.array([17.0, 0.0, 10.0])
    if "magnets" in S:
        mags = S["magnets"].solids()
        cz = [m.center().Z for m in mags]
        zmid = 4.1762 + 1.0
        lo = [m for m, z in zip(mags, cz) if z < zmid]
        hi = [m for m, z in zip(mags, cz) if z >= zmid]
        S["magnets_sole"] = bd.Compound(lo)
        S["magnets_top"] = bd.Compound(hi)
        PART_MAT["magnets_sole"] = PART_MAT["magnets_top"] = "metal"
    plys = {n: ply_of(n, s) for n, s in S.items()}

    def meshes(names_, tag="", src=None):
        src = src or plys
        return [(src[n], MAT[PART_MAT[n]]) for n in names_ if n in src and src[n]]

    jobs = {}
    jobs["cad_hero"] = lambda: go("cad_hero", meshes(["top_shell", "sole"]), tgt + [-185, -150, 135], tgt, 24, res, spp)
    jobs["cad_rear"] = lambda: go("cad_rear", meshes(["top_shell", "sole", "usb", "pcb"]), np.array([60.0, 0, 6]) + [120, -70, 45],
                                  np.array([56.0, 0, 7]), 22, res, spp)
    def underside():
        # the stone turned over on the table, sole up (as you would inspect it)
        flip = {n: bd.Pos(0, 0, 25.4) * bd.Rot(180, 0, 0) * S[n] for n in ("top_shell", "sole", "leds")}
        m = [(ply_of(n, s, "_flip"), MAT[PART_MAT[n]]) for n, s in flip.items()]
        t2 = np.array([17.0, 0.0, 22.0])
        return go("cad_underside", m, t2 + [-150, 150, 190], t2, 26, res, spp, floor="floor_light")
    jobs["cad_underside"] = underside

    def exploded():
        off = {"sole": 0, "leds": 9, "ntc": 9, "pcb": 9, "magnets": 9, "usb": 9, "battery": 20,
               "seam_leds": 9, "pins": 9, "seam_mask": 30, "bridge": 42, "switch": 54, "top_shell": 78}
        ex = {}
        for n, s in S.items():
            ex[n] = ply_of(n, bd.Pos(0, 0, off[n]) * s, "_x")
        m = [(ex[n], MAT[PART_MAT[n]]) for n in ex]
        t2 = tgt + [0, 0, 32]
        return go("cad_exploded", m, t2 + [-215, -205, 150], t2, 28, (res[0], int(res[1] * 1.15)), spp,
                  floor_z=-0.5)
    jobs["cad_exploded"] = exploded

    def section_centre():
        keep = bd.Pos(20, 30, 10) * bd.Box(200, 60, 80)          # keep y >= 0
        cs = {n: cut(s, keep) for n, s in S.items()}
        m = []
        for n, s in cs.items():
            if s is not None:
                m.append((ply_of(n, s, "_secy"), MAT[PART_MAT[n]]))
        t2 = np.array([38.0, 0, 10])
        return go("cad_section_centre", m, t2 + [-10, -175, 38], t2, 30, res, spp, env=0.55)
    jobs["cad_section_centre"] = section_centre

    def section_button():
        keep = bd.Pos(35 + 50, 0, 10) * bd.Box(100, 120, 80)     # keep x >= 35 (button axis)
        cs = {n: cut(s, keep) for n, s in S.items()}
        m = []
        for n, s in cs.items():
            if s is not None:
                m.append((ply_of(n, s, "_secx"), MAT[PART_MAT[n]]))
        t2 = np.array([35.0, 0, 12])
        return go("cad_section_button", m, t2 + [-175, -40, 45], t2, 30, res, spp, env=0.55)
    jobs["cad_section_button"] = section_button

    def interior():
        flip = {n: bd.Pos(0, 0, 30) * bd.Rot(180, 0, 0) * S[n] for n in ("top_shell", "seam_mask", "bridge")}
        m = [(ply_of(n, s, "_in"), MAT[PART_MAT[n]]) for n, s in flip.items() if n == "top_shell"]
        t2 = np.array([17.0, 0, 30 - 10])
        return go("cad_interior", m, t2 + [-120, -150, 260], t2, 30, res, spp, env=0.5)
    jobs["cad_interior"] = interior

    def zebra():
        from skin import Skin
        sk = Skin(verbose=False)
        p = ply_of("skin", sk.solid)
        env = zebra_env(ROOT / "build" / "render" / "zebra_env.exr")
        t2 = np.array([20.0, 0, 12])
        out = []
        for nm, off_, up in (("cad_zebra", [-150, -170, 150], (0, 0, 1)), ("cad_zebra_top", [0.01, 0, 330], (1, 0, 0))):
            sc = {"type": "scene", "integrator": {"type": "path", "max_depth": 6},
                  "sensor": {"type": "perspective", "fov": 26, "fov_axis": "x",
                             "to_world": mi.ScalarTransform4f().look_at(origin=list(t2 + off_), target=list(t2), up=list(up)),
                             "film": {"type": "hdrfilm", "width": res[0], "height": res[1], "rfilter": {"type": "gaussian"}},
                             "sampler": {"type": "independent", "sample_count": max(32, spp // 2)}},
                  "env": {"type": "envmap", "filename": str(env),
                          "to_world": mi.ScalarTransform4f().rotate([1, 0, 0], 90) @ mi.ScalarTransform4f().rotate([0, 0, 1], 15)},
                  "skin": {"type": "ply", "filename": p, "bsdf": MAT["mirror"]}}
            out.append(render(sc, OUT / f"{nm}.png"))
            print(f"[render] {nm}", flush=True)
        return out
    jobs["cad_zebra"] = zebra

    # assembly guide: the build-up in five steps, same camera
    def asm(name, parts, lift=None):
        lift = lift or {}
        m = []
        for n in parts:
            if n not in S:
                continue
            sh = bd.Pos(0, 0, lift.get(n, 0.0)) * S[n] if lift.get(n) else S[n]
            m.append((ply_of(n, sh, f"_{name}"), MAT[PART_MAT[n]]))
        t2 = tgt + [0, 0, 4]
        return go(name, m, t2 + [-175, -165, 150], t2, 26, res, spp)
    jobs["asm_1_sole"] = lambda: asm("asm_1_sole", ["sole", "magnets_sole"])
    jobs["asm_2_board"] = lambda: asm("asm_2_board", ["sole", "magnets_sole", "pcb", "leds", "ntc", "usb", "pins", "seam_leds"],
                                      {"pcb": 12, "leds": 12, "ntc": 12, "usb": 12, "pins": 12, "seam_leds": 12})
    jobs["asm_3_battery"] = lambda: asm("asm_3_battery", ["sole", "magnets_sole", "pcb", "leds", "ntc", "usb", "pins",
                                                          "seam_leds", "battery"], {"battery": 14})
    jobs["asm_4_mask_bridge"] = lambda: asm("asm_4_mask_bridge", ["sole", "magnets_sole", "pcb", "leds", "ntc", "usb", "pins",
                                                                  "seam_leds", "battery", "seam_mask", "bridge", "switch"],
                                            {"seam_mask": 10, "bridge": 14, "switch": 14})
    jobs["asm_5_close"] = lambda: asm("asm_5_close", ["sole", "magnets_sole", "pcb", "leds", "ntc", "usb", "pins", "seam_leds",
                                                      "battery", "seam_mask", "bridge", "switch", "top_shell", "magnets_top"],
                                      {"top_shell": 38, "magnets_top": 38})

    for n in (names or list(jobs)):
        jobs[n]()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="*")
    ap.add_argument("--spp", type=int, default=64)
    ap.add_argument("--scale", type=float, default=0.7)
    a = ap.parse_args()
    main(a.names, a.spp, a.scale)
