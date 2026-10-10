"""
Concept-gate preliminary budgets for the vein-finder (see PHYSICS_NOTES.md).

SI units inside every function.  Run:  python concept_budget.py
Writes calc/out/concept_budget.json and prints a markdown summary.

Personal prototype for bench evaluation - NOT a medical device.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

# ------------------------------------------------------------------ physical constants
H_PLANCK_J_S = 6.62607015e-34
C_LIGHT_M_PER_S = 299_792_458.0
N_AVOGADRO_PER_MOL = 6.02214076e23
K_M_LM_PER_W = 683.0                     # photopic max luminous efficacy
MM = 1e-3                                # metres per millimetre

# CIE 1924 photopic V(lambda), 580-700 nm in 5 nm steps
V_LAMBDA_NM = np.arange(580, 701, 5)
V_LAMBDA = np.array([0.870, 0.8163, 0.757, 0.6949, 0.631, 0.5668, 0.503, 0.4412, 0.381, 0.321,
                     0.265, 0.217, 0.175, 0.1382, 0.107, 0.0816, 0.061, 0.04458, 0.032, 0.0232,
                     0.017, 0.01192, 0.00821, 0.005723, 0.004102])

# Hemoglobin molar extinction (Prahl compilation), cm^-1 / M
HB_EPS = {620: (942.0, 6509.6), 660: (319.6, 3226.56)}     # (HbO2, Hb)
HB_G_PER_L = 150.0
HB_G_PER_MOL = 64_500.0


# ------------------------------------------------------------------ LEDs (datasheet snapshots)
@dataclass(frozen=True)
class Led:
    name: str
    peak_nm: float
    fwhm_nm: float
    i_ref_A: float
    vf_ref_V: float
    p_opt_ref_W: float           # radiant flux at i_ref
    i_max_A: float
    v0_V: float                  # V_f(I) = v0 + rs*I through (i_ref, vf_ref)
    src_area_m2: float           # emitting die area assumed for radiance (conservative small)


def photon_flux_to_watts(umol_per_s: float, wavelength_nm: float) -> float:
    e_photon_J = H_PLANCK_J_S * C_LIGHT_M_PER_S / (wavelength_nm * 1e-9)
    return umol_per_s * 1e-6 * N_AVOGADRO_PER_MOL * e_photon_J


def luminous_efficacy(peak_nm: float, fwhm_nm: float) -> float:
    """lm per radiant W for a Gaussian spectrum (CIE 1924 V(lambda))."""
    lam = np.linspace(peak_nm - 3 * fwhm_nm, peak_nm + 3 * fwhm_nm, 601)
    sig = fwhm_nm / 2.3548
    s = np.exp(-0.5 * ((lam - peak_nm) / sig) ** 2)
    v = np.interp(lam, V_LAMBDA_NM, V_LAMBDA, left=V_LAMBDA[0], right=0.0)
    return K_M_LM_PER_W * np.trapezoid(v * s, lam) / np.trapezoid(s, lam)


# Lumileds LUXEON SunPlus 2835 Deep Red L1SP-DRD0002800000: 0.82 umol/s, 2.08 V @ 120 mA, 300 mA max
DEEP_RED = Led("L1SP-DRD0002800000 (660 nm)", 660.0, 20.0, 0.120, 2.08,
               photon_flux_to_watts(0.82, 660.0), 0.300, 1.90, 0.30e-6)
# Lumileds LUXEON 2835 Red-Orange L128-RNG1003500000: 27 lm, 2.10 V @ 120 mA, 340 mA max
_RO_K = luminous_efficacy(622.0, 17.0)
RED_ORANGE = Led("L128-RNG1003500000 (~620 nm)", 622.0, 17.0, 0.120, 2.10, 27.0 / _RO_K, 0.340, 1.92, 0.30e-6)


def led_p_opt(led: Led, i_A):
    return led.p_opt_ref_W * np.asarray(i_A) / led.i_ref_A


def led_vf(led: Led, i_A):
    rs = (led.vf_ref_V - led.v0_V) / led.i_ref_A
    return led.v0_V + rs * np.asarray(i_A)


def led_i_for_p(led: Led, p_W):
    return np.asarray(p_W) * led.i_ref_A / led.p_opt_ref_W


# ------------------------------------------------------------------ tissue optics
@dataclass(frozen=True)
class Tissue:
    name: str
    musp_per_mm: float = 2.0
    blood_frac: float = 0.02
    so2: float = 0.75
    mua_bg_per_mm: float = 0.015
    f_mel: float = 0.02
    d_epi_mm: float = 0.08
    n: float = 1.40


def mua_per_mm(t: Tissue, wl_nm: int) -> float:
    eps_o, eps_d = HB_EPS[wl_nm]
    c_M = HB_G_PER_L / HB_G_PER_MOL
    mua_blood_per_cm = 2.303 * c_M * (t.so2 * eps_o + (1 - t.so2) * eps_d)
    return t.mua_bg_per_mm + t.blood_frac * mua_blood_per_cm / 10.0


def epidermis_T(t: Tissue, wl_nm: float) -> float:
    mua_mel_per_mm = 6.6e11 * wl_nm ** -3.33 / 10.0 * t.f_mel
    return float(np.exp(-mua_mel_per_mm * t.d_epi_mm))


def groenhuis_A(n_rel: float) -> float:
    r_d = -1.440 / n_rel**2 + 0.710 / n_rel + 0.668 + 0.0636 * n_rel
    return (1 + r_d) / (1 - r_d)


def farrell_R(rho_m, mua_per_m: float, musp_per_m: float, n_rel: float = 1.4):
    """Diffuse reflectance per unit area [1/m^2] at distance rho [m] (Farrell 1992)."""
    mutp = mua_per_m + musp_per_m
    ap = musp_per_m / mutp
    z0 = 1.0 / mutp
    zb = 2.0 * groenhuis_A(n_rel) / (3.0 * mutp)
    mueff = np.sqrt(3.0 * mua_per_m * mutp)
    rho = np.asarray(rho_m, float)
    r1 = np.sqrt(z0**2 + rho**2)
    r2 = np.sqrt((z0 + 2 * zb) ** 2 + rho**2)
    return ap / (4 * np.pi) * (z0 * (mueff + 1 / r1) * np.exp(-mueff * r1) / r1**2
                               + (z0 + 2 * zb) * (mueff + 1 / r2) * np.exp(-mueff * r2) / r2**2)


def farrell_Rd_total(mua_per_m: float, musp_per_m: float, n_rel: float = 1.4) -> float:
    ap = musp_per_m / (mua_per_m + musp_per_m)
    s = np.sqrt(3 * (1 - ap))
    return 0.5 * ap * np.exp(-s) * (1 + np.exp(-4.0 / 3.0 * groenhuis_A(n_rel) * s))


def led_ring(n: int, r_mm: float, gap_half_angle_deg: float):
    """LED skin-entry points on an arc around the window, symmetric, avoiding the front gap."""
    a = np.radians(np.linspace(-(180 - gap_half_angle_deg), 180 - gap_half_angle_deg, n))
    return np.c_[r_mm * np.cos(a), r_mm * np.sin(a)] * MM          # +x = tail, gap at -x


def window_exitance(src_m, p_inj_W, t: Tissue, wl_nm: int, window_r_mm=15.0, n_grid=121):
    """Exitance map [W/m^2] over the window disk, plus summary stats."""
    mua = mua_per_mm(t, wl_nm) / MM
    musp = t.musp_per_mm / MM
    T2 = epidermis_T(t, wl_nm) ** 2
    g = np.linspace(-window_r_mm, window_r_mm, n_grid) * MM
    X, Y = np.meshgrid(g, g)
    inside = np.hypot(X, Y) <= window_r_mm * MM
    M = np.zeros_like(X)
    for (sx, sy) in src_m:
        M += p_inj_W * T2 * farrell_R(np.hypot(X - sx, Y - sy), mua, musp, t.n)
    M[~inside] = np.nan
    r = np.hypot(X, Y)
    centre = float(np.nanmean(M[r < 3 * MM]))
    rim = float(np.nanmean(M[(r > (window_r_mm - 3) * MM) & inside & (X > 0)]))   # back half rim
    return dict(mean=float(np.nanmean(M)), centre=centre, rim=rim, map=M)


# ------------------------------------------------------------------ thermal
SKIN_K_W_PER_MK = 0.37
PERFUSION_PER_S = 1.0e-3
BLOOD_RHO_C_J_PER_M3K = 1060.0 * 3600.0
PERFUSION_LEN_M = np.sqrt(SKIN_K_W_PER_MK / (PERFUSION_PER_S * BLOOD_RHO_C_J_PER_M3K))


def spot_rise_self(p_abs_W, a_m=2.0 * MM, k=SKIN_K_W_PER_MK):
    """Centre rise of a hemispherical uniform source under an insulated surface."""
    return 3.0 * np.asarray(p_abs_W) / (4.0 * np.pi * k * a_m)


def spot_rise_neighbours(p_abs_W, src_m, k=SKIN_K_W_PER_MK, L_p=PERFUSION_LEN_M):
    """Largest neighbour contribution over the ring (same bank lit)."""
    d = np.linalg.norm(src_m[:, None, :] - src_m[None, :, :], axis=-1)
    np.fill_diagonal(d, np.inf)
    contrib = (np.exp(-d / L_p) / (2 * np.pi * k * d)).sum(1)
    return float(np.asarray(p_abs_W) * contrib.max())


# ------------------------------------------------------------------ electrical
@dataclass(frozen=True)
class Power:
    eta_boost: float = 0.85
    v_fb_V: float = 0.204          # TPS61169 feedback reference
    p_quiescent_W: float = 0.020   # MCU active + status LED + charger idle
    cap_mAh: float = 600.0         # Jauch LP503040JH
    v_nom_V: float = 3.7
    usable: float = 0.90


def bank_power(led: Led, n: int, i_A: float, pw: Power):
    p_out = i_A * (n * led_vf(led, i_A) + pw.v_fb_V)
    p_in = p_out / pw.eta_boost
    p_bat = p_in + pw.p_quiescent_W
    p_opt = n * led_p_opt(led, i_A)
    heat_led = n * i_A * led_vf(led, i_A) - p_opt
    return dict(p_out=p_out, p_in=p_in, p_bat=p_bat, p_opt=p_opt, heat_led=heat_led,
                heat_driver=p_in - p_out, i_bat_A=p_bat / pw.v_nom_V)


def runtime_h(p_bat_W: float, pw: Power) -> float:
    return pw.cap_mAh * 1e-3 * pw.v_nom_V * pw.usable / p_bat_W


# ------------------------------------------------------------------ study
SKINS = {
    "light (I-II)": Tissue("light", f_mel=0.02),
    "medium (III-IV)": Tissue("medium", f_mel=0.10),
    "dark (V-VI)": Tissue("dark", f_mel=0.30),
}
SKIN_T0_C = 33.5
T_LIMIT_C = 41.0
DEVICE_SHARE_K = 1.5            # device self-heating seen at the contact face (lumped, see notes)
COUPLING = 0.75
AMBIENT_LX = 500.0
SHADE = 0.5
SKIN_VIS_REFL = {"light (I-II)": 0.45, "medium (III-IV)": 0.30, "dark (V-VI)": 0.12}
RING_R_MM = 20.0                # skin entry radius (LED pockets just outside a ~3 mm lip)
GAP_HALF_DEG = 38.0


def study(n_per_bank=6):
    pw = Power()
    src = led_ring(n_per_bank, RING_R_MM, GAP_HALF_DEG)
    rows = []
    for bank, led, wl in (("deep red 660", DEEP_RED, 660), ("red-orange 620", RED_ORANGE, 620)):
        K = luminous_efficacy(led.peak_nm, led.fwhm_nm)
        for skin, t in SKINS.items():
            mua = mua_per_mm(t, wl) / MM
            musp = t.musp_per_mm / MM
            T2 = epidermis_T(t, wl) ** 2
            Rd = farrell_Rd_total(mua, musp, t.n)
            f_abs = 1.0 - Rd * T2
            # thermal cap: self + neighbours + device share <= limit
            budget_K = T_LIMIT_C - SKIN_T0_C - DEVICE_SHARE_K
            per_W = spot_rise_self(1.0) + spot_rise_neighbours(1.0, src)
            p_abs_max = budget_K / per_W
            p_inj_max = p_abs_max / f_abs
            p_opt_max = p_inj_max / COUPLING
            i_max = float(min(led_i_for_p(led, p_opt_max), led.i_max_A))
            win = window_exitance(src, p_inj_max, t, wl)
            Lv = {k: K * win[k] / np.pi for k in ("centre", "rim", "mean")}
            L_amb = AMBIENT_LX * SKIN_VIS_REFL[skin] * SHADE / np.pi
            pb = bank_power(led, n_per_bank, i_max, pw)
            rows.append(dict(bank=bank, skin=skin, mueff_per_mm=round(float(np.sqrt(3 * mua * (mua + musp)) * MM), 3),
                             T_epi2=round(T2, 3), Rd=round(Rd, 3), p_opt_per_led_mW=round(p_opt_max * 1e3, 1),
                             i_per_led_mA=round(i_max * 1e3, 1), L_rim_nit=round(Lv["rim"], 1),
                             L_centre_nit=round(Lv["centre"], 2), L_ambient_nit=round(L_amb, 1),
                             rim_over_ambient=round(Lv["rim"] / L_amb, 2), centre_over_ambient=round(Lv["centre"] / L_amb, 3),
                             bank_p_bat_W=round(pb["p_bat"], 3), bank_heat_W=round(pb["heat_led"] + pb["heat_driver"], 3),
                             runtime_h=round(runtime_h(pb["p_bat"], pw), 1)))
    return rows


def ieec62471_prelim(d_m=0.200):
    """Bare LED at its full rated current (worst case), preliminary.

    Limits as reproduced from IEC 62471:2006 Table 6 by secondary sources (to verify
    against the standard): retinal thermal L_R <= 28000/alpha (exempt), blue light
    L_B <= 100 W/m2/sr (exempt); for small sources (alpha < 0.011 rad) blue light is
    assessed as irradiance, exempt E_B <= 0.01 W/m2 (100 J/m2 in 10 000 s).
    B(lambda) = 0.001 and R(lambda) = 1.0 for 600-700 nm."""
    out = {}
    for led in (DEEP_RED, RED_ORANGE):
        p_max = float(led_p_opt(led, led.i_max_A))
        L = p_max / (np.pi * led.src_area_m2)
        alpha = 2 * np.sqrt(led.src_area_m2 / np.pi) / d_m
        alpha_eff = max(alpha, 0.0017)
        E = (p_max / np.pi) / d_m**2                      # on-axis irradiance of a Lambertian emitter
        out[led.name] = dict(p_opt_at_imax_mW=round(p_max * 1e3), alpha_mrad=round(alpha * 1e3, 2),
                             radiance_W_m2_sr=round(L), L_R_over_exempt=round(L / (28000.0 / alpha_eff), 4),
                             small_source=bool(alpha < 0.011),
                             E_B_W_m2=round(0.001 * E, 5), E_B_over_exempt=round(0.001 * E / 0.01, 3))
    return out


def main():
    res = dict(per_led=dict(deep_red=dict(p_opt_ref_mW=round(DEEP_RED.p_opt_ref_W * 1e3, 1),
                                          wpe_ref=round(DEEP_RED.p_opt_ref_W / (DEEP_RED.i_ref_A * DEEP_RED.vf_ref_V), 3),
                                          K_lm_per_W=round(luminous_efficacy(660, 20), 1)),
                            red_orange=dict(p_opt_ref_mW=round(RED_ORANGE.p_opt_ref_W * 1e3, 1),
                                            wpe_ref=round(RED_ORANGE.p_opt_ref_W / (RED_ORANGE.i_ref_A * RED_ORANGE.vf_ref_V), 3),
                                            K_lm_per_W=round(_RO_K, 1))),
               perfusion_length_mm=round(PERFUSION_LEN_M / MM, 1),
               study_6=study(6), study_8=study(8), iec62471=ieec62471_prelim())
    out = Path(__file__).with_name("out")
    out.mkdir(exist_ok=True)
    (out / "concept_budget.json").write_text(json.dumps(res, indent=2))
    print(json.dumps(res["per_led"], indent=1))
    for n in (6, 8):
        print(f"\n### {n} LEDs per bank (one bank lit), each LED at its 41 C-limited current")
        print("| bank | skin | mu_eff /mm | I/LED mA | P_opt/LED mW | rim nit | centre nit | ambient nit | rim/amb | centre/amb | P_bat W | runtime h |")
        print("|---|---|---|---|---|---|---|---|---|---|---|---|")
        for r in res[f"study_{n}"]:
            print(f"| {r['bank']} | {r['skin']} | {r['mueff_per_mm']} | {r['i_per_led_mA']} | {r['p_opt_per_led_mW']} | "
                  f"{r['L_rim_nit']} | {r['L_centre_nit']} | {r['L_ambient_nit']} | {r['rim_over_ambient']} | "
                  f"{r['centre_over_ambient']} | {r['bank_p_bat_W']} | {r['runtime_h']} |")
    print("\nIEC 62471 (bare LED at I_max, preliminary):", json.dumps(res["iec62471"], indent=1))


if __name__ == "__main__":
    main()
