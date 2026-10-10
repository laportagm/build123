"""
Concept-board renders (gate 1).

  python concept_renders.py            # all options, all views
  python concept_renders.py --fast     # low spp preview

Studio views for A/B/C, plus for A (the chosen form): seam-on detail, underside, and an
in-context shot on a forearm where the window shows transilluminated skin.
"""
import argparse
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "cad" / "concepts"))
sys.path.insert(0, str(ROOT / "cad" / "stone"))

import mitsuba as mi  # noqa: E402

from studio import MATERIALS, _look, render, studio_scene, write_ply  # noqa: E402

OUT = ROOT / "docs" / "01-concept" / "renders"
BUILD = ROOT / "build" / "concepts"

SEAM_ARC = dict(r=18.6, a0=-44.0, a1=44.0)          # hairline status seam on the rim slope, over the PCB ring
SEAM_GLOW = [1.00 * 7.0, 0.80 * 7.0, 0.58 * 7.0]     # warm white through the thin wall


def tube_mesh(P, radius, n_side=10, taper=2.5):
    """Tube along polyline P (N,3) -> V, N, F; radius fades to zero over `taper` mm at both ends."""
    T = np.gradient(P, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    ref = np.array([0.0, 0.0, 1.0])
    Nn = np.cross(T, ref)
    Nn /= np.linalg.norm(Nn, axis=1, keepdims=True)
    Bn = np.cross(T, Nn)
    ang = np.linspace(0, 2 * np.pi, n_side, endpoint=False)
    s = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    rad = radius * np.sqrt(np.clip(np.minimum(s, s[-1] - s) / taper, 0.0, 1.0))
    V, N = [], []
    for i in range(len(P)):
        for a in ang:
            d = np.cos(a) * Nn[i] + np.sin(a) * Bn[i]
            V.append(P[i] + rad[i] * d)
            N.append(d)
    F = []
    for i in range(len(P) - 1):
        for j in range(n_side):
            a, b = i * n_side + j, i * n_side + (j + 1) % n_side
            c, d = a + n_side, b + n_side
            F += [[a, c, b], [b, c, d]]
    return np.array(V), np.array(N), np.array(F)


def seam_ply(stone, dz, path):
    th = np.radians(np.linspace(SEAM_ARC["a0"], SEAM_ARC["a1"], 160))
    xy = np.c_[SEAM_ARC["r"] * np.cos(th), SEAM_ARC["r"] * np.sin(th)]
    zt, _ = stone.probe(xy)
    P = np.c_[xy, zt + dz - 0.22]
    V, N, F = tube_mesh(P, 0.42)
    return write_ply(path, V, N, F)


def write_ply_uv(path, V, N, UV, F):
    header = (
        "ply\nformat binary_little_endian 1.0\n"
        f"element vertex {len(V)}\nproperty float x\nproperty float y\nproperty float z\n"
        "property float nx\nproperty float ny\nproperty float nz\nproperty float u\nproperty float v\n"
        f"element face {len(F)}\nproperty list uchar int vertex_indices\nend_header\n"
    )
    vert = np.hstack([V, N, UV]).astype("<f4")
    face = np.empty(len(F), dtype=[("n", "u1"), ("i", "<i4", 3)])
    face["n"] = 3
    face["i"] = F
    with open(path, "wb") as f:
        f.write(header.encode())
        f.write(vert.tobytes())
        f.write(face.tobytes())
    return str(path)


def glow_texture(path, n=768):
    """Transilluminated skin inside the window: bright near the LED rim, dark veins."""
    s = np.linspace(-16, 16, n)
    X, Y = np.meshgrid(s, s)                       # X along the arm (+x = tail), Y across
    r = np.hypot(X, Y)
    rim = np.clip((r - 2.0) / 14.0, 0, 1) ** 1.6
    front = 0.35 + 0.65 * np.clip((X + 16.0) / 18.0, 0, 1)   # no LEDs across the gap
    glow = (0.32 + 0.68 * rim) * front

    def vein(path_xy, w):
        px, py = path_xy
        d = np.full(X.shape, 1e9)
        for i in range(len(px) - 1):
            ax_, ay_, bx, by = px[i], py[i], px[i + 1], py[i + 1]
            vx, vy = bx - ax_, by - ay_
            t = np.clip(((X - ax_) * vx + (Y - ay_) * vy) / (vx * vx + vy * vy), 0, 1)
            d = np.minimum(d, np.hypot(X - ax_ - t * vx, Y - ay_ - t * vy))
        return np.exp(-0.5 * (d / w) ** 2)

    t = np.linspace(-20, 20, 60)
    v1 = vein((t, 2.0 + 3.2 * np.sin(t / 9.0)), 1.15)
    t2 = np.linspace(-1, 20, 30)
    v2 = vein((t2, 2.0 + 3.2 * np.sin(t2 / 9.0) - 0.48 * (t2 + 1)), 0.8)
    t3 = np.linspace(-20, 4, 30)
    v3 = vein((t3, -9.5 + 0.18 * t3 + 1.2 * np.sin(t3 / 6.0)), 0.7)
    veins = np.clip(0.85 * v1 + 0.7 * v2 + 0.55 * v3, 0, 1)
    edge = 1.0 - np.clip((r - 14.6) / 1.4, 0, 1) ** 2 * (3 - 2 * np.clip((r - 14.6) / 1.4, 0, 1))
    lum = glow * (1.0 - 0.80 * veins) * edge
    img = np.stack([1.00 * lum, 0.115 * lum, 0.045 * lum], axis=-1).astype(np.float32)
    mi.Bitmap(img).write(str(path))
    return str(path)


def arm_meshes(z_top, d):
    """Forearm as a broad elliptic cylinder (top radius 120 mm) + an emissive window patch."""
    xs = np.linspace(-150, 190, 341)
    ys = np.linspace(-62, 62, 125)
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    a, b = 62.0, 31.0
    Z = z_top - b * (1 - np.sqrt(np.clip(1 - (Y / a) ** 2, 0, None)))
    dzdy = -b * (Y / a**2) / np.sqrt(np.clip(1 - (Y / a) ** 2, 1e-6, None))
    Nrm = np.stack([np.zeros_like(Z), -dzdy, np.ones_like(Z)], -1)
    Nrm /= np.linalg.norm(Nrm, axis=-1, keepdims=True)
    V = np.stack([X, Y, Z], -1).reshape(-1, 3)
    N = Nrm.reshape(-1, 3)
    nx, ny = X.shape
    idx = np.arange(nx * ny).reshape(nx, ny)
    quads = np.stack([idx[:-1, :-1], idx[1:, :-1], idx[1:, 1:], idx[:-1, 1:]], -1).reshape(-1, 4)
    cx = V[quads].mean(1)
    win = np.hypot(cx[:, 0], cx[:, 1]) < 16.0
    def tri(q):
        return np.r_[q[:, [0, 1, 2]], q[:, [0, 2, 3]]]
    arm = write_ply(d / "arm.ply", V, N, tri(quads[~win]))
    UV = np.c_[(V[:, 0] + 16) / 32, (V[:, 1] + 16) / 32]
    Vw = V.copy()
    Vw[:, 2] += 0.03
    glow = write_ply_uv(d / "arm_window.ply", Vw, N, UV, tri(quads[win]))
    return arm, glow


def flip_transform(height):
    return mi.ScalarTransform4f().translate([0, 0, height]) @ mi.ScalarTransform4f().rotate([1, 0, 0], 180)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fast", action="store_true")
    ap.add_argument("--only", default="ABC")
    ap.add_argument("--extras", action="store_true", help="A-only extra views")
    ap.add_argument("--views", default="hero,side,plan", help="studio views to render for --only options")
    ap.add_argument("--no-extras", action="store_true")
    a = ap.parse_args()
    spp = 24 if a.fast else 160
    res = (900, 620) if a.fast else (1500, 1040)
    OUT.mkdir(parents=True, exist_ok=True)

    from build_concept import build, export
    built = {}
    for k in a.only:
        st, solid, top, sole, info = build(k, verbose=False)
        plys = export(k, st, solid, top, sole, info)
        built[k] = (st, solid, plys, info)
        print(k, info)

    views = {
        "hero": dict(offset=(-165, -140, 150), fov=23, tz=0.38),
        "side": dict(offset=(-6, -400, 18), fov=17, tz=0.42),
        "plan": dict(offset=(0.01, 0, 430), fov=19, tz=0.0, up=(1, 0, 0)),
    }
    views = {k: v for k, v in views.items() if k in a.views.split(",")}
    for k, (st, solid, plys, info) in built.items():
        bb = solid.bounding_box()
        cx = (bb.min.X + bb.max.X) / 2
        for vname, v in views.items():
            tgt = np.array([cx, 0.0, bb.size.Z * v["tz"]])
            sc = studio_scene([(plys["top"], "stone"), (plys["sole"], "sole")], tgt + np.array(v["offset"]),
                              tgt, fov=v["fov"], res=res, spp=spp, up=v.get("up", (0, 0, 1)))
            render(sc, OUT / f"{k}_{vname}.png")
            print("rendered", k, vname)

    if "A" in built and (a.extras or not a.fast) and not a.no_extras:
        st, solid, plys, info = built["A"]
        bb = solid.bounding_box()
        cx = (bb.min.X + bb.max.X) / 2
        d = BUILD / "A"
        dz = st.dz
        seam = seam_ply(st, dz, d / "seam.ply")
        glow = {"type": "area", "radiance": {"type": "rgb", "value": SEAM_GLOW}}
        meshes = [(plys["top"], "stone"), (plys["sole"], "sole"), (seam, glow)]
        # front-three-quarter with seam glowing
        tgt = np.array([cx, 0.0, bb.size.Z * 0.38])
        sc = studio_scene(meshes, tgt + np.array([-165, -140, 150]), tgt, fov=23, res=res, spp=spp)
        render(sc, OUT / "A_hero_seam.png")
        # detail: window rim, seam and index dimple, grazing light
        tgt = np.array([14.0, 0.0, 13.0])
        sc = studio_scene(meshes, tgt + np.array([-70, -48, 62]), tgt, fov=30, res=res, spp=spp, key=0.75)
        render(sc, OUT / "A_detail.png")
        # rear three-quarter (tail, USB-C side)
        tgt = np.array([cx, 0.0, bb.size.Z * 0.38])
        sc = studio_scene(meshes, tgt + np.array([190, 150, 120]), tgt, fov=23, res=res, spp=spp)
        render(sc, OUT / "A_rear.png")
        # underside: flip the parts and lay them on the floor
        H = bb.max.Z
        flip = flip_transform(H)
        extra = {}
        for i, (p, mat) in enumerate([(plys["top"], "stone"), (plys["sole"], "sole")]):
            extra[f"u{i}"] = {"type": "ply", "filename": str(p), "face_normals": False,
                              "to_world": flip, "bsdf": MATERIALS[mat]}
        tgt = np.array([cx, 0.0, H * 0.4])
        sc = studio_scene([], tgt + np.array([-150, 150, 165]), tgt, fov=23, res=res, spp=spp, extra=extra)
        render(sc, OUT / "A_underside.png")
        # in context: on a forearm, dim room, the skin inside the window is the display
        z_arm = float(st.spec.base(0.0, 0.0) + dz)
        arm, win = arm_meshes(z_arm, d)
        tex = glow_texture(d / "glow.exr")
        skin = {"type": "principled", "base_color": {"type": "rgb", "value": [0.70, 0.47, 0.37]},
                "roughness": 0.55, "specular": 0.30}
        win_em = {"type": "area", "radiance": {"type": "bitmap", "filename": tex, "raw": True}}
        meshes_ctx = [(plys["top"], "stone"), (plys["sole"], "sole"), (seam, glow), (arm, skin)]
        extra = {"win": {"type": "ply", "filename": win, "face_normals": False, "emitter": win_em, "bsdf": skin}}
        tgt = np.array([4.0, 0.0, 8.0])
        sc = studio_scene(meshes_ctx, tgt + np.array([-120, -95, 125]), tgt, fov=30, res=res, spp=spp,
                          floor="floor_dark", floor_z=z_arm - 31.5, env=0.06, key=0.22, extra=extra)
        render(sc, OUT / "A_context.png")
        print("rendered A extras")


if __name__ == "__main__":
    main()
