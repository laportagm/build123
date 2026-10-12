"""
Gate-3 electronics budget with the chosen parts' datasheet values.

    python budget.py  ->  budget.json (+ the tables quoted in electronics.md)

Personal prototype for bench evaluation - NOT a medical device.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "calc"))
from electronics_budget import Budget, DriverIC, Inductor, LedPart, boost_point, ntc_resolution, run, standby_current  # noqa: E402

DRV = DriverIC(name="TPS61169DCKR", v_fb=0.204, f_sw=1.2e6, i_lim=1.2, v_ovp=36.0, vin_min=2.7,
               i_q_on=0.30e-3, i_q_off=2e-6, pwm_analog_band=(5e3, 100e3),
               source="TI SNVSA40B / ZHCSD24B via TI document viewer: VREF 188/204/220 mV, 1.2 MHz, "
                      "ILIM 1.2 A min, OVP 36/37.5/39 V, Iq 0.3 mA typ, shutdown 1 uA typ / 2 uA max")
LED_A = LedPart(name="SunLED XZM2MR55W-3 (660 nm)", vf_at=(2.1, 0.020), i_max=0.030,
                source="Digi-Key listing / SunLED base datasheet: Vf 2.1 V typ (2.5 max) @ 20 mA, 30 mA DC max")
LED_B = LedPart(name="SunLED XZM2CRK55W-3 (625 nm)", vf_at=(2.2, 0.020), i_max=0.030,
                source="Digi-Key listing: Vf 2.2 V typ @ 20 mA; SunLED datasheet copy: 30 mA DC max")
IND = Inductor(name="Sunlord SWPA4018S100MT", L=10e-6, i_sat=1.30, dcr=0.18,
               source="Sunlord SWPA4018S datasheet (alfatec mirror): 10 uH, Isat 1.30 A typ, DCR 0.18 ohm typ")

R_SET = 8.2
R_TOL = 0.01
I_CEIL = (0.188 / (R_SET * (1 + R_TOL)), 0.204 / R_SET, 0.220 / (R_SET * (1 - R_TOL)))
# firmware caps per LED (A): bank A from the concept's thermal study (dark skin, 41 C limit:
# 23.2 mA); bank B is held by the hardware ceiling (its thermal cap, 30 mA, is higher)
CAP_A = 0.023
CAP_B = I_CEIL[1]


def main():
    b = Budget(driver=DRV, led_a=LED_A, led_b=LED_B, ind=IND, i_cap_a=CAP_A, i_cap_b=CAP_B,
               v_d_schottky=0.35, i_mcu_active=1.5e-3, i_seam=4.0e-3)
    res = run(b)
    res["sense_resistor"] = dict(R_ohm=R_SET, tol=R_TOL, ceiling_mA=[round(i * 1e3, 1) for i in I_CEIL],
                                 note="I = VREF / R at 100 % CTRL duty; VREF 188/204/220 mV")
    res["duty_for_caps"] = dict(bank_A=round(CAP_A / I_CEIL[1], 3), bank_B=round(CAP_B / I_CEIL[1], 3),
                                worst_case_A_mA=round(CAP_A / I_CEIL[1] * I_CEIL[2] * 1e3, 1),
                                note="duty = cap / typical ceiling; worst case = same duty at VREF max, R min")
    # USB charging (BQ21040, K_ISET 490/540/590 A.ohm, R_ISET 2.2 k)
    ich = [k / 2200.0 for k in (490, 540, 590)]
    res["charger"] = dict(i_charge_mA=[round(i * 1e3) for i in ich], c_rate=[round(i / 0.6, 2) for i in ich],
                          i_term_mA=round(0.1 * ich[1] * 1e3, 1), i_pre_mA=round(0.2 * ich[1] * 1e3, 1),
                          t_full_h_estimate=round(0.8 * 0.6 / ich[1] + 1.0, 1),
                          note="cell max 0.5C = 300 mA; ~80 % in constant current, then ~1 h constant voltage (estimate)")
    # standby: MCU power-down with the PIT (0.7 uA, secondary source), charger battery leakage
    # 1 uA max, TPS61169 shutdown 2 uA max; dividers switched off; PCM self-current not verified
    res["standby"] = standby_current(i_mcu_pd=0.7e-6, i_chg_rev=1.0e-6, i_drv_off=2.0e-6)
    res["standby"]["note"] = "excludes the cell's protection circuit (not verified, typically a few uA)"
    res["ntc"] = {f"{t} C": ntc_resolution(t) for t in (25, 37, 41, 45)}
    # boost at the extremes of the cell
    vout = 6 * (2.5 + 0.0) + 0.220
    res["boost_worst"] = {k: (round(v, 3) if isinstance(v, float) else v) for k, v in
                          boost_point(3.0, vout, I_CEIL[2], IND, DRV.f_sw, 0.80, 0.45).items()}
    res["boost_worst"]["case"] = f"VIN 3.0 V, VOUT {vout:.1f} V (6 x Vf max 2.5 V + VREF max), I {I_CEIL[2] * 1e3:.1f} mA"
    res["boost_worst"]["ovp_margin_V"] = round(DRV.v_ovp - vout, 1)
    (HERE / "budget.json").write_text(json.dumps(res, indent=1, default=float))
    print("| bank | level | I_LED mA | VOUT V | P_bat W | runtime h | duty 3.0 V | I_pk 3.0 V mA |")
    print("|---|---|---|---|---|---|---|---|")
    for r in res["levels"]:
        print(f"| {r['bank']} | {int(r['level'] * 100)} % | {r['i_led_mA']} | {r['v_out']} | {r['p_bat_W']} | {r['runtime_h']} | "
              f"{r['duty_3V0']} | {r['i_peak_3V0_mA']} |")
    for k in ("sense_resistor", "duty_for_caps", "charger", "standby", "ntc", "boost_worst"):
        print(k, res[k])


if __name__ == "__main__":
    main()
