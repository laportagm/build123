"""
Studio renderer for design review: OCC shapes -> PLY (with exact surface normals) ->
Mitsuba 3 path tracer (llvm_ad_rgb).  Units: mm.  +z up, +x toward the device tail.
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np

import mitsuba as mi

mi.set_variant("llvm_ad_rgb")

# ------------------------------------------------------------------ tessellation


def tessellate(shape, lin_defl=0.015, ang_defl=0.12):
    """Triangulate an OCC/build123d shape; return (V, N, F) with exact surface normals."""
    from OCP.BRep import BRep_Tool
    from OCP.BRepLib import BRepLib_ToolTriangulatedShape
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.TopAbs import TopAbs_FACE, TopAbs_REVERSED
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopLoc import TopLoc_Location
    from OCP.TopoDS import TopoDS

    shp = shape.wrapped if hasattr(shape, "wrapped") else shape
    BRepMesh_IncrementalMesh(shp, lin_defl, False, ang_defl, True)
    Vs, Ns, Fs = [], [], []
    off = 0
    ex = TopExp_Explorer(shp, TopAbs_FACE)
    while ex.More():
        face = TopoDS.Face(ex.Current())
        loc = TopLoc_Location()
        tri = BRep_Tool.Triangulation_s(face, loc)
        ex.Next()
        if tri is None:
            continue
        if not tri.HasNormals():
            BRepLib_ToolTriangulatedShape.ComputeNormals_s(face, tri)
        trsf = loc.Transformation()
        n = tri.NbNodes()
        V = np.empty((n, 3))
        N = np.empty((n, 3))
        for i in range(1, n + 1):
            p = tri.Node(i).Transformed(trsf)
            V[i - 1] = (p.X(), p.Y(), p.Z())
            d = tri.Normal(i).Transformed(trsf)       # normals follow the shape's location too
            N[i - 1] = (d.X(), d.Y(), d.Z())
        F = np.empty((tri.NbTriangles(), 3), dtype=np.int64)
        for i in range(1, tri.NbTriangles() + 1):
            F[i - 1] = tri.Triangle(i).Get()
        F -= 1
        if face.Orientation() == TopAbs_REVERSED:
            F = F[:, ::-1]
            N = -N
        Vs.append(V)
        Ns.append(N)
        Fs.append(F + off)
        off += n
    V = np.vstack(Vs)
    N = np.vstack(Ns)
    N /= np.linalg.norm(N, axis=1, keepdims=True) + 1e-12
    return V, N, np.vstack(Fs)


def write_ply(path, V, N, F):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    header = (
        "ply\nformat binary_little_endian 1.0\n"
        f"element vertex {len(V)}\nproperty float x\nproperty float y\nproperty float z\n"
        "property float nx\nproperty float ny\nproperty float nz\n"
        f"element face {len(F)}\nproperty list uchar int vertex_indices\nend_header\n"
    )
    vert = np.hstack([V, N]).astype("<f4")
    face = np.empty(len(F), dtype=[("n", "u1"), ("i", "<i4", 3)])
    face["n"] = 3
    face["i"] = F
    with open(path, "wb") as f:
        f.write(header.encode())
        f.write(vert.tobytes())
        f.write(face.tobytes())
    return str(path)


# ------------------------------------------------------------------ materials

MATERIALS = {
    # warm light-grey PETG, satin (sanded / matte-finish print)
    "stone": {"type": "principled", "base_color": {"type": "rgb", "value": [0.60, 0.575, 0.535]},
              "roughness": 0.44, "specular": 0.45},
    "stone_cool": {"type": "principled", "base_color": {"type": "rgb", "value": [0.50, 0.52, 0.53]},
                   "roughness": 0.46, "specular": 0.42},
    "sole": {"type": "principled", "base_color": {"type": "rgb", "value": [0.022, 0.022, 0.024]},
             "roughness": 0.40, "specular": 0.45},
    "floor": {"type": "diffuse", "reflectance": {"type": "rgb", "value": [0.30, 0.295, 0.29]}},
    "floor_light": {"type": "diffuse", "reflectance": {"type": "rgb", "value": [0.78, 0.77, 0.75]}},
    "floor_dark": {"type": "diffuse", "reflectance": {"type": "rgb", "value": [0.16, 0.16, 0.17]}},
    "clay": {"type": "diffuse", "reflectance": {"type": "rgb", "value": [0.72, 0.72, 0.72]}},
}


def _look(origin, target, up=(0, 0, 1)):
    return mi.ScalarTransform4f().look_at(origin=list(map(float, origin)),
                                          target=list(map(float, target)), up=list(map(float, up)))


def _rect_light(center, target, size, radiance):
    """Area light (rectangle) at `center`, facing `target`."""
    c = np.asarray(center, float)
    t = np.asarray(target, float)
    to_world = _look(c, t, up=(0, 0, 1) if abs((t - c)[2]) < 0.99 * np.linalg.norm(t - c) else (1, 0, 0))
    return {"type": "rectangle",
            "to_world": to_world @ mi.ScalarTransform4f().scale([size[0] / 2, size[1] / 2, 1]),
            "emitter": {"type": "area", "radiance": {"type": "rgb", "value": list(map(float, radiance))}}}


def studio_scene(meshes, cam_origin, cam_target, fov=26.0, res=(1400, 1000), spp=96,
                 floor="floor", floor_z=0.0, env=0.30, key=1.0, up=(0, 0, 1), extra=None):
    """meshes: list of (ply_path, material_name_or_dict)."""
    tgt = np.asarray(cam_target, float)
    scene = {
        "type": "scene",
        "integrator": {"type": "path", "max_depth": 10},
        "sensor": {
            "type": "perspective", "fov": fov, "fov_axis": "x",
            "to_world": _look(cam_origin, cam_target, up),
            "film": {"type": "hdrfilm", "width": res[0], "height": res[1], "pixel_format": "rgb",
                     "rfilter": {"type": "gaussian"}},
            "sampler": {"type": "independent", "sample_count": spp},
        },
        "env": {"type": "constant", "radiance": {"type": "rgb", "value": [env, env, env * 1.02]}},
        # key: big soft box front-left-above; fill: right; rim: behind
        "key": _rect_light(tgt + [-260, -220, 330], tgt, (360, 300), np.array([7.5, 7.3, 7.0]) * key),
        "fill": _rect_light(tgt + [120, 300, 340], tgt, (300, 260), [1.9, 1.95, 2.05]),
        "rim": _rect_light(tgt + [330, -60, 140], tgt, (90, 380), [4.0, 4.0, 4.1]),
    }
    if floor:
        scene["floor"] = {"type": "rectangle",
                          "to_world": mi.ScalarTransform4f().translate([0, 0, floor_z]).scale([4000, 4000, 1]),
                          "bsdf": MATERIALS[floor] if isinstance(floor, str) else floor}
    for i, (ply, mat) in enumerate(meshes):
        bsdf = MATERIALS[mat] if isinstance(mat, str) else mat
        entry = {"type": "ply", "filename": str(ply), "face_normals": False}
        if isinstance(bsdf, dict) and bsdf.get("type") == "area":
            entry["emitter"] = bsdf
        else:
            entry["bsdf"] = bsdf
        scene[f"m{i}"] = entry
    if extra:
        scene.update(extra)
    return scene


def render(scene_dict, out_png, exposure=0.0):
    scene = mi.load_dict(scene_dict)
    img = mi.render(scene)
    bmp = mi.Bitmap(img)
    arr = np.array(bmp, copy=False).astype(np.float32) * (2.0 ** exposure)
    out = mi.Bitmap(arr).convert(pixel_format=mi.Bitmap.PixelFormat.RGB,
                                 component_format=mi.Struct.Type.UInt8, srgb_gamma=True)
    Path(out_png).parent.mkdir(parents=True, exist_ok=True)
    out.write(str(out_png))
    return out_png


# camera presets relative to a target point (front of the device is -x)
VIEWS = {
    "hero":  dict(offset=(-185, -150, 135), fov=24),
    "front": dict(offset=(-330, -40, 70), fov=20),
    "side":  dict(offset=(0, -360, 30), fov=22),
    "top":   dict(offset=(0.01, 0, 420), fov=20, up=(1, 0, 0)),
    "rear":  dict(offset=(230, 170, 120), fov=24),
    "low":   dict(offset=(-150, -230, 30), fov=24),
}
