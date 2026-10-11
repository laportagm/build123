"""
Gate-2 verification on the real geometry.

  walls        normal wall thickness of the top shell, sampled over the whole skin
  overhang     outer-skin facets in print orientation (must be support-free) and the
               interior area that needs (internal, build-plate-only) supports
  interference pairwise intersection volume of every part and stand-in
  mass         printed parts (PETG) + bought parts
  membrane     button press force: linear shallow-shell Ritz model of the real skin
  magnets      closure pull of the four N42 magnet pairs (coaxial current-loop model)

Units: mm, N, g.  Writes build/device/checks.json.
"""
from __future__ import annotations

import json
import math
import time
from itertools import combinations
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree
from scipy.special import ellipe, ellipk

import params as P
from skin import BUTTON_XY

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "build" / "device"

PETG = dict(E=2.0e3, nu=0.38, rho=1.27e-3)      # E in N/mm^2 (MPa), rho in g/mm^3
MU0 = 4e-7 * math.pi


# ----------------------------------------------------------------------------- volume
def mesh_volume(shape, lin=0.01, ang=0.05):
    """Volume from a fine closed triangulation (mm^3).  build123d's default `.volume` uses
    OCC's fixed-order Gauss integration, which is ~2 % off on these large trimmed B-spline
    faces (checked: outer skin 59 183 default vs 60 546 adaptive vs 60 538 mesh)."""
    from studio import tessellate
    V, N, F = tessellate(shape, lin_defl=lin, ang_defl=ang)
    t = V[F]
    return float(abs(np.einsum("ij,ij->i", t[:, 0], np.cross(t[:, 1], t[:, 2])).sum() / 6.0))


# ----------------------------------------------------------------------------- walls
def wall_map(parts, n_u=1344, n_v=700):
    """Normal thickness of the top shell at outer-skin samples above the waterline.

    For each outer point the nearest point of the inner (cavity) surface samples is found;
    the distance is the local wall.  Regions inside the seam slot and the magnet bosses
    are reported separately (they are designed thin / thick)."""
    sk, lay = parts.sk, parts.lay
    us = np.linspace(0, 1, n_u, endpoint=False)
    vs = np.linspace(0.40, 1.0, n_v)
    S, N = sk.outer(us, vs)
    zp = sk.z_part
    S = S.reshape(-1, 3)
    S = S[S[:, 2] > zp + 0.3]
    _, _, Pn, _ = sk.cavity_samples(__import__("parts").wall_thickness, zp - 1.2, n_u=1344, n_rows=720)
    inner = Pn.reshape(-1, 3)
    inner = inner[inner[:, 2] > zp - 0.2]
    d, _ = cKDTree(inner).query(S)
    xy = S[:, :2]
    from shapely.geometry import Point
    in_slot = np.array([lay.slot_2d.buffer(0.6).contains(Point(*p)) for p in xy])
    r_but = np.sqrt(((xy[:, 0] - BUTTON_XY[0]) / P.BUTTON_AXES[0]) ** 2 + (xy[:, 1] / P.BUTTON_AXES[1]) ** 2)
    in_button = r_but < 1.0 + 2.2 * P.MEMBRANE_TAPER / min(P.BUTTON_AXES)
    near_usb = (xy[:, 0] > P.USB_X_FACE - P.USB_L - 1.0) & (np.abs(xy[:, 1]) < P.USB_LAND_HW + 1.0)
    general = ~(in_slot | in_button | near_usb)
    res = dict(general_min=float(d[general].min()), general_p01=float(np.percentile(d[general], 0.1)),
               general_median=float(np.median(d[general])),
               button_min=float(d[in_button].min()),
               n_samples=int(len(d)))
    i = np.argmin(np.where(general, d, 99))
    res["general_min_at"] = S[i].round(2).tolist()
    return res, (S, d)


def probe_vertical(shape, x, y):
    """Material intervals of `shape` along the vertical line through (x, y): [(z0, z1), ...]."""
    import build123d as bd
    rod = bd.Pos(x, y, -5) * bd.Cylinder(0.01, 50, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    r = shape & rod
    if r is None:
        return []
    out = []
    for so in r.solids():
        bb = so.bounding_box()
        out.append((round(bb.min.Z, 3), round(bb.max.Z, 3)))
    return sorted(out)


def seam_probe(parts, shell):
    """Vertical material extent through the seam slot vs just beside it (60 deg wall)."""
    res = {}
    for a in (0.0, 30.0, -40.0):
        th = math.radians(a)
        for tag, r in (("slot", P.SEAM_R), ("beside", P.SEAM_R + 1.2)):
            iv = probe_vertical(shell, r * math.cos(th), r * math.sin(th))
            res[f"{tag}_{a:+.0f}deg"] = iv
    return res


def mirror_symmetry(shapes):
    """Every part is symmetric about y = 0: compare the two halves' volumes (catches silent
    boolean failures, which are rarely symmetric)."""
    import build123d as bd
    out = {}
    for n in ("top_shell", "sole", "seam_mask", "bridge", "pcb"):
        s = shapes[n]
        a = s & (bd.Pos(0, 50, 0) * bd.Box(300, 100, 100))
        b = s & (bd.Pos(0, -50, 0) * bd.Box(300, 100, 100))
        va = 0.0 if a is None else mesh_volume(a)
        vb = 0.0 if b is None else mesh_volume(b)
        out[n] = dict(y_pos=round(va, 2), y_neg=round(vb, 2), rel_diff=round(abs(va - vb) / max(va, vb, 1e-9), 5))
    return out


def magnet_cover(parts, shell):
    """PETG left between each top-magnet pocket and the outer skin (min over the pocket rim)."""
    sk = parts.sk
    zp = sk.z_part
    out = []
    S, N = sk.outer(np.linspace(0, 1, 1344, endpoint=False), np.linspace(0.40, 1.0, 900))
    pts = S.reshape(-1, 3)
    tree = cKDTree(pts)
    for m in parts.lay.magnets:
        z_top = zp + P.MAG_PROUD + P.MAG_GAP + P.MAG_H_TOP + 0.06
        r = (P.MAG_D + P.MAG_POCKET_CLEAR) / 2
        th = np.linspace(0, 2 * np.pi, 72, endpoint=False)
        rim = np.c_[m["x"] + r * np.cos(th), m["y"] + r * np.sin(th), np.full_like(th, z_top)]
        rim2 = np.c_[m["x"] + r * np.cos(th), m["y"] + r * np.sin(th), np.full_like(th, z_top - P.MAG_H_TOP)]
        d1, _ = tree.query(np.vstack([rim, rim2]))
        out.append(round(float(d1.min()), 2))
    return out


# ----------------------------------------------------------------------------- overhang
def overhang(shape, z_bed, flip, outer_face_ids=None, limit=45.0):
    """Facet overhang in print orientation.  flip=True for parts printed upside down."""
    from studio import tessellate
    V, N_, F = tessellate(shape, lin_defl=0.03, ang_defl=0.15)
    tri = V[F]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    area = 0.5 * np.linalg.norm(n, axis=1)
    sv = np.einsum("ij,ij->i", tri[:, 0], np.cross(tri[:, 1], tri[:, 2])).sum() / 6.0
    if sv < 0:
        n = -n
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-15
    nz = -n[:, 2] if flip else n[:, 2]
    zc = tri[:, :, 2].mean(axis=1)
    h = (z_bed - zc) if flip else (zc - z_bed)           # height above the bed
    on_bed = h < 0.05
    ang = np.degrees(np.arcsin(np.clip(-nz, 0, 1)))       # 0 = vertical wall, 90 = ceiling
    over = (nz < 0) & (ang > limit) & ~on_bed
    return dict(V=V, F=F, area=area, over=over, ang=ang, nz=nz)


# ----------------------------------------------------------------------------- interference
def interference(shapes, skip=()):
    rows = []
    names = list(shapes)
    for a, b in combinations(names, 2):
        if (a, b) in skip or (b, a) in skip:
            continue
        sa, sb = shapes[a], shapes[b]
        if sa is None or sb is None:
            continue
        ba, bb = sa.bounding_box(), sb.bounding_box()
        if (ba.max.X < bb.min.X or bb.max.X < ba.min.X or ba.max.Y < bb.min.Y or bb.max.Y < ba.min.Y
                or ba.max.Z < bb.min.Z or bb.max.Z < ba.min.Z):
            continue
        try:
            r = sa & sb
            v = 0.0 if (r is None or len(r.solids()) == 0) else mesh_volume(r, lin=0.02, ang=0.1)
        except Exception as e:  # noqa: BLE001
            v = float("nan")
            print("intersection failed", a, b, e)
        if v > 1e-3 or v != v:
            rows.append((a, b, round(v, 4)))
    return rows


# ----------------------------------------------------------------------------- membrane
def _poly_basis(px, py):
    """Even polynomial terms x^i y^j (i, j even), i + j <= deg."""
    return [(i, j) for i in range(0, px + 1, 2) for j in range(0, py + 1, 2) if i + j <= max(px, py)]


def membrane_force(parts, gap=P.SWITCH_GAP, travel=0.25, f_switch=(0.98, 1.57), patch_r=3.5,
                   deg_w=8, deg_uv=7, n_grid=181, curv_scale=1.0, t_scale=1.0):
    """Finger force to actuate the hidden switch.

    Linear shallow-shell (Marguerre) Ritz model over an elliptical domain that covers the
    thin skin and its taper and is clamped where the wall is back at 1.8 mm:
      bending:   D = E t^3 / 12(1-nu^2),  t = t(x, y) from the real thickness field
      membrane:  A = E t / (1-nu^2),  eps = (u_x + z0_x w_x, v_y + z0_y w_y,
                 u_y + v_x + z0_x w_y + z0_y w_x),  z0 = local skin shape about its tangent plane
    The finger load is a uniform patch of radius patch_r at the centre; the switch needs the
    centre to move gap + travel; the switch's own force adds on top.
    Returns the centre stiffness (plate-only and shell) and the press-force range."""
    from parts import wall_thickness
    sk = parts.sk
    E, nu = PETG["E"], PETG["nu"]
    a0, b0 = P.BUTTON_AXES
    ext = 1.0 + 2.2 * P.MEMBRANE_TAPER / min(a0, b0)        # domain: where t is back to ~1.8
    a, b = a0 * ext, b0 * ext
    # local skin shape: fit z(x, y) around the button in the tangent frame at the centre
    S, N = sk.outer(np.linspace(0, 1, 1344, endpoint=False), np.linspace(0.80, 1.0, 600))
    pts = S.reshape(-1, 3)
    c = np.array([BUTTON_XY[0], BUTTON_XY[1]])
    sel = np.hypot(pts[:, 0] - c[0], (pts[:, 1] - c[1])) < max(a, b) + 1.0
    p = pts[sel]
    dx, dy = p[:, 0] - c[0], p[:, 1] - c[1]
    A_ = np.c_[np.ones_like(dx), dx, dy, dx * dx, dx * dy, dy * dy, dx**3, dx * dx * dy, dx * dy * dy, dy**3]
    co = np.linalg.lstsq(A_, p[:, 2], rcond=None)[0]
    g = co[1:3]
    nrm = np.array([-g[0], -g[1], 1.0])
    nrm /= np.linalg.norm(nrm)
    e1 = np.array([1.0, 0.0, g[0]])
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(nrm, e1)
    P0 = np.array([c[0], c[1], co[0]])
    loc = np.c_[(p - P0) @ e1, (p - P0) @ e2, (p - P0) @ nrm]
    X, Y, Z = loc.T
    B = np.c_[X * X, X * Y, Y * Y, X**3, X * X * Y, X * Y * Y, Y**3, X**4, Y**4, X * X * Y * Y]
    cz = np.linalg.lstsq(B, Z, rcond=None)[0] * curv_scale
    # grid over the domain (local tangent coordinates ~ plan coordinates; slope ~ 10 deg)
    xs = np.linspace(-a, a, n_grid)
    ys = np.linspace(-b, b, n_grid)
    XX, YY = np.meshgrid(xs, ys, indexing="ij")
    rho2 = (XX / a) ** 2 + (YY / b) ** 2
    inside = rho2 < 1.0
    dA = (xs[1] - xs[0]) * (ys[1] - ys[0])
    # thickness from the real field (plan coordinates)
    T = wall_thickness(XX * e1[0] + c[0], YY + c[1]) * t_scale
    # z0 derivatives
    z0x = 2 * cz[0] * XX + cz[1] * YY + 3 * cz[3] * XX**2 + 2 * cz[4] * XX * YY + cz[5] * YY**2 + 4 * cz[7] * XX**3 + 2 * cz[9] * XX * YY**2
    z0y = cz[1] * XX + 2 * cz[2] * YY + cz[4] * XX**2 + 2 * cz[5] * XX * YY + 3 * cz[6] * YY**2 + 4 * cz[8] * YY**3 + 2 * cz[9] * XX**2 * YY
    xn, yn = XX / a, YY / b
    phi = (1.0 - rho2)
    # w = phi^2 * x^i y^j ; u = phi * x^i y^j (u odd in x), v = phi * x^i y^j (v odd in y)
    # derivatives evaluated analytically via the product rule
    phx, phy = -2 * XX / a**2, -2 * YY / b**2
    phxx, phyy = -2 / a**2, -2 / b**2

    def mono(i, j, xv=xn, yv=yn):
        m = xv**i * yv**j
        mx = (i * xv ** max(i - 1, 0) * yv**j / a) if i > 0 else 0 * xv
        my = (j * xv**i * yv ** max(j - 1, 0) / b) if j > 0 else 0 * xv
        mxx = (i * (i - 1) * xv ** max(i - 2, 0) * yv**j / a**2) if i > 1 else 0 * xv
        myy = (j * (j - 1) * xv**i * yv ** max(j - 2, 0) / b**2) if j > 1 else 0 * xv
        mxy = (i * j * xv ** max(i - 1, 0) * yv ** max(j - 1, 0) / (a * b)) if (i > 0 and j > 0) else 0 * xv
        return m, mx, my, mxx, myy, mxy

    wt = _poly_basis(deg_w, deg_w)
    Wb = []   # (w_x, w_y, w_xx, w_yy, w_xy, w) for each basis
    for (i, j) in wt:
        m, mx, my, mxx, myy, mxy = mono(i, j)
        f = phi**2
        fx, fy = 2 * phi * phx, 2 * phi * phy
        fxx, fyy, fxy = 2 * phx**2 + 2 * phi * phxx, 2 * phy**2 + 2 * phi * phyy, 2 * phx * phy
        Wb.append((f * mx + fx * m, f * my + fy * m,
                   f * mxx + 2 * fx * mx + fxx * m, f * myy + 2 * fy * my + fyy * m,
                   f * mxy + fx * my + fy * mx + fxy * m, f * m))
    ub = [(i, j) for i in range(1, deg_uv + 1, 2) for j in range(0, deg_uv + 1, 2) if i + j <= deg_uv]
    vb = [(i, j) for i in range(0, deg_uv + 1, 2) for j in range(1, deg_uv + 1, 2) if i + j <= deg_uv]
    Ub, Vb = [], []
    for (i, j) in ub:
        m, mx, my, *_ = mono(i, j)
        Ub.append((phi * mx + phx * m, phi * my + phy * m))
    for (i, j) in vb:
        m, mx, my, *_ = mono(i, j)
        Vb.append((phi * mx + phx * m, phi * my + phy * m))
    nw, nu_, nv_ = len(Wb), len(Ub), len(Vb)
    ntot = nw + nu_ + nv_
    msk = inside.astype(float) * dA
    D = E * T**3 / (12 * (1 - nu**2))
    Am = E * T / (1 - nu**2)

    def assemble(shell=True):
        K = np.zeros((ntot, ntot))
        # strain vectors for each dof: bending curvatures and membrane strains (linear in dofs)
        kxx = [w[2] for w in Wb]
        kyy = [w[3] for w in Wb]
        kxy = [w[4] for w in Wb]
        ex = [z0x * w[0] for w in Wb] + [u[0] for u in Ub] + [0 * phi for _ in Vb]
        ey = [z0y * w[1] for w in Wb] + [0 * phi for _ in Ub] + [v[1] for v in Vb]
        gxy = [z0x * w[1] + z0y * w[0] for w in Wb] + [u[1] for u in Ub] + [v[0] for v in Vb]
        for p_ in range(nw):
            for q in range(p_, nw):
                val = np.sum(D * (kxx[p_] * kxx[q] + kyy[p_] * kyy[q] + nu * (kxx[p_] * kyy[q] + kyy[p_] * kxx[q])
                                  + 2 * (1 - nu) * kxy[p_] * kxy[q]) * msk)
                K[p_, q] = K[q, p_] = val
        if shell:
            for p_ in range(ntot):
                for q in range(p_, ntot):
                    val = np.sum(Am * (ex[p_] * ex[q] + ey[p_] * ey[q] + nu * (ex[p_] * ey[q] + ey[p_] * ex[q])
                                       + 0.5 * (1 - nu) * gxy[p_] * gxy[q]) * msk)
                    K[p_, q] += val
                    if q != p_:
                        K[q, p_] += val
        return K

    load = (np.hypot(XX, YY) < patch_r).astype(float)
    load_area = np.sum(load * dA)
    f = np.zeros(ntot)
    for k, w in enumerate(Wb):
        f[k] = np.sum(w[5] * load * dA) / load_area          # unit total force
    centre = np.array([w[5][n_grid // 2, n_grid // 2] for w in Wb])
    res = {}
    for name, shell in (("plate", False), ("shell", True)):
        K = assemble(shell)
        if not shell:
            K = K[:nw, :nw]
            sol = np.linalg.solve(K + 1e-12 * np.eye(nw), f[:nw])
            wc = centre @ sol
        else:
            sol = np.linalg.solve(K + 1e-12 * np.eye(ntot), f)
            wc = centre @ sol[:nw]
        res[f"k_centre_{name}_N_per_mm"] = 1.0 / wc
    k = res["k_centre_shell_N_per_mm"]
    res["domain_semi_axes_mm"] = [round(a, 2), round(b, 2)]
    res["skin_curvatures_1_per_mm"] = [round(2 * cz[0], 4), round(2 * cz[2], 4)]
    res["press_force_N"] = [round(k * (gap + travel) + fs, 2) for fs in f_switch]
    res["press_force_note"] = (f"k x (gap {gap} + travel {travel} mm) + switch {f_switch} N; "
                               f"finger patch r = {patch_r} mm; E = {E} MPa")
    # sensitivity to the printed skin thickness (+-0.05 mm)
    return res


# ----------------------------------------------------------------------------- magnets
def loop_force(a, b, z, I1, I2):
    """Axial force between two coaxial circular loops (radii a, b; separation z), N.
    Positive = attraction for co-directed currents."""
    m = 4 * a * b / ((a + b) ** 2 + z**2)
    pre = MU0 * I1 * I2 * z / math.sqrt((a + b) ** 2 + z**2)
    return pre * (-ellipk(m) + (a * a + b * b + z * z) / ((a - b) ** 2 + z * z) * ellipe(m))


def magnet_pull(d=P.MAG_D, h1=P.MAG_H_SOLE, h2=P.MAG_H_TOP, gap=P.MAG_GAP, Br=1.29, n=60):
    """Pull between two coaxial, axially magnetised discs (N42: Br ~ 1.29 T), face gap in mm.
    Each magnet = a solenoid sheet with surface current K = Br / mu0."""
    K = Br / MU0
    r = d / 2 * 1e-3
    z1 = (np.arange(n) + 0.5) / n * h1 * 1e-3
    z2 = (h1 + gap) * 1e-3 + (np.arange(n) + 0.5) / n * h2 * 1e-3
    I1 = K * h1 * 1e-3 / n
    I2 = K * h2 * 1e-3 / n
    F = 0.0
    for za in z1:
        for zb in z2:
            F += loop_force(r, r, zb - za, I1, I2)
    return F


# ----------------------------------------------------------------------------- mass
def mass_budget(shapes, parts):
    lay = parts.lay
    petg = PETG["rho"]
    m = {}
    # printed: shells print as perimeters (solid); the sole/bridge/mask as walls + 30 % infill;
    # the volume-weighted fill factors below are conservative upper bounds.
    vol = {n: mesh_volume(shapes[n]) for n in ("top_shell", "sole", "seam_mask", "bridge")}
    m["top_shell"] = vol["top_shell"] * petg * 0.98
    m["sole"] = vol["sole"] * petg * 0.80
    m["seam_mask"] = vol["seam_mask"] * petg * 1.0
    m["bridge"] = vol["bridge"] * petg * 0.85
    m["pcb_fr4"] = lay.pcb.area * P.PCB_T * 1.85e-3 + lay.pcb.area * 0.07 * 8.96e-3 * 0.6
    m["battery"] = 12.1            # Jauch LP503040JH, datasheet typ. (verify at the electronics gate)
    m["magnets"] = len(lay.magnets) * math.pi * (P.MAG_D / 2) ** 2 * (P.MAG_H_SOLE + P.MAG_H_TOP) * 7.5e-3
    m["leds_ics_passives"] = 3.0   # 12 LEDs, MCU, driver, inductor, charger, connectors: estimate
    m["usb_receptacle"] = 1.0
    m["switch_wire_tape"] = 1.0
    m = {k: round(v, 2) for k, v in m.items()}
    m["total"] = round(sum(m.values()), 1)
    return m


# ----------------------------------------------------------------------------- main
def run(parts, shapes):
    t0 = time.time()
    rep = {}
    walls, _ = wall_map(parts)
    rep["walls"] = walls
    rep["magnet_cover_mm"] = magnet_cover(parts, shapes["top_shell"])
    rep["mirror_symmetry"] = mirror_symmetry(shapes)
    rep["seam_probe_z_intervals"] = seam_probe(parts, shapes["top_shell"])
    print("[checks] walls", walls, round(time.time() - t0, 1), "s", flush=True)
    zp = parts.sk.z_part
    import sys
    sys.path.insert(0, str(ROOT / "render"))
    S, _ = parts.sk.outer(np.linspace(0, 1, 2688, endpoint=False), np.linspace(0.0, 1.0, 1800))
    skin_tree = cKDTree(S.reshape(-1, 3))
    for name, flip in (("top_shell", False), ("sole", True)):
        o = overhang(shapes[name], zp, flip)
        cen = o["V"][o["F"]].mean(axis=1)
        dist, _ = skin_tree.query(cen)
        on_skin = dist < 0.08                       # facet lies on the cosmetic outer skin
        down = o["nz"] < 0
        rep[f"overhang_{name}"] = dict(
            skin_max_deg=round(float(o["ang"][down & on_skin].max()), 1) if (down & on_skin).any() else 0.0,
            skin_area_over_45_mm2=round(float(o["area"][o["over"] & on_skin].sum()), 2),
            interior_area_over_45_mm2=round(float(o["area"][o["over"] & ~on_skin].sum()), 1),
            note="skin = cosmetic outer surface (must be support-free); interior = supported from the build plate")
    print("[checks] overhang done", round(time.time() - t0, 1), "s", flush=True)
    rep["membrane"] = membrane_force(parts)
    print("[checks] membrane", rep["membrane"], round(time.time() - t0, 1), "s", flush=True)
    f1 = magnet_pull()
    rep["magnets"] = dict(pair_pull_N=round(f1, 2), total_pull_N=round(4 * f1, 1),
                          model="coaxial current loops, N42 Br 1.29 T, gap %.2f mm" % P.MAG_GAP)
    rep["mass_g"] = mass_budget(shapes, parts)
    skip = {("top_shell", "magnets"), ("sole", "magnets")}
    rep["interference"] = interference(shapes, skip=())
    print("[checks] interference", rep["interference"], round(time.time() - t0, 1), "s", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "checks.json").write_text(json.dumps(rep, indent=1, default=float))
    return rep
