"""Pinning tests for concept_budget.py (closed-form ground truth).  Run: python -m pytest -q"""
import numpy as np
import pytest

import concept_budget as cb

MM = cb.MM


def test_photon_energy_660nm():
    # 1 umol/s at 660 nm.  N_A h c = 0.119626565638697009 J m/mol exactly (SI-defined h, c, N_A;
    # evaluated with 40-digit decimal arithmetic) -> 0.18125237217984395 W
    assert cb.photon_flux_to_watts(1.0, 660.0) == pytest.approx(0.18125237217984395, rel=1e-12)


def test_deep_red_datasheet_conversion():
    # 0.82 umol/s at 660 nm -> ~148.6 mW; wall-plug efficiency at 120 mA / 2.08 V ~ 0.60
    assert cb.DEEP_RED.p_opt_ref_W == pytest.approx(0.1486, rel=2e-3)
    assert 0.5 < cb.DEEP_RED.p_opt_ref_W / (0.120 * 2.08) < 0.7


@pytest.mark.parametrize("mua,musp", [(0.01, 1.0), (0.04, 2.0), (0.1, 3.0)])
def test_farrell_integral_matches_closed_form(mua, musp):
    mua_m, musp_m = mua / MM, musp / MM
    rho = np.concatenate([np.linspace(0, 2 * MM, 20001), np.linspace(2 * MM, 300 * MM, 200001)[1:]])
    integ = np.trapezoid(cb.farrell_R(rho, mua_m, musp_m) * 2 * np.pi * rho, rho)
    assert integ == pytest.approx(cb.farrell_Rd_total(mua_m, musp_m), rel=2e-3)


def test_farrell_no_absorption_limit():
    # a' -> 1  =>  all injected light eventually leaves: R_d -> 1
    assert cb.farrell_Rd_total(1e-9, 1.0 / MM) == pytest.approx(1.0, abs=1e-3)


def test_sphere_heating_closed_form_by_quadrature():
    # Centre rise of a uniformly heated sphere (power 2P, infinite medium) by integrating the
    # point-source Green's function 1/(4 pi k r) over the volume == 3P/(4 pi k a).
    P, k, a = 0.02, cb.SKIN_K_W_PER_MK, 2.0 * MM
    q = 2 * P / (4 / 3 * np.pi * a**3)
    r = np.linspace(1e-9, a, 200001)
    dT = np.trapezoid(q * 4 * np.pi * r**2 / (4 * np.pi * k * r), r)
    assert dT == pytest.approx(cb.spot_rise_self(P, a, k), rel=1e-6)


def test_boost_energy_balance_and_signs():
    pw = cb.Power()
    b = cb.bank_power(cb.DEEP_RED, 6, 0.030, pw)
    assert b["p_in"] - b["p_out"] - b["heat_driver"] == pytest.approx(0.0, abs=1e-15)
    for k in ("p_out", "p_in", "p_bat", "p_opt", "heat_led", "heat_driver"):
        assert b[k] >= 0
    assert b["p_opt"] < 6 * 0.030 * cb.led_vf(cb.DEEP_RED, 0.030)   # cannot emit more than it consumes


def test_runtime_units():
    pw = cb.Power(cap_mAh=1000.0, v_nom_V=4.0, usable=1.0)
    assert cb.runtime_h(4.0, pw) == pytest.approx(1.0)                # 4 Wh / 4 W = 1 h


def test_luminous_efficacy_bounds():
    # a narrow line at 620 nm must give K close to 683 * V(620) = 260 lm/W
    assert cb.luminous_efficacy(620.0, 0.5) == pytest.approx(683 * 0.381, rel=5e-3)
    assert cb.luminous_efficacy(660.0, 20.0) < cb.luminous_efficacy(622.0, 17.0)


def test_window_symmetry():
    src = cb.led_ring(6, 20.0, 38.0)
    w = cb.window_exitance(src, 0.03, cb.Tissue("t"), 660)
    M = w["map"]
    assert np.allclose(M, M[::-1, :], equal_nan=True, rtol=1e-9)      # mirror in y
