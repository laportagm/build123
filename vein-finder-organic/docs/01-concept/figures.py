"""
Concept-board figures (static, light mode, for the PDF one-pager):

  fig_window_profile.png  luminance across the window (y at x = 0) for two LED entry radii
                          and two skin types, against the shaded ambient reflection
  fig_plan.png            option A plan: key dimensions + packaging (cell, PCB ring, LEDs,
                          switch, seam, USB-C, magnets)
  fig_section.png         option A centre-line section: stone, waterline, internal stack

Palette: dataviz reference instance (blue #2a78d6 / orange #eb6834 validated, text inks,
surface #fcfcfb).  Identity is never colour-alone (dash + direct labels + legend).
"""
import sys
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "calc"))
sys.path.insert(0, str(ROOT / "cad" / "concepts"))
sys.path.insert(0, str(ROOT / "cad" / "stone"))

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#9a9993"
GRID = "#e6e5e1"
BLUE = "#2a78d6"
ORANGE = "#eb6834"
STONE = "#cfc9bf"
SOLE = "#2b2b2b"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2, "axes.facecolor": SURFACE, "figure.facecolor": SURFACE,
    "savefig.facecolor": SURFACE, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False,
})


def fig_window_profile(out):
    import concept_budget as cb
    fig, ax = plt.subplots(figsize=(5.4, 3.0))
    y = np.linspace(-14.9, 14.9, 241)
    for r_entry, col in ((20.0, BLUE), (17.5, ORANGE)):
        src = cb.led_ring(6, r_entry, cb.GAP_HALF_DEG)
        for skin, ls in (("light (I-II)", "-"), ("dark (V-VI)", (0, (4, 2)))):
            t = cb.SKINS[skin]
            led = cb.RED_ORANGE
            mua = cb.mua_per_mm(t, 620) / cb.MM
            musp = t.musp_per_mm / cb.MM
            T2 = cb.epidermis_T(t, 620) ** 2
            Rd = cb.farrell_Rd_total(mua, musp, t.n)
            p_abs_max = (cb.T_LIMIT_C - cb.SKIN_T0_C - cb.DEVICE_SHARE_K) / (cb.spot_rise_self(1.0) + cb.spot_rise_neighbours(1.0, src))
            p_inj = p_abs_max / (1 - Rd * T2)
            K = cb.luminous_efficacy(led.peak_nm, led.fwhm_nm)
            M = np.zeros_like(y)
            for (sx, sy) in src:
                M += p_inj * T2 * cb.farrell_R(np.hypot(0 - sx, y * cb.MM - sy), mua, musp, t.n)
            L = K * M / np.pi
            ax.plot(y, L, color=col, lw=2, ls=ls, label=f"LEDs at r = {r_entry:g} mm, {skin.split()[0]} skin")
    for skin, refl in (("light", 0.45), ("dark", 0.12)):
        La = cb.AMBIENT_LX * refl * cb.SHADE / np.pi
        ax.axhline(La, color=MUTED, lw=1, ls=":")
        ax.text(0, La * 1.12, f"room light reflected, {skin} skin (500 lx, half-shaded)", ha="center", va="bottom",
                color=INK2, fontsize=7.2, bbox=dict(fc=SURFACE, ec="none", pad=0.3))
    ax.set_yscale("log")
    ax.set_ylim(0.02, 3000)
    ax.set_xlim(-15, 15)
    ax.set_xlabel("position across the window, mm (0 = centre)")
    ax.set_ylabel("luminance, cd/m² (log)")
    ax.set_title("Red-orange bank at its 41 °C-limited current: the window is rim-lit",
                 loc="left", fontsize=9.5, color=INK)
    ax.legend(loc="upper center", fontsize=7.2, ncol=2, bbox_to_anchor=(0.5, -0.22))
    fig.tight_layout()
    fig.savefig(out, dpi=220)
    plt.close(fig)


def _stone(key="A"):
    from build_concept import build
    st, solid, top, sole, info = build(key, verbose=False)
    return st, solid, info


def fig_plan(out, st, info):
    from options import BUTTON_A
    fig, ax = plt.subplots(figsize=(6.4, 4.3))
    B = np.vstack([st.boundary, st.boundary[:1]])
    ax.fill(B[:, 0], B[:, 1], color=STONE, zorder=1)
    ax.plot(B[:, 0], B[:, 1], color=INK2, lw=1.0, zorder=2)
    # battery bay (Jauch LP503040JH, 5.4 x 30.5 x 42 mm, across), PCB ring around it
    ax.add_patch(Rectangle((24.0, -21.0), 30.5, 42.0, fc="#ffffff", ec=INK, lw=1.0, zorder=3))
    ax.text(39.25, 0, "600 mAh LiPo\n30.5 × 42 × 5.4\n(on the sole,\nin a PCB cut-out)", ha="center", va="center",
            fontsize=7, color=INK, zorder=4)
    # LED ring (6 + 6 interleaved), entry radius 17.5 mm
    a = np.radians(np.linspace(-142, 142, 12))
    for i, ang in enumerate(a):
        col = BLUE if i % 2 == 0 else ORANGE
        ax.add_patch(Rectangle((17.9 * np.cos(ang) - 1.4, 17.9 * np.sin(ang) - 1.75), 2.8, 3.5,
                               angle=0, fc=col, ec="none", zorder=4))
    th = np.linspace(-np.pi * 0.83, np.pi * 0.83, 200)
    ax.plot(15 * np.cos(th), 15 * np.sin(th), color=INK, lw=0.6, ls=(0, (2, 2)), zorder=3)
    # switch, seam, USB-C, magnets
    ax.add_patch(Rectangle((21.0 - 3, -3), 6, 6, fc="#ffffff", ec=INK, lw=1.0, zorder=5))
    ax.text(21.0, -4.0, "switch\n(top side)", ha="center", va="top", fontsize=6.2, color=INK2, zorder=5)
    ts = np.radians(np.linspace(-44, 44, 60))
    ax.plot(18.6 * np.cos(ts), 18.6 * np.sin(ts), color="#eda100", lw=1.4, zorder=6)
    ax.add_patch(Rectangle((57.4, -4.5), 4.6, 9.0, fc=SOLE, ec="none", zorder=5))
    ax.text(64.5, 0, "USB-C\n(on the\nwaterline)", ha="left", va="center", fontsize=6.5, color=INK2)
    for (mx, my) in [(-4.0, 24.2), (-4.0, -24.2), (58.0, 13.0), (58.0, -13.0)]:
        ax.add_patch(Circle((mx, my), 3.2, fc="#ffffff", ec=INK2, lw=0.8, zorder=5))
    # dimensions
    xmin, xmax = st.boundary[:, 0].min(), st.boundary[:, 0].max()
    ymin, ymax = st.boundary[:, 1].min(), st.boundary[:, 1].max()
    def dim(x0, y0, x1, y1, txt, off=(0, 0), rot=0):
        ax.annotate("", (x0, y0), (x1, y1), arrowprops=dict(arrowstyle="<->", color=INK2, lw=0.8), zorder=7)
        ax.text((x0 + x1) / 2 + off[0], (y0 + y1) / 2 + off[1], txt, ha="center", va="center", fontsize=7.5,
                color=INK, rotation=rot, bbox=dict(fc=SURFACE, ec="none", pad=0.6), zorder=8)
    dim(xmin, ymin - 5, xmax, ymin - 5, f"{info['size'][0]:.1f}")
    dim(xmax + 13, ymin, xmax + 13, ymax, f"{info['size'][1]:.1f}", rot=90)
    dim(-15, 0, 15, 0, "Ø30 window", off=(0, 2.4))
    gx = st.boundary[st.boundary[:, 0] < -10]
    gy = gx[np.abs(gx[:, 1]) < 10]
    ax.annotate("", (-18, -8.0), (-18, 8.0), arrowprops=dict(arrowstyle="<->", color=INK2, lw=0.8), zorder=7)
    ax.text(-20.0, 0, "16\ngap", ha="right", va="center", fontsize=7.5, color=INK)
    ax.set_aspect("equal")
    ax.set_xlim(-38, 80)
    ax.set_ylim(-38, 34)
    ax.axis("off")
    # legend (identity never colour-alone: labels)
    ax.plot([], [], "s", color=BLUE, label="660 nm deep-red LED, bank 1 (PCB underside)")
    ax.plot([], [], "s", color=ORANGE, label="620 nm red-orange LED, bank 2 (PCB underside)")
    ax.plot([], [], "-", color="#eda100", lw=1.4, label="hairline status seam (top surface)")
    ax.plot([], [], "o", mfc="#ffffff", mec=INK2, label="magnet pairs Ø6.35 (indicative)")
    ax.legend(loc="upper left", fontsize=7, ncol=2, bbox_to_anchor=(0.0, 1.02))
    fig.tight_layout()
    fig.savefig(out, dpi=220)
    plt.close(fig)


def fig_section(out, st, info):
    from options import Z_PART
    zp = Z_PART + st.dz
    x = np.linspace(15.0, 62.6, 500)
    P = np.c_[x, np.zeros_like(x)]
    from matplotlib.path import Path as MP
    ins = MP(st.boundary).contains_points(P, radius=-1e-3)
    zt = np.full_like(x, np.nan)
    zb = np.full_like(x, np.nan)
    zt[ins], zb[ins] = st.probe(P[ins])
    zt += st.dz
    zb += st.dz
    # front horn section line y = 0 is the window: show the back half (window rim -> tail)
    fig, ax = plt.subplots(figsize=(6.4, 2.6))
    ax.fill_between(x, np.maximum(zb, zp), zt, color=STONE, lw=0, zorder=1)
    ax.fill_between(x, zb, np.minimum(zt, zp), where=zb < zp, color=SOLE, lw=0, zorder=1)
    ax.plot(x, zt, color=INK2, lw=0.9)
    ax.plot(x, zb, color=INK2, lw=0.9)
    ax.axhline(zp, color="#eda100", lw=1.0, ls=(0, (5, 3)))
    ax.text(63.5, zp, f"waterline / parting plane  z = {zp:.1f}", va="center", fontsize=7, color=INK2)
    # internal stack (schematic): PCB ring, switch, cell, wall
    ax.add_patch(Rectangle((16.8, zp), 7.0, 1.0, fc="#1baf7a", ec="none", zorder=3))
    ax.add_patch(Rectangle((54.8, zp), 7.0, 1.0, fc="#1baf7a", ec="none", zorder=3))
    ax.text(20.3, zp + 0.5, "PCB", ha="center", va="center", fontsize=6, color="#ffffff", zorder=4)
    ax.add_patch(Rectangle((24.0, zp + 0.4), 30.5, 5.4, fc="#ffffff", ec=INK, lw=0.8, zorder=3))
    ax.text(39.25, zp + 3.1, "LiPo 5.4 mm", ha="center", va="center", fontsize=7, color=INK, zorder=4)
    ax.add_patch(Rectangle((18.0, zp + 1.0), 6.0, 3.5, fc="#ffffff", ec=INK, lw=0.8, zorder=3))
    ax.add_patch(Rectangle((21.0 - 1.75, zp + 4.5), 3.5, 3.8, fc="#ffffff", ec=INK, lw=0.8, zorder=3))
    ax.text(21.0, zp + 2.75, "switch", ha="center", va="center", fontsize=5.6, color=INK, zorder=4)
    ax.annotate("index-finger dimple\n= flexing membrane", (20.5, np.interp(20.5, x, zt)), (6, 24),
                fontsize=7, color=INK2, arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.7))
    ax.annotate("black optical sole\n(light-tight, skin side)", (40, zp - 1.0), (66, -3.0),
                fontsize=7, color=INK2, arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.7))
    ax.annotate("skin contact\n(concave R120)", (35, np.nanmin(zb)), (2, -3.5),
                fontsize=7, color=INK2, arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.7))
    ax.set_aspect("equal")
    ax.set_xlim(0, 92)
    ax.set_ylim(-6, 29)
    ax.set_xlabel("x along the centre line, mm (window rim at 15)")
    ax.set_ylabel("z, mm")
    ax.set_title(f"Option A centre-line section — {info['size'][2]:.1f} mm tall; cell sits on the sole inside the PCB ring",
                 loc="left", fontsize=9, color=INK)
    fig.tight_layout()
    fig.savefig(out, dpi=220)
    plt.close(fig)


if __name__ == "__main__":
    out = HERE / "figures"
    out.mkdir(exist_ok=True)
    fig_window_profile(out / "fig_window_profile.png")
    st, solid, info = _stone("A")
    fig_plan(out / "fig_plan.png", st, info)
    fig_section(out / "fig_section.png", st, info)
    print("figures written to", out)
