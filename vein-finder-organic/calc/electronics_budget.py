"""
Gate-3 electronics budget: LED current caps, boost converter operating point, battery
current and runtime per brightness level, charger time, NTC resolution, standby drain.

Personal prototype for bench evaluation - NOT a medical device.

Units: SI inside (V, A, W, s, ohm, H, Hz); names carry mA/mm/uH where an input is
naturally in those units.  Every datasheet number lives in DATA with its source; nothing
here is a guess -- values marked "assumed" are design assumptions, stated as such.
"""
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent


@dataclass
class DriverIC:
    name: str
    v_fb: float              # V, feedback regulation voltage
    f_sw: float              # Hz
    i_lim: float             # A, switch current limit (min)
    v_ovp: float             # V, output over-voltage protection (min)
    vin_min: float           # V
    i_q_on: float            # A, quiescent current while switching (typ)
    i_q_off: float           # A, shutdown current (max)
    pwm_analog_band: tuple   # (Hz, Hz) CTRL PWM range that scales FB (analog dimming)
    source: str


@dataclass
class LedPart:
    name: str
    vf_at: tuple             # (V, A) datasheet typical forward voltage at test current
    i_max: float             # A, absolute max continuous
    source: str


@dataclass
class Inductor:
    name: str
    L: float                 # H
    i_sat: float             # A
    dcr: float               # ohm
    source: str


@dataclass
class Budget:
    driver: DriverIC
    led_a: LedPart           # 660 nm bank
    led_b: LedPart           # 620 nm bank
    ind: Inductor
    n_per_bank: int = 6
    # thermal current caps per LED from the concept (calc/concept_budget.py, dark skin = the
    # binding case; light/medium skin allow more).  These set the maximum level.
    i_cap_a: float = 0.023
    i_cap_b: float = 0.030
    levels: tuple = (0.40, 0.70, 1.00)        # fraction of the cap for the three taps
    eta: float = 0.80                         # assumed boost efficiency at 0.2-0.6 W (datasheet curves)
    v_d_schottky: float = 0.35                # V at ~50 mA (diode datasheet)
    batt_mah: float = 600.0
    batt_v_nom: float = 3.7
    batt_usable: float = 0.90
    i_mcu_active: float = 1.0e-3              # A, ATtiny1614 at 1-4 MHz active/idle mix (assumed)
    i_seam: float = 4.0e-3                    # A, status seam while on (5 LEDs, dimmed)


def string_voltage(led: LedPart, n: int, i: float, v_fb: float) -> float:
    """Boost output voltage: n LEDs at current i (Vf scaled by a 0.15 V/decade law, assumed)
    plus the feedback (sense) voltage."""
    v0, i0 = led.vf_at
    vf = v0 + 0.15 * math.log10(max(i, 1e-6) / i0)
    return n * vf + v_fb


def boost_point(vin: float, vout: float, iout: float, ind: Inductor, f_sw: float, eta: float, v_d: float):
    """Asynchronous boost operating point: duty, inductor ripple, peak current, mode."""
    d = 1.0 - vin * eta / (vout + v_d)
    i_in = vout * iout / (eta * vin)
    ripple = vin * d / (ind.L * f_sw)
    ccm = i_in > ripple / 2
    if ccm:
        i_pk = i_in + ripple / 2
    else:  # DCM: peak from energy per cycle  1/2 L Ipk^2 f = Pout/eta - ...
        i_pk = math.sqrt(2 * (vout + v_d - vin) * iout / (ind.L * f_sw))
    return dict(duty=d, i_in=i_in, ripple=ripple, i_pk=i_pk, ccm=ccm)


def run(b: Budget):
    out = {"inputs": asdict(b), "levels": []}
    for bank, led, cap in (("A 660 nm", b.led_a, b.i_cap_a), ("B 620 nm", b.led_b, b.i_cap_b)):
        for lv in b.levels:
            i = cap * lv
            vout = string_voltage(led, b.n_per_bank, i, b.driver.v_fb)
            p_out = vout * i
            p_in = p_out / b.eta
            p_bat = p_in + 3.7 * (b.driver.i_q_on + b.i_mcu_active + b.i_seam)
            e_wh = b.batt_mah / 1000 * b.batt_v_nom * b.batt_usable
            worst = boost_point(3.0, vout, i, b.ind, b.driver.f_sw, b.eta, b.v_d_schottky)
            nom = boost_point(3.7, vout, i, b.ind, b.driver.f_sw, b.eta, b.v_d_schottky)
            out["levels"].append(dict(
                bank=bank, level=lv, i_led_mA=round(i * 1e3, 1), v_out=round(vout, 2), p_led_W=round(p_out, 3),
                p_bat_W=round(p_bat, 3), runtime_h=round(e_wh / p_bat, 1),
                duty_3V0=round(worst["duty"], 3), i_peak_3V0_mA=round(worst["i_pk"] * 1e3, 1),
                ccm_3V0=worst["ccm"], duty_3V7=round(nom["duty"], 3),
                within_led_rating=i <= led.i_max, within_ovp=vout < b.driver.v_ovp,
                peak_vs_isat=round(worst["i_pk"] / b.ind.i_sat, 3), peak_vs_ilim=round(worst["i_pk"] / b.driver.i_lim, 3)))
    return out


def standby_current(i_mcu_pd: float, i_chg_rev: float, i_drv_off: float, i_divider: float = 0.0):
    tot = i_mcu_pd + i_chg_rev + i_drv_off + i_divider
    return dict(total_uA=round(tot * 1e6, 2), years_600mAh=round(0.6 / tot / 24 / 365, 1) if tot > 0 else None)


def ntc_resolution(t_c: float, r25=10e3, beta=3380.0, r_fix=10e3, bits=10):
    """dT per ADC LSB at temperature t_c for a top-side 10k fixed resistor / NTC to GND."""
    t = t_c + 273.15
    r = r25 * math.exp(beta * (1 / t - 1 / 298.15))
    v = r / (r + r_fix)                        # ratio of the divider supply
    dr_dt = -beta / t**2 * r
    dv_dt = r_fix / (r + r_fix) ** 2 * dr_dt
    lsb = 1 / (2**bits - 1)
    return dict(ratio=round(v, 4), K_per_lsb=round(abs(lsb / dv_dt), 4))


if __name__ == "__main__":
    print("use from docs/03-electronics/budget.py with datasheet values filled in")
