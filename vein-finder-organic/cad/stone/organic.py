"""
Organic, curvature-continuous (G2) stone modelling for build123d / OpenCascade.

Pipeline
--------
1. Planform: a smooth closed C-shape (body outline minus a keyhole = window + front gap),
   built from 2D signed distance fields with C2 smooth-min/max, then contoured.
2. Mesh the planform (Triangle) and solve three small FEM problems on it:
      tau   : torsion function, Laplace(tau) = -1, tau = 0 on the edge  -> "inflation"
      s~    : screened-Poisson distance to the edge (smooth near-edge distance)
      g     : boundary flux |grad tau|, extended harmonically inside
3. Map the planform to the unit disk (Floater mean-value map, bijective), then build a
   sphere-like parametrisation  (v, phi):  rho = sin v,  v in [0, pi]
      v < pi/2 : underside,   v = pi/2 : silhouette ("equator"),   v > pi/2 : top
4. Heights
      top    z = z_eq + H * f(psi),          psi = sqrt(tau / tau_max),  f odd to 2nd order
      bottom z = z_eq - Db * R(s~ / r_b),     R(t) = sqrt(1 - (1 - t)^4)  (saturates, C2)
   with r_b chosen so the top and bottom have the SAME edge curvature at every
   silhouette point.  Both branches are then one C2 function of v across the equator,
   so the closed surface is G2 there by construction.
5. Least-squares fit of ONE cubic B-spline surface: periodic in u (C2 across the seam),
   clamped in v with the two end rows collapsed to poles (G1 enforced exactly, G2 to
   fit tolerance -- the poles are placed in low-curvature regions).
6. Make an OCC face -> shell -> solid.  Everything downstream (split, shell, pockets) is
   ordinary build123d.

All lengths in mm.  Coordinates: window centre at the origin, +x toward the tail,
z = 0 on the lowest skin-contact point (after `normalise`).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import numpy as np
import triangle
from matplotlib.path import Path as MplPath
from matplotlib.tri import Triangulation
from scipy import sparse
from scipy.interpolate import BSpline, CubicSpline
from scipy.sparse.linalg import splu
from scipy.spatial import cKDTree
from skimage import measure

# --------------------------------------------------------------------------- 2D SDF


def smin(a, b, k):
    """C2 cubic smooth minimum (Quilez). k = blend width in mm."""
    h = np.maximum(k - np.abs(a - b), 0.0) / k
    return np.minimum(a, b) - h**3 * k / 6.0


def smax(a, b, k):
    return -smin(-a, -b, k)


def smoothstep5(t):
    """C2 quintic smoothstep on [0,1], clamped."""
    t = np.clip(t, 0.0, 1.0)
    return t * t * t * (t * (6 * t - 15) + 10)


def closed_spline(ctrl, n=4000):
    """Periodic C2 cubic spline through control points; returns n evenly spaced samples."""
    P = np.asarray(ctrl, float)
    P = np.vstack([P, P[:1]])
    d = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    cs = CubicSpline(d, P, bc_type="periodic")
    t = np.linspace(0.0, d[-1], n, endpoint=False)
    return cs(t)


def mirrored_outline(half_pts, n=4000):
    """Symmetric closed outline from upper-half points ordered tail(+x, y=0) -> front(y=0).

    The first and last points must lie on y = 0; they are not duplicated.
    """
    H = np.asarray(half_pts, float)
    lower = H[-2:0:-1].copy()
    lower[:, 1] *= -1.0
    return closed_spline(np.vstack([H, lower]), n)


def polyline_sdf(poly, X, Y):
    tree = cKDTree(poly)
    pts = np.c_[X.ravel(), Y.ravel()]
    d, _ = tree.query(pts)
    inside = MplPath(poly).contains_points(pts)
    return np.where(inside, -d, d).reshape(X.shape)


@dataclass
class PlanformSpec:
    body_half: list            # upper-half outline control points, tail -> front
    window_r: float = 15.0     # crescent window radius (narrowest aperture)
    gap: float = 16.0          # front gap between the horn tips
    k_inner: float = 7.0       # rounding of the horn tips on the window side
    k_outer: float = 9.0       # rounding of the horn tips on the outside
    grid: float = 0.15         # SDF raster for contouring


def planform_sdf(spec: PlanformSpec, X, Y, body_poly):
    d_body = polyline_sdf(body_poly, X, Y)
    d_win = np.hypot(X, Y) - spec.window_r
    qx, qy = X, np.abs(Y) - spec.gap / 2.0          # half-infinite slot toward -x
    d_slot = np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0)
    d_key = smin(d_win, d_slot, spec.k_inner)
    return smax(d_body, -d_key, spec.k_outer)


def planform_boundary(spec: PlanformSpec, spacing=0.4):
    body = mirrored_outline(spec.body_half)
    lo = body.min(0) - 6
    hi = body.max(0) + 6
    xs = np.arange(lo[0], hi[0], spec.grid)
    ys = np.arange(lo[1], hi[1], spec.grid)
    X, Y = np.meshgrid(xs, ys)
    D = planform_sdf(spec, X, Y, body)
    cs = measure.find_contours(D, 0.0)
    c = max(cs, key=len)
    pts = np.c_[xs[0] + c[:, 1] * spec.grid, ys[0] + c[:, 0] * spec.grid]
    if np.allclose(pts[0], pts[-1]):
        pts = pts[:-1]
    # counter-clockwise
    area = 0.5 * np.sum(pts[:, 0] * np.roll(pts[:, 1], -1) - np.roll(pts[:, 0], -1) * pts[:, 1])
    if area < 0:
        pts = pts[::-1]
    # resample by arc length with a periodic spline (removes raster noise)
    seg = np.linalg.norm(np.diff(np.vstack([pts, pts[:1]]), axis=0), axis=1)
    s = np.r_[0.0, np.cumsum(seg)]
    cs = CubicSpline(s, np.vstack([pts, pts[:1]]), bc_type="periodic")
    L = s[-1]
    n = int(round(L / spacing))
    t = np.linspace(0, L, n, endpoint=False)
    B = cs(t)
    # start at the tail tip (max x near y = 0)
    i0 = np.argmax(B[:, 0] - 10.0 * np.abs(B[:, 1]))
    B = np.roll(B, -i0, axis=0)
    return B, body, (X, Y, D)


# --------------------------------------------------------------------------- FEM


def p1_stiffness_mass(V, F):
    p0, p1, p2 = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    e = [p2 - p1, p0 - p2, p1 - p0]
    A = 0.5 * ((p1 - p0)[:, 0] * (p2 - p0)[:, 1] - (p1 - p0)[:, 1] * (p2 - p0)[:, 0])
    n = len(V)
    rows, cols, vals = [], [], []
    for i in range(3):
        for j in range(3):
            rows.append(F[:, i])
            cols.append(F[:, j])
            vals.append((e[i] * e[j]).sum(1) / (4.0 * A))
    K = sparse.coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)).tocsr()
    m = np.zeros(n)
    for i in range(3):
        np.add.at(m, F[:, i], A / 3.0)
    return K, m, A


def dirichlet_solve(K, rhs, bnd, xb):
    n = K.shape[0]
    inner = np.setdiff1d(np.arange(n), bnd)
    x = np.zeros(n)
    x[bnd] = xb
    Kii = K[inner][:, inner].tocsc()
    r = rhs[inner] - K[inner][:, bnd] @ xb
    x[inner] = splu(Kii).solve(r)
    return x


def mean_value_map(V, F, bnd, ub):
    """Floater mean-value parametrisation: interior positions from boundary positions ub."""
    n = len(V)
    rows, cols, vals = [], [], []
    for a, b, c in [(0, 1, 2), (1, 2, 0), (2, 0, 1)]:
        i, j, k = F[:, a], F[:, b], F[:, c]
        vij, vik = V[j] - V[i], V[k] - V[i]
        lij, lik = np.linalg.norm(vij, axis=1), np.linalg.norm(vik, axis=1)
        ang = np.arccos(np.clip((vij * vik).sum(1) / (lij * lik), -1, 1))
        t = np.tan(ang / 2.0)
        rows += [i, i]
        cols += [j, k]
        vals += [t / lij, t / lik]
    W = sparse.coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)).tocsr()
    L = W - sparse.diags(np.asarray(W.sum(1)).ravel())
    inner = np.setdiff1d(np.arange(n), bnd)
    Lii = L[inner][:, inner].tocsc()
    lu = splu(Lii)
    U = np.zeros((n, 2))
    U[bnd] = ub
    for d in range(2):
        U[inner, d] = lu.solve(-(L[inner][:, bnd] @ ub[:, d]))
    return U


# --------------------------------------------------------------------------- stone spec


@dataclass
class StoneSpec:
    name: str
    plan: PlanformSpec
    pole: tuple                                   # planform point used as the top/bottom pole
    z_eq: Callable                                # silhouette height field      z_eq(x, y)
    h_top: Callable                               # target rise of the top above z_eq  h(x, y)
    base: Callable                                # underside target surface     base(x, y)
    fullness: float = 0.40                        # top profile f(psi) = (1+a)psi - a psi^3
    rb_lo: float = 2.2                            # bottom tuck width: smooth clamp range (mm)
    rb_hi: float = 7.0
    w_len: float = 8.0                            # edge -> interior blend length of the top scale
    lam: float = 2.5                              # screened-distance smoothing length
    n_u: int = 168
    n_v: int = 60
    mesh_area: float = 0.12
    notes: dict = field(default_factory=dict)


class Stone:
    """Holds the planform analysis, the sampled surface and the fitted B-spline."""

    def __init__(self, spec: StoneSpec, verbose=True):
        self.spec = spec
        self.verbose = verbose
        self._planform()
        self._fields()
        self._disk()

    # ---------------------------------------------------------------- planform & mesh
    def _planform(self):
        sp = self.spec
        B, body, raster = planform_boundary(sp.plan)
        self.boundary, self.body_outline, self.raster = B, body, raster
        nb = len(B)
        seg = np.c_[np.arange(nb), (np.arange(nb) + 1) % nb]
        t = triangle.triangulate({"vertices": B, "segments": seg}, f"pq30a{sp.mesh_area}Y")
        V, F = t["vertices"], t["triangles"]
        # Triangle keeps the input vertices first; with 'Y' none are added on the boundary.
        assert np.allclose(V[:nb], B)
        p0, p1, p2 = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
        a = (p1 - p0)[:, 0] * (p2 - p0)[:, 1] - (p1 - p0)[:, 1] * (p2 - p0)[:, 0]
        F[a < 0] = F[a < 0][:, ::-1]
        self.V, self.F, self.bnd = V, F, np.arange(nb)
        if self.verbose:
            print(f"[{sp.name}] planform: {nb} boundary pts, {len(V)} nodes, {len(F)} tris, "
                  f"perimeter {np.linalg.norm(np.diff(np.vstack([B, B[:1]]), axis=0), axis=1).sum():.1f} mm")

    # ---------------------------------------------------------------- FEM fields
    def _fields(self):
        sp = self.spec
        V, F, bnd = self.V, self.F, self.bnd
        K, m, A = p1_stiffness_mass(V, F)
        self.area = A.sum()
        # torsion function
        tau = dirichlet_solve(K, m, bnd, np.zeros(len(bnd)))
        self.tau, self.tau_max = tau, tau.max()
        self.tau_argmax = V[np.argmax(tau)]
        # screened-Poisson distance: (lam^2 K + M) U = 0, U = 1 on the edge, s = -lam log U
        Kd = (sp.lam**2) * K + sparse.diags(m)
        U = dirichlet_solve(Kd.tocsr(), np.zeros(len(V)), bnd, np.ones(len(bnd)))
        self.sdist = -sp.lam * np.log(np.clip(U, 1e-300, None))
        # boundary flux g = |grad tau| on the edge (per-triangle P1 gradient, averaged)
        p0, p1, p2 = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
        e = [p2 - p1, p0 - p2, p1 - p0]
        grad = np.zeros((len(F), 2))
        for i in range(3):
            rot = np.c_[-e[i][:, 1], e[i][:, 0]]
            grad += tau[F[:, i]][:, None] * rot
        grad /= (2.0 * A)[:, None]
        gmag = np.linalg.norm(grad, axis=1)
        acc = np.zeros(len(V))
        cnt = np.zeros(len(V))
        for i in range(3):
            np.add.at(acc, F[:, i], gmag)
            np.add.at(cnt, F[:, i], 1)
        gb = acc[bnd] / cnt[bnd]
        # smooth along the boundary (Gaussian, sigma ~ 2 mm)
        nb = len(bnd)
        sig = max(2.0 / 0.4, 1.0)
        k = np.exp(-0.5 * (np.arange(-int(4 * sig), int(4 * sig) + 1) / sig) ** 2)
        k /= k.sum()
        gb = np.convolve(np.r_[gb[-len(k):], gb, gb[:len(k)]], k, mode="same")[len(k):-len(k)]
        self.g_b = gb
        self.g = dirichlet_solve(K, np.zeros(len(V)), bnd, gb)
        if self.verbose:
            print(f"[{sp.name}] area {self.area:.0f} mm2, tau_max {self.tau_max:.1f} mm2 at "
                  f"({self.tau_argmax[0]:.1f},{self.tau_argmax[1]:.1f}), g in [{gb.min():.2f},{gb.max():.2f}]")

    # ---------------------------------------------------------------- disk map
    def _disk(self):
        sp = self.spec
        B = self.boundary
        seg = np.linalg.norm(np.diff(np.vstack([B, B[:1]]), axis=0), axis=1)
        s = np.r_[0.0, np.cumsum(seg)[:-1]]
        th = 2 * np.pi * s / seg.sum()
        ub = np.c_[np.cos(th), np.sin(th)]
        U = mean_value_map(self.V, self.F, self.bnd, ub)
        # Mobius re-centre so the chosen pole maps to the disk centre
        tri = Triangulation(self.V[:, 0], self.V[:, 1], self.F)
        w = self._bary_eval(tri, np.array([sp.pole]), U)[0]
        wc = complex(w[0], w[1])
        z = U[:, 0] + 1j * U[:, 1]
        z = (z - wc) / (1 - np.conj(wc) * z)
        z *= np.exp(-1j * np.angle(z[0]))           # boundary vertex 0 (tail tip) at phi = 0
        self.U = np.c_[z.real, z.imag]
        self.U[self.bnd] /= np.abs(z[self.bnd])[:, None]
        self.disk_tri = Triangulation(self.U[:, 0], self.U[:, 1], self.F)
        self.disk_finder = self.disk_tri.get_trifinder()
        self.mobius_shift = abs(wc)
        if self.verbose:
            print(f"[{sp.name}] disk map ok, Mobius shift |w_c| = {abs(wc):.3f}")

    @staticmethod
    def _bary_eval(tri, P, values):
        finder = tri.get_trifinder()
        t = finder(P[:, 0], P[:, 1])
        if np.any(t < 0):
            raise ValueError("point outside triangulation")
        T = tri.triangles[t]
        a, b, c = (np.c_[tri.x[T[:, i]], tri.y[T[:, i]]] for i in range(3))
        v0, v1, v2 = b - a, c - a, P - a
        d00, d01, d11 = (v0 * v0).sum(1), (v0 * v1).sum(1), (v1 * v1).sum(1)
        d20, d21 = (v2 * v0).sum(1), (v2 * v1).sum(1)
        den = d00 * d11 - d01 * d01
        l1 = (d11 * d20 - d01 * d21) / den
        l2 = (d00 * d21 - d01 * d20) / den
        l0 = 1 - l1 - l2
        vals = np.asarray(values)
        return l0[..., None] * vals[T[:, 0]] + l1[..., None] * vals[T[:, 1]] + l2[..., None] * vals[T[:, 2]] \
            if vals.ndim > 1 else l0 * vals[T[:, 0]] + l1 * vals[T[:, 1]] + l2 * vals[T[:, 2]]

    def disk_to_plan(self, W):
        """Map disk points W (N,2) to planform points and interpolated FEM fields."""
        nb = len(self.bnd)
        W = W * np.cos(np.pi / nb) * (1 - 1e-9)       # stay inside the inscribed polygon
        t = self.disk_finder(W[:, 0], W[:, 1])
        if np.any(t < 0):
            raise ValueError("disk point outside mesh")
        T = self.F[t]
        a, b, c = self.U[T[:, 0]], self.U[T[:, 1]], self.U[T[:, 2]]
        v0, v1, v2 = b - a, c - a, W - a
        d00, d01, d11 = (v0 * v0).sum(1), (v0 * v1).sum(1), (v1 * v1).sum(1)
        d20, d21 = (v2 * v0).sum(1), (v2 * v1).sum(1)
        den = d00 * d11 - d01 * d01
        l1 = (d11 * d20 - d01 * d21) / den
        l2 = (d00 * d21 - d01 * d20) / den
        l0 = 1 - l1 - l2

        def interp(f):
            if f.ndim > 1:
                return l0[:, None] * f[T[:, 0]] + l1[:, None] * f[T[:, 1]] + l2[:, None] * f[T[:, 2]]
            return l0 * f[T[:, 0]] + l1 * f[T[:, 1]] + l2 * f[T[:, 2]]

        return interp(self.V), interp(self.tau), interp(self.sdist), interp(self.g)

    # ---------------------------------------------------------------- heights
    def edge_terms(self, x, y, g):
        """Bottom tuck width rb and the top's edge scale H_edge (G2 matching).

        Natural (unclamped) tuck that matches the interior dome exactly:
            rb_nat = 3 Db^2 tau_max / (H_int^2 (1+a)^2 g)
        It is smoothly clamped to [rb_lo, rb_hi]; where clamping acts, the top's scale
        near the edge is changed instead so the sqrt(s) coefficients still agree:
            H_edge = Db sqrt(3 tau_max / (rb g)) / (1+a)
        """
        sp = self.spec
        a = sp.fullness
        Db = sp.z_eq(x, y) - sp.base(x, y)
        gg = np.clip(g, 1e-6, None)
        # thickness compensation: in a strip of half-width h, max psi = h / sqrt(2 tau_max)
        # and g = h, so H = h_top / f(psi_hat) makes thin horns reach their target height too.
        ph = np.clip(gg / np.sqrt(2.0 * self.tau_max), 0.26, 1.0)
        Hint = sp.h_top(x, y) / ((1 + a) * ph - a * ph**3)
        rb_nat = 3.0 * Db**2 * self.tau_max / (Hint**2 * (1 + a) ** 2 * gg)
        k = 0.8
        rb = smin(smax(rb_nat, sp.rb_lo, k), sp.rb_hi, k)
        H_edge = Db * np.sqrt(3.0 * self.tau_max / (rb * gg)) / (1 + a)
        return Db, rb, H_edge, Hint

    def heights(self, q, tau, sd, g, top: bool):
        """Top / bottom height at planform points q.

        bottom  z = z_eq - Db * R3(s~/rb),   R3(t) = sqrt(1 - (1-t)^3) ~ sqrt(3t)   (C2 at t=1)
        top     z = z_eq + H * f(psi),       psi = sqrt(tau/tau_max) ~ sqrt(g s / tau_max)
                H = H_int + (H_edge - H_int) * w(s~),  w = 1 at the edge, 0 beyond w_len
        Equal sqrt(s) coefficients at every silhouette point -> one C2 meridian curve -> G2.
        """
        sp = self.spec
        x, y = q[:, 0], q[:, 1]
        zeq = sp.z_eq(x, y)
        Db, rb, H_edge, Hint = self.edge_terms(x, y, g)
        if top:
            a = sp.fullness
            w = 1.0 - smoothstep5(sd / sp.w_len)
            H = Hint + (H_edge - Hint) * w
            psi = np.sqrt(np.clip(tau, 0, None) / self.tau_max)
            return zeq + H * ((1 + a) * psi - a * psi**3)
        t = np.clip(sd / rb, 0.0, 1.0)
        return zeq - Db * np.sqrt(1.0 - (1.0 - t) ** 3)

    def probe(self, P):
        """Top/bottom heights at arbitrary planform points P (N,2) -> (z_top, z_bot)."""
        tri = Triangulation(self.V[:, 0], self.V[:, 1], self.F)
        tau = self._bary_eval(tri, P, self.tau)
        sd = self._bary_eval(tri, P, self.sdist)
        g = self._bary_eval(tri, P, self.g)
        return self.heights(P, tau, sd, g, True), self.heights(P, tau, sd, g, False)

    def edge_report(self):
        """Silhouette diagnostics along the boundary: depth Db, tuck rb, edge radius r_e."""
        sp = self.spec
        B = self.boundary
        x, y = B[:, 0], B[:, 1]
        Db, rb, H_edge, Hint = self.edge_terms(x, y, self.g_b)
        return dict(Db=Db, rb=rb, r_e=1.5 * Db**2 / rb, zeq=sp.z_eq(x, y), H_edge=H_edge, H_int=Hint)

    # ---------------------------------------------------------------- sampling
    def sample(self, Nv=None, Nu=None):
        sp = self.spec
        Nv = Nv or 4 * sp.n_v
        Nu = Nu or 4 * sp.n_u
        v = np.linspace(0.0, np.pi, Nv)
        phi = np.linspace(0.0, 2 * np.pi, Nu, endpoint=False)
        VV, PP = np.meshgrid(v, phi, indexing="ij")
        rho = np.sin(VV)
        W = np.c_[(rho * np.cos(PP)).ravel(), (rho * np.sin(PP)).ravel()]
        q, tau, sd, g = self.disk_to_plan(W)
        top = (VV.ravel() >= np.pi / 2)
        z = np.empty(len(q))
        z[top] = self.heights(q[top], tau[top], sd[top], g[top], True)
        z[~top] = self.heights(q[~top], tau[~top], sd[~top], g[~top], False)
        P = np.c_[q, z].reshape(Nv, Nu, 3)
        self.samples = (v / np.pi, phi / (2 * np.pi), P)
        return self.samples

    def normalise(self):
        """Shift z so the lowest sampled point is z = 0 (skin-contact plane)."""
        vs, us, P = self.samples
        self.dz = -P[..., 2].min()
        P[..., 2] += self.dz
        return self.dz

    # ---------------------------------------------------------------- B-spline fit
    def fit(self, smooth=1e-4):
        sp = self.spec
        if not hasattr(self, "samples"):
            self.sample()
        vs, us, P = self.samples
        p = 3
        nu, nv = sp.n_u, sp.n_v
        # periodic basis in u (matches OCC's periodic convention, verified)
        tu = np.arange(-p, nu + p + 1) / nu
        Bx = BSpline.design_matrix(np.mod(us, 1.0), tu, p, extrapolate=False).toarray()
        Bu = np.zeros((len(us), nu))
        for j in range(Bx.shape[1]):
            Bu[:, j % nu] += Bx[:, j]
        # clamped basis in v
        inner = np.linspace(0, 1, nv - p + 1)
        tv = np.r_[[0.0] * p, inner, [1.0] * p]
        Bv = BSpline.design_matrix(vs, tv, p).toarray()

        def reg_solve(B, n, periodic):
            # LSQ with a small second-difference penalty (fairing)
            D = np.zeros((n, n))
            for i in range(n):
                if periodic or 1 <= i <= n - 2:
                    D[i, (i - 1) % n] += 1
                    D[i, i] -= 2
                    D[i, (i + 1) % n] += 1
            A = B.T @ B + smooth * len(B) / n * (D.T @ D)
            return np.linalg.solve(A, B.T)

        Pu = reg_solve(Bu, nu, True)        # (nu, Nu)
        Pv = reg_solve(Bv, nv, False)       # (nv, Nv)
        C = np.tensordot(np.tensordot(Pv, P, axes=(1, 0)), Pu, axes=(1, 1))   # (nv, Nu?) -> (nv, 3, nu)
        C = np.transpose(C, (0, 2, 1)).copy()                                   # (nv, nu, 3)
        # poles: collapse end rows, enforce tangent-plane (G1) on the next rows
        for r0, r1 in [(0, 1), (nv - 1, nv - 2)]:
            pole = P[0 if r0 == 0 else -1, 0]
            C[r0] = pole
            Q = C[r1] - pole
            _, _, vt = np.linalg.svd(Q - 0.0, full_matrices=False)
            nrm = vt[-1]
            C[r1] = C[r1] - np.outer(Q @ nrm, nrm)
        self.ctrl, self.tu, self.tv = C, tu, tv
        # fit error
        S = np.transpose(np.tensordot(np.tensordot(Bv, C, axes=(1, 0)), Bu, axes=(1, 1)), (0, 2, 1))
        err = np.linalg.norm(S - P, axis=2)
        self.fit_err = (err.max(), np.sqrt((err**2).mean()))
        if self.verbose:
            print(f"[{sp.name}] B-spline {nu}x{nv} ctrl, fit error max {err.max():.3f} mm, rms {self.fit_err[1]:.3f} mm")
        return C

    # ---------------------------------------------------------------- OCC
    def occ_surface(self):
        from OCP.collections import Array1_double, Array1_int, Array2_gp_Pnt
        from OCP.Geom import Geom_BSplineSurface
        from OCP.gp import gp_Pnt

        C = self.ctrl
        nv, nu, _ = C.shape
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

    def occ_solid(self):
        from OCP.BRep import BRep_Builder
        from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace
        from OCP.BRepCheck import BRepCheck_Analyzer
        from OCP.BRepGProp import BRepGProp
        from OCP.GProp import GProp_GProps
        from OCP.ShapeFix import ShapeFix_Solid
        from OCP.TopoDS import TopoDS_Shell, TopoDS_Solid

        surf = self.occ_surface()
        face = BRepBuilderAPI_MakeFace(surf, 1e-6).Face()
        bld = BRep_Builder()
        sh = TopoDS_Shell()
        bld.MakeShell(sh)
        bld.Add(sh, face)
        so = TopoDS_Solid()
        bld.MakeSolid(so)
        bld.Add(so, sh)
        fx = ShapeFix_Solid(so)
        fx.Perform()
        so = fx.Solid()
        props = GProp_GProps()
        BRepGProp.VolumeProperties_s(so, props)
        if props.Mass() < 0:
            so.Reverse()
            BRepGProp.VolumeProperties_s(so, props)
        ok = BRepCheck_Analyzer(so).IsValid()
        if self.verbose:
            print(f"[{self.spec.name}] OCC solid valid={ok}, volume {props.Mass() / 1000:.1f} cm3")
        self.volume = props.Mass()
        return so, ok
