"""
Device skin (gate 2): form A "Pebble" as approved at the concept gate, with the finger
dimple replaced by a worry-stone thumb dish on the front of the crown (where the hidden
button now sits), plus the inner offset surfaces used to hollow the top shell.

Coordinates as in the concept: window centre at the origin, +x toward the tail, z up,
z = 0 at the lowest skin-contact point.  Lengths in mm.

Inner offset ("cavity") solids
------------------------------
OpenCascade's thick-solid offset fails on this single periodic B-spline face (invalid
result after ~150 s), so the cavity is built explicitly:
  1. sample the fitted outer B-spline and its unit normals densely;
  2. for every meridian u, offset the part above the waterline inward by t
     (Q = S - t N), starting where the outer surface crosses the waterline;
  3. continue each meridian below the waterline with a G1 quadratic (tangent at the
     start, vertical at the end) down to the cap plane z_cap < z_part;
  4. resample every meridian by arc length, fit one B-spline surface (periodic in u,
     pole at the crown, bottom row exactly on z = z_cap) and close it with a planar cap.
The result is a valid solid; subtracting it from the top part leaves a wall of normal
thickness t everywhere above the waterline.
"""
from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

import numpy as np
from scipy.interpolate import BSpline

HERE = Path(__file__).resolve().parent
CAD = HERE.parent
sys.path.insert(0, str(CAD / "stone"))
sys.path.insert(0, str(CAD / "concepts"))

from options import OPTION_A, Z_PART, ellipsoid_dome  # noqa: E402
from organic import Stone  # noqa: E402

# ----------------------------------------------------------------------------- form
BUTTON_XY = (35.0, 0.0)     # thumb-dish centre = membrane / switch axis (plan)

# Worry-stone thumb dish on the crown front (replaces the concept's 0.55 mm finger dimple).
# A curved 0.45 mm PETG skin is ~5x stiffer than a flat one (shell action; see checks.py),
# so the button needs a nearly flat skin: inside the ellipse (a, b) the top becomes a very
# shallow concave paraboloid (curvature `k`, radius 1/k) laid in the dome's tangent plane at
# the centre; a C2 weight blends it back to the dome over `blend` mm (G2 preserved).  The
# depth is set so the dish never rises above the dome (no raised rim).
DISH = dict(a=10.0, b=14.0, blend=6.0, k=0.002)


def concept_h(x, y):
    """Top rise above the silhouette: the approved concept dome (dimple removed)."""
    return ellipsoid_dome(x, y, xc=27.0, ax_front=50.0, ax_back=66.0, ay=46.0, lo=5.2, hi=16.9)


def _smoothstep5(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * t * (t * (6 * t - 15) + 10)


class DeviceStone(Stone):
    """Form A with the thumb dish.  Only the top branch is changed, inside the dish."""

    def __init__(self, spec, verbose=True, dish=DISH):
        super().__init__(spec, verbose=verbose)
        self.dish = dish
        self._dish_frame()

    def _raw_top(self, P):
        from matplotlib.tri import Triangulation
        tri = Triangulation(self.V[:, 0], self.V[:, 1], self.F)
        tau = self._bary_eval(tri, P, self.tau)
        sd = self._bary_eval(tri, P, self.sdist)
        g = self._bary_eval(tri, P, self.g)
        return Stone.heights(self, P, tau, sd, g, True)

    def _dish_frame(self):
        d = self.dish
        cx, cy = BUTTON_XY
        # tangent plane of the undished top at the centre (local cubic fit, r <= 3 mm)
        r = np.linspace(0.3, 3.0, 10)
        t = np.linspace(0, 2 * np.pi, 36, endpoint=False)
        R, T = np.meshgrid(r, t, indexing="ij")
        dx = np.r_[0.0, (R * np.cos(T)).ravel()]
        dy = np.r_[0.0, (R * np.sin(T)).ravel()]
        z = self._raw_top(np.c_[cx + dx, cy + dy])
        A = np.c_[np.ones_like(dx), dx, dy, dx * dx, dx * dy, dy * dy, dx**3, dx * dx * dy, dx * dy * dy, dy**3]
        c = np.linalg.lstsq(A, z, rcond=None)[0]
        self.dish_plane = (c[0], c[1], c[2])
        # depth: the dish surface may touch but never exceed the dome on the inner ellipse
        th = np.linspace(0, 2 * np.pi, 180, endpoint=False)
        bx, by = d["a"] * np.cos(th), d["b"] * np.sin(th)
        zb = self._raw_top(np.c_[cx + bx, cy + by])
        lift = c[0] + c[1] * bx + c[2] * by + 0.5 * d["k"] * (bx**2 + by**2) - zb
        self.dish_depth = float(lift.max())
        if self.verbose:
            print(f"[{self.spec.name}] thumb dish {2 * d['a']:.0f} x {2 * d['b']:.0f} mm, "
                  f"depth {self.dish_depth:.2f} mm below the dome's tangent plane")

    def dish_weight(self, x, y):
        d = self.dish
        rho = np.sqrt(((x - BUTTON_XY[0]) / d["a"]) ** 2 + ((y - BUTTON_XY[1]) / d["b"]) ** 2)
        s = (rho - 1.0) * min(d["a"], d["b"]) / d["blend"]
        return 1.0 - _smoothstep5(s)

    def heights(self, q, tau, sd, g, top):
        z = Stone.heights(self, q, tau, sd, g, top)
        if not top or not hasattr(self, "dish_plane"):
            return z
        x, y = q[:, 0] - BUTTON_XY[0], q[:, 1] - BUTTON_XY[1]
        z0, gx, gy = self.dish_plane
        dish = z0 - self.dish_depth + gx * x + gy * y + 0.5 * self.dish["k"] * (x * x + y * y)
        w = self.dish_weight(q[:, 0], q[:, 1])
        return z + w * (dish - z)


SPEC = dataclasses.replace(OPTION_A, name="device", h_top=concept_h,
                           notes=dict(title="Pebble (device)", tag="gate-2 skin with thumb dish"))


# ----------------------------------------------------------------------------- evaluator
class SurfEval:
    """Vectorised evaluation of the clamped-v / periodic-u cubic B-spline control net."""

    def __init__(self, ctrl, tu, tv):
        self.C = np.asarray(ctrl, float)               # (nv, nu, 3)
        self.nv, self.nu, _ = self.C.shape
        self.tu, self.tv = np.asarray(tu), np.asarray(tv)

    def grid(self, us, vs):
        """S, S_u, S_v on the tensor grid (len(vs), len(us), 3)."""
        nv, nu = self.nv, self.nu
        bv = BSpline(self.tv, self.C.reshape(nv, nu * 3), 3)
        A = bv(vs).reshape(len(vs), nu, 3)
        Av = bv.derivative()(vs).reshape(len(vs), nu, 3)
        out = []
        for M in (A, Av):
            ext = np.concatenate([M, M[:, :3]], axis=1)                  # periodic wrap (nu + 3)
            bu = BSpline(self.tu, np.transpose(ext, (1, 0, 2)).reshape(nu + 3, -1), 3)
            out.append((bu(np.mod(us, 1.0)), bu.derivative()(np.mod(us, 1.0))))
        (S, Su), (Sv, _) = out
        sh = (len(us), len(vs), 3)
        S, Su, Sv = (np.transpose(a.reshape(sh), (1, 0, 2)) for a in (S, Su, Sv))
        return S, Su, Sv

    def normals(self, us, vs):
        S, Su, Sv = self.grid(us, vs)
        N = np.cross(Su, Sv)
        N /= np.linalg.norm(N, axis=2, keepdims=True) + 1e-300
        return S, N


# ----------------------------------------------------------------------------- build
class Skin:
    def __init__(self, verbose=True):
        import build123d as bd
        self.st = DeviceStone(SPEC, verbose=verbose)
        self.st.sample()
        self.dz = self.st.normalise()
        self.st.fit(g2_poles=True)
        so, ok = self.st.occ_solid()
        assert ok, "outer solid invalid"
        self.solid = bd.Solid(so)
        self.z_part = Z_PART + self.dz
        self.ev = SurfEval(self.st.ctrl, self.st.tu, self.st.tv)
        # orientation of the normals (outward): check against the centroid
        us = np.linspace(0, 1, 64, endpoint=False)
        S, N = self.ev.normals(us, np.array([0.5]))
        cc = self.solid.center()
        c = np.array([cc.X, cc.Y, cc.Z])
        self.nsign = 1.0 if np.mean(np.sum((S - c) * N, axis=2)) > 0 else -1.0

    def outer(self, us, vs):
        """Points and outward unit normals.  At the two poles S_u vanishes, so the normal
        there is taken as the u-average of the normals on a tiny ring (G1 pole: exact)."""
        S, N = self.ev.normals(us, vs)
        N = self.nsign * N
        for v_pole, v_near in ((0.0, 1e-5), (1.0, 1.0 - 1e-5)):
            rows = np.where(np.abs(vs - v_pole) < 1e-9)[0]
            if len(rows):
                _, Nr = self.ev.normals(us, np.array([v_near]))
                n = (self.nsign * Nr[0]).mean(axis=0)
                N[rows] = n / np.linalg.norm(n)
        return S, N

    # -------------------------------------------------------------- cavity samples
    def cavity_samples(self, t, z_cap, n_u=672, n_v=900, n_rows=360, ext_len=1.5):
        """Arc-length-resampled inner meridians (n_rows, n_u, 3) for wall thickness t.

        t is a constant or a function t(x, y) of the outer point's plan position (used for
        the button skin, which thins smoothly inside the wall instead of a stepped pocket)."""
        us = np.linspace(0.0, 1.0, n_u, endpoint=False)
        vs = np.linspace(0.30, 1.0, n_v)
        S, N = self.outer(us, vs)                          # (n_v, n_u, 3)
        tt = t(S[..., 0], S[..., 1])[..., None] if callable(t) else t
        Q = S - tt * N
        zp = self.z_part
        rows = np.empty((n_rows, n_u, 3))
        info = []
        for j in range(n_u):
            z = S[:, j, 2]
            # last waterline crossing below the equator (outer surface going up through zp)
            idx = np.where((z[:-1] < zp) & (z[1:] >= zp) & (vs[:-1] < 0.5))[0]
            k = idx[-1]
            f = (zp - z[k]) / (z[k + 1] - z[k])
            q_w = Q[k, j] + f * (Q[k + 1, j] - Q[k, j])
            top = np.vstack([q_w, Q[k + 1:, j]])           # offset meridian, waterline -> crown pole
            d = top[0] - top[1]
            d /= np.linalg.norm(d)
            if d[2] > -0.2:                                # make sure the extension heads down
                d = d + np.array([0.0, 0.0, -0.2 - d[2]])
                d /= np.linalg.norm(d)
            p0 = top[0]
            p1 = p0 + ext_len * d
            p2 = np.array([p1[0], p1[1], z_cap])
            s = np.linspace(0.0, 1.0, 40)[:-1]             # quadratic Bezier, cap end first
            bez = ((1 - s) ** 2)[:, None] * p2 + (2 * (1 - s) * s)[:, None] * p1 + (s**2)[:, None] * p0
            mer = np.vstack([bez, top])                    # z_cap -> crown pole
            seg = np.linalg.norm(np.diff(mer, axis=0), axis=1)
            L = np.r_[0.0, np.cumsum(seg)]
            tt = np.linspace(0.0, L[-1], n_rows)
            rows[:, j] = np.c_[[np.interp(tt, L, mer[:, k3]) for k3 in range(3)]].T
            info.append((float(vs[k] + f * (vs[k + 1] - vs[k])), float(q_w[2])))
        rows[0, :, 2] = z_cap
        return us, np.linspace(0.0, 1.0, n_rows), rows, info

    def cavity_solid(self, t, z_cap=None, nu=336, nv=72, smooth=1e-5, key=None):
        """Closed solid: everything inside the outer skin by at least t (mm, or t(x, y)),
        above z_cap."""
        z_cap = self.z_part - 1.2 if z_cap is None else z_cap
        us, vs, P, info = self.cavity_samples(t, z_cap)
        t = key if key is not None else t
        C, tu, tv, err = fit_grid(P, us, vs, nu, nv, smooth=smooth, plane_bottom_z=z_cap)
        above = P[..., 2] > self.z_part
        self.cavity_net = getattr(self, "cavity_net", {})
        self.cavity_net[t] = (C, tu, tv, P)
        return make_capped_solid(C, nu, nv, z_cap), dict(
            t=t, z_cap=float(z_cap), fit_err_max_above_waterline=float(err[above].max()),
            fit_err_rms_above_waterline=float(np.sqrt((err[above] ** 2).mean())))


# ----------------------------------------------------------------------------- generic fit
def _bases(us, vs, nu, nv, p=3):
    tu = np.arange(-p, nu + p + 1) / nu
    Bx = BSpline.design_matrix(np.mod(us, 1.0), tu, p, extrapolate=False).toarray()
    Bu = np.zeros((len(us), nu))
    for j in range(Bx.shape[1]):
        Bu[:, j % nu] += Bx[:, j]
    inner = np.linspace(0, 1, nv - p + 1)
    tv = np.r_[[0.0] * p, inner, [1.0] * p]
    Bv = BSpline.design_matrix(vs, tv, p).toarray()
    return Bu, Bv, tu, tv


def _reg(B, n, smooth, periodic):
    D = np.zeros((n, n))
    for i in range(n):
        if periodic or 1 <= i <= n - 2:
            D[i, (i - 1) % n] += 1
            D[i, i] -= 2
            D[i, (i + 1) % n] += 1
    return B.T @ B + smooth * len(B) / n * (D.T @ D)


def fit_grid(P, us, vs, nu, nv, smooth=2e-5, plane_bottom_z=None):
    """Fit a periodic-u / clamped-v cubic B-spline with a pole at v = 1 (top row collapsed,
    next row projected into the tangent plane) and, optionally, the v = 0 row on a plane."""
    Bu, Bv, tu, tv = _bases(us, vs, nu, nv)
    Pu = np.linalg.solve(_reg(Bu, nu, smooth, True), Bu.T)
    Pv = np.linalg.solve(_reg(Bv, nv, smooth, False), Bv.T)
    C = np.transpose(np.tensordot(np.tensordot(Pv, P, axes=(1, 0)), Pu, axes=(1, 1)), (0, 2, 1)).copy()
    pole = P[-1].mean(axis=0)
    C[-1] = pole
    Qd = C[-2] - pole
    _, _, vt = np.linalg.svd(Qd, full_matrices=False)
    n = vt[-1]
    C[-2] = C[-2] - np.outer(Qd @ n, n)
    if plane_bottom_z is not None:
        C[0, :, 2] = plane_bottom_z
    S = np.transpose(np.tensordot(np.tensordot(Bv, C, axes=(1, 0)), Bu, axes=(1, 1)), (0, 2, 1))
    err = np.linalg.norm(S - P, axis=2)
    return C, tu, tv, err


def occ_bspline(C, nu, nv):
    from OCP.collections import Array1_double, Array1_int, Array2_gp_Pnt
    from OCP.Geom import Geom_BSplineSurface
    from OCP.gp import gp_Pnt
    poles = Array2_gp_Pnt(1, nu, 1, nv)
    for i in range(nu):
        for j in range(nv):
            poles.SetValue(i + 1, j + 1, gp_Pnt(*map(float, C[j, i])))
    uk = Array1_double(1, nu + 1)
    um = Array1_int(1, nu + 1)
    for i in range(nu + 1):
        uk.SetValue(i + 1, i / nu)
        um.SetValue(i + 1, 1)
    distinct = np.linspace(0, 1, nv - 3 + 1)
    vk = Array1_double(1, len(distinct))
    vm = Array1_int(1, len(distinct))
    for i, k in enumerate(distinct):
        vk.SetValue(i + 1, float(k))
        vm.SetValue(i + 1, 4 if i in (0, len(distinct) - 1) else 1)
    return Geom_BSplineSurface(poles, uk, vk, um, vm, 3, 3, True, False)


def make_capped_solid(C, nu, nv, z_cap):
    """B-spline patch (pole at v=1, planar boundary at v=0) + planar cap -> valid solid."""
    import build123d as bd
    from OCP.BRep import BRep_Tool
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.BRepBuilderAPI import (BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakeSolid,
                                    BRepBuilderAPI_MakeWire, BRepBuilderAPI_Sewing)
    from OCP.BRepCheck import BRepCheck_Analyzer
    from OCP.gp import gp_Dir, gp_Pln, gp_Pnt
    from OCP.ShapeFix import ShapeFix_Solid
    from OCP.TopAbs import TopAbs_EDGE, TopAbs_SHELL
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopoDS import TopoDS

    surf = occ_bspline(C, nu, nv)
    face = BRepBuilderAPI_MakeFace(surf, 1e-6).Face()
    # the bottom boundary edge: the non-degenerate, non-seam edge lying on z = z_cap
    ex = TopExp_Explorer(face, TopAbs_EDGE)
    wire_mk = BRepBuilderAPI_MakeWire()
    while ex.More():
        e = TopoDS.Edge(ex.Current())
        if not BRep_Tool.Degenerated_s(e):
            crv = BRepAdaptor_Curve(e)
            a, b = crv.FirstParameter(), crv.LastParameter()
            pa, pb, pm = crv.Value(a), crv.Value(b), crv.Value(0.5 * (a + b))
            if abs(pm.Z() - z_cap) < 1e-6 and abs(pa.Z() - z_cap) < 1e-6:
                wire_mk.Add(e)
        ex.Next()
    cap = BRepBuilderAPI_MakeFace(gp_Pln(gp_Pnt(0, 0, z_cap), gp_Dir(0, 0, -1)), wire_mk.Wire()).Face()
    sew = BRepBuilderAPI_Sewing(1e-5)
    sew.Add(face)
    sew.Add(cap)
    sew.Perform()
    sewed = sew.SewedShape()
    ex = TopExp_Explorer(sewed, TopAbs_SHELL)
    shell = TopoDS.Shell(ex.Current())
    so = BRepBuilderAPI_MakeSolid(shell).Solid()
    fx = ShapeFix_Solid(so)
    fx.Perform()
    so = fx.Solid()
    solid = bd.Solid(so)
    if solid.volume < 0:
        so.Reverse()
        solid = bd.Solid(so)
    assert BRepCheck_Analyzer(so).IsValid(), "cavity solid invalid"
    return solid
