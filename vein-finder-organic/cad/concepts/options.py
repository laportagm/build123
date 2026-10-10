"""
Concept-gate form options.  Each option is a StoneSpec: a planform + smooth height
fields.  Shared constraints (from the brief):

  envelope   ~ 90 x 58 x 26 mm
  window     30 mm aperture (radius 15) centred at the origin, 16 mm front gap
  underside  gently concave across the width (cylinder R_C) to saddle a forearm
  parting    one planar "waterline" at Z_PART, below the silhouette, so both halves
             print outer-surface-up with no supports on cosmetic faces

Coordinates: +x toward the tail, window centre at (0, 0), z up, z = 0 at the lowest
skin-contact point (after normalisation).
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "stone"))
from organic import PlanformSpec, StoneSpec, smoothstep5, smin, smax  # noqa: E402

# ----------------------------------------------------------------------------- shared
R_C = 120.0         # underside concavity radius across the width ("gently concave")
Y_RAIL = 22.0       # contact rails: lowest skin-contact lines, |y| = 22
Z_RAIL = 0.5        # rail height before normalisation
SOLE_MIN = 1.6      # minimum sole (bottom part) thickness


CURL = 0.0085       # beyond the rails the underside curls up (C2 cubic) so the flanks stay soft


def base_cyl(x, y):
    """Underside target: cylinder concave across the width between the rails, curling up outside."""
    out = np.maximum(np.abs(y) - Y_RAIL, 0.0)
    return Z_RAIL + (Y_RAIL**2 - y**2) / (2.0 * R_C) + CURL * out**3


Z_PART = float(base_cyl(0.0, 0.0)) + SOLE_MIN + 0.2   # waterline / parting plane (pre-normalisation)


def ring_r(x, y):
    return np.hypot(x, y)


def gauss_dome(x, y, xc, sx_front, sx_back, sy, lo, hi, x_mid=None, w=18.0):
    """Smooth anisotropic bump; the x-width blends from sx_front to sx_back (C-infinity)."""
    x_mid = xc if x_mid is None else x_mid
    sx = sx_front + (sx_back - sx_front) * 0.5 * (1.0 + np.tanh((x - x_mid) / w))
    return lo + (hi - lo) * np.exp(-((x - xc) / sx) ** 2 - (y / sy) ** 2)


def ellipsoid_dome(x, y, xc, ax_front, ax_back, ay, lo, hi, w=20.0):
    """Convex cap sqrt(1 - u^2) with a smoothly varying front/back semi-axis.

    Concave as a function everywhere it is positive, so the stone stays convex in
    elevation (pebbles are convex).  Semi-axes are chosen larger than the planform."""
    ax = ax_front + (ax_back - ax_front) * 0.5 * (1.0 + np.tanh((x - xc) / w))
    u2 = ((x - xc) / ax) ** 2 + (y / ay) ** 2
    q = 1.0 - u2
    eps = 0.12
    soft = 0.5 * (q + np.sqrt(q * q + eps * eps))     # C-infinity, ~q inside, ->0+ outside
    return lo + (hi - lo) * np.sqrt(soft)


def zeq_window_to_outer(x, y, z_win, z_out, r0=16.0, r1=27.0):
    """Silhouette height: low at the window (crisp bored rim), different at the outer flank."""
    return z_win + (z_out - z_win) * smoothstep5((ring_r(x, y) - r0) / (r1 - r0))


# ----------------------------------------------------------------------------- A: Pebble
# One convex dome with the crescent bored through its nose.  Thin lens-like outer edge,
# crisp functional window lip, horns that taper toward the gap.  ~23 mm.
def A_zeq(x, y):
    return zeq_window_to_outer(x, y, 4.9, 5.4)


BUTTON_A = (20.5, 0.0)      # hidden button: index-finger dimple just behind the window


def A_h(x, y):
    dome = ellipsoid_dome(x, y, xc=27.0, ax_front=50.0, ax_back=66.0, ay=46.0, lo=5.2, hi=16.9)
    dimple = 0.55 * np.exp(-((x - BUTTON_A[0]) ** 2 + (y - BUTTON_A[1]) ** 2) / (2 * 5.2**2))
    return dome - dimple


OPTION_A = StoneSpec(
    name="A_pebble",
    plan=PlanformSpec(
        body_half=[(62.6, 0.0), (61.9, 11.6), (58.9, 20.6), (52.0, 26.4), (41.0, 28.9),
                   (29.0, 29.4), (16.0, 29.4), (4.0, 29.2), (-8.0, 28.4), (-18.0, 25.4),
                   (-24.8, 19.6), (-27.9, 10.5), (-28.4, 0.0)],
        k_inner=5.6, k_outer=5.5),
    pole=(34.0, 0.0),
    z_eq=A_zeq, h_top=A_h, base=base_cyl, fullness=0.10,
    notes=dict(title="Pebble", tag="one convex dome; crescent bored through its nose; battery under the crown"),
)


# ----------------------------------------------------------------------------- B: Crescent
# A true crescent: the horns taper to soft points that reach toward each other, the
# crown rides just behind the window and the back sweeps down to a teardrop tail.
def B_zeq(x, y):
    return zeq_window_to_outer(x, y, 5.0, 5.6)


def B_h(x, y):
    return ellipsoid_dome(x, y, xc=18.0, ax_front=46.0, ax_back=60.0, ay=34.0, lo=4.4, hi=17.4)


OPTION_B = StoneSpec(
    name="B_crescent",
    plan=PlanformSpec(
        body_half=[(63.5, 0.0), (61.6, 6.6), (55.5, 12.6), (45.5, 18.6), (33.0, 24.4),
                   (19.0, 28.6), (5.0, 29.4), (-6.0, 28.2), (-15.0, 24.8), (-21.6, 19.6),
                   (-25.6, 13.8), (-27.4, 8.6), (-27.8, 0.0)],
        k_inner=4.0, k_outer=4.0),
    pole=(28.0, 0.0),
    z_eq=B_zeq, h_top=B_h, base=base_cyl, fullness=0.12,
    notes=dict(title="Crescent", tag="tapered horns; crown behind the window; teardrop tail"),
)


# ----------------------------------------------------------------------------- C: Hagstone
# Flat lens with a wide worn crater: the top dishes toward the window from far out, so
# the opening is the hero (a "hag stone").  ~20 mm, broad horns that slope inward.
def C_zeq(x, y):
    return zeq_window_to_outer(x, y, 4.8, 5.6, r0=17.0, r1=30.0)


def C_h(x, y):
    r = ring_r(x, y)
    crater = smoothstep5((r - 9.0) / 34.0)
    lens = ellipsoid_dome(x, y, xc=22.0, ax_front=70.0, ax_back=56.0, ay=40.0, lo=0.0, hi=1.0)
    return 4.2 + 11.0 * crater * lens


OPTION_C = StoneSpec(
    name="C_hagstone",
    plan=PlanformSpec(
        body_half=[(60.5, 0.0), (59.0, 11.5), (53.5, 21.0), (43.5, 27.4), (29.5, 29.8),
                   (15.0, 30.0), (0.0, 29.8), (-12.0, 28.2), (-21.0, 23.8), (-26.8, 16.6),
                   (-29.3, 8.4), (-29.7, 0.0)],
        k_inner=4.5, k_outer=6.0),
    pole=(30.0, 0.0),
    z_eq=C_zeq, h_top=C_h, base=base_cyl, fullness=0.10,
    notes=dict(title="Hagstone", tag="flat lens; worn crater funnel; the opening is the hero"),
)

OPTIONS = {"A": OPTION_A, "B": OPTION_B, "C": OPTION_C}
