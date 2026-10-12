"""
Bench data sheet for the first unit: one row per measurement, with the expected value, the
limit and where each comes from.  Writes, next to this file:

  bench-sheet.csv         fill in "measured", "pass_fail", "notes"; send it back
  bench-offset-log.csv    checklist 3.7: thermocouples every minute, both banks
  bench-sheet.md          the same rows, printable

    python docs/08-prototype/make_bench_sheet.py

Expected values are copied from the cited files and checked against them by
check_bench_sheet() below where they are computed (LED-current windows, supply currents,
VOUT, charger, firmware thresholds), so a change in budget.json or logic.h fails this
script instead of leaving a stale number in the sheet.

Personal prototype for bench evaluation - NOT a medical device.
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

COLS = ["id", "section", "test", "item", "what", "unit", "instrument", "expected", "limit",
        "source", "measured", "pass_fail", "notes"]

ROWS: list[dict] = []


def row(id_, section, test, item, what, unit, instrument, expected, limit, source):
    ROWS.append(dict(id=id_, section=section, test=test, item=item, what=what, unit=unit,
                     instrument=instrument, expected=expected, limit=limit, source=source,
                     measured="", pass_fail="", notes=""))


def load():
    budget = json.loads((ROOT / "docs/03-electronics/budget.json").read_text())
    thermal = json.loads((ROOT / "docs/06-verification/thermal.json").read_text())
    dims = json.loads((HERE / "print_dims.json").read_text())
    logic_h = (ROOT / "fw/src/logic.h").read_text()
    return budget, thermal, dims, logic_h


def define(budget, thermal, dims):
    f = dims["features"]
    bb = dims["bbox_print_xyz_mm"]
    R9 = budget["sense_resistor"]["R_ohm"]

    # ------------------------------------------------------------------ P: prints
    P = "P print first article"
    pp = "print-packet §4"
    row("P-S1", P, pp, "", "Sole overall size L × W × H", "mm", "calipers",
        " × ".join(f"{v:.2f}" for v in bb["sole"]), "record", "print_dims.json")
    row("P-S2", P, pp, "", "Sole magnet pockets take a magnet (4)", "go/no-go", "magnet",
        f"Ø {f['magnet_pocket_d']:.2f}", f"goes in (Ø ≥ {f['magnet_d']})", "params.py MAG_D + MAG_POCKET_CLEAR")
    row("P-S3", P, pp, "", "Magnet height above the waterline face, dry: horns / tails", "mm", "depth rod",
        "1.95 / 1.10 (pocket 0.05 deeper, for glue)", "≤ 2.15 / ≤ 1.30", "params.py MAGNETS proud, MAG_GAP; parts.py sole()")
    row("P-S3g", P, "build-day 4.1", "", "Same, after gluing: horns / tails", "mm", "depth rod",
        "2.00 / 1.15", "≤ 2.15 / ≤ 1.30", "params.py MAGNETS proud, MAG_GAP")
    tol = f["magnet_centre_dist_tol"]
    row("P-S4a", P, pp, "", "Magnet centre distance, horn pair (across magnets − 6.35)", "mm", "calipers",
        f"{f['magnet_centre_dist_horns_y']:.2f}", f"± {tol}", "params.py MAGNETS, MAG_PCB_HOLE, MAG_POCKET_CLEAR")
    row("P-S4b", P, pp, "", "Magnet centre distance, tail pair (edge notches: limit is conservative)", "mm",
        "calipers", f"{f['magnet_centre_dist_tails_y']:.2f}", f"± {tol}", "params.py MAGNETS; order.md §1")
    ht = (f["magnet_centre_dist_horn_tail_x"] ** 2 + ((f["magnet_centre_dist_horns_y"] - f["magnet_centre_dist_tails_y"]) / 2) ** 2) ** 0.5
    row("P-S4c", P, pp, "", "Magnet centre distance, horn to tail, same side", "mm", "calipers",
        f"{ht:.2f}", f"± {tol}", "params.py MAGNETS")
    row("P-S5", P, pp, "", "Bare PCB drops over the four dry magnets", "go/no-go", "bare PCB",
        "drops on", "no force", "layout.json pcb_holes; MAG_PCB_HOLE 6.75")
    row("P-S6", P, pp, "", "LED channels take an LED body (12)", "go/no-go", "spare LEDs",
        f"{f['led_channel_radial']:.2f} × {f['led_channel_tangential']:.2f}",
        f"body enters (≤ {f['led_body_radial_max']} wide)", "params.py LED_PKG, LED_TOL; parts.py sole()")
    row("P-S7", P, pp, "", "NTC pocket depth", "mm", "depth rod", f"{f['ntc_pocket_depth']:.2f}",
        f"≥ {f['ntc_body_max'][2]}", "params.py NTC_PKG; parts.py sole()")
    row("P-S8", P, pp, "", "Sole thickness at the NTC pocket; window = S8 − S7", "mm", "calipers",
        "1.80 (window 0.70)", "window: record; hole = reprint", "checks.json ntc (sensor window)")
    row("P-S9", P, pp, "", "USB-C opening width at the sole's waterline face", "mm", "calipers",
        f"{f['usb_opening_width_at_waterline']:.2f}", f"≥ {f['usb_shell_width_at_waterline']:.2f} (shell there)",
        "params.py USB_*; print_dims.json")
    row("P-S10", P, pp, "20", "USB-C lip under the opening (N19), and preview layer count", "mm", "calipers",
        "0.91", "record (N19 decided for 0.91)", "checks.json usb opening lip; readiness N19")
    row("P-S11", P, pp, "", "Sole waterline face flat on glass", "obs", "glass", "flat", "record", "build §1")
    row("P-T1", P, pp, "", "Top shell overall size L × W × H", "mm", "calipers",
        " × ".join(f"{v:.2f}" for v in bb["top_shell"]), "record", "print_dims.json")
    row("P-T2", P, pp, "", "Boss undersides below the waterline face (4)", "mm", "depth rod",
        f"{f['boss_underside_above_waterline']:.2f}", "≥ board thickness (A-2.1a)",
        "params.py PCB_T + BOSS_PCB_GAP")
    row("P-T3", P, pp, "", "Bare PCB in the shell: no wall contact; face at or below the waterline", "go/no-go",
        "bare PCB, straightedge", "0.3 mm clearance", "no contact; not proud", "params.py PCB_CLEAR, BOSS_PCB_GAP")
    row("P-T4", P, pp, "", "Horn counterbores take a magnet (2)", "go/no-go", "magnet",
        f"Ø {f['dowel_counterbore_d']:.2f}", "goes in", "params.py MAG_D + MAG_DOWEL_CLEAR")
    row("P-T5", P, pp, "", "Top magnet pockets take a magnet (4)", "go/no-go", "magnet",
        f"Ø {f['magnet_pocket_d']:.2f}", "goes in", "params.py MAG_D + MAG_POCKET_CLEAR")
    row("P-T6", P, pp, "", "USB-C opening width in the shell, at its widest (0.98 above the waterline)", "mm",
        "calipers", f"{f['usb_opening'][0]:.2f}", f"≥ {f['usb_shell'][0]}", "params.py USB_W + 2 × USB_CLEAR")
    row("P-T7", P, pp, "", "Button skin and seam slot against a bright light", "obs", "lamp",
        "even glow; slot open", "no pinholes", "checklist 1.6")
    row("P-B1", P, pp, "", "Bridge pedestal top above the feet", "mm", "calipers",
        f"{f['bridge_pedestal_top_above_feet']:.2f}", f"≤ {f['bridge_pedestal_top_above_feet'] + f['switch_gap']:.2f}",
        "print_dims.json; params.py SWITCH_GAP")
    row("P-B2", P, pp, "", "Bridge deck underside above the feet", "mm", "depth rod",
        f"{f['bridge_deck_underside_above_feet']:.2f}", "≥ tape + cell (A-2.1f)",
        "params.py BATT_FOAM + BATT_T + BATT_TOP_CLEAR")
    sw_top = f["bridge_pedestal_top_above_feet"] + f["switch_h"]
    row("P-B3", P, pp, "5", "Switch seated: feet to actuator top", "mm", "calipers",
        f"{sw_top:.2f} on the pedestal; {sw_top - f['switch_seat'][2]:.2f} in the 0.60 seat",
        f"≤ {sw_top + f['switch_gap']:.2f}; shims ≈ ({sw_top + f['switch_gap']:.2f} − B3) / 0.1",
        "parts.py bridge(); params.py SWITCH_H, SWITCH_GAP; cad.md §4")
    row("P-B4", P, pp, "", "Bridge leg span", "mm", "calipers", f"{f['bridge_leg_y_span']:.2f}", "record",
        "params.py BRIDGE_LEG_Y, BRIDGE_LEG")
    row("P-B5", P, pp, "", "Posts slide into the 4 bridge holes", "go/no-go", "header post",
        f"Ø {f['pin_hole_part']} hole, {f['pin_post_diagonal']} post", "snug; ream 1.0 if tight",
        "params.py PIN_HOLE_PART, PIN_SQ; build §1")
    row("P-M1", P, pp, "", "Seam mask highest point above the base", "mm", "calipers",
        f"{bb['seam_mask'][2]:.2f}", f"≤ {bb['seam_mask'][2] + f['mask_gap_to_shell']:.2f}",
        "print_dims.json; params.py MASK_GAP")
    row("P-M2", P, pp, "", "Mask ear height", "mm", "calipers", f"{f['mask_ear_height']:.2f}", "record",
        "params.py MASK_EAR")
    row("P-M3", P, pp, "", "Posts slide into the 2 ear holes", "go/no-go", "header post",
        f"Ø {f['pin_hole_part']}", "snug; ream 1.0 if tight", "params.py PIN_HOLE_PART")
    row("P-M4", P, pp, "", "Mask over the five amber LEDs, none touched", "go/no-go", "populated PCB",
        f"channel {f['mask_channel']}", "no LED touched (lands 0.95)", "params.py MASK_CHANNEL; electronics §3")

    # ------------------------------------------------------------------ A: bare board
    A = "A bare board (stage A)"
    row("A-1.2a", A, "chk 1.2", "", "fw.hex sha256 (first 8 hex)", "hash", "sha256sum",
        "e8bc8159 at f2a3eef, avr-gcc 14.1.0", "record; build checks pass", "gate run 2026-10-12 (BUILD-LOG)")
    row("A-1.2b", A, "chk 1.2", "15", "fw_wdt_test.hex sha256 (first 8 hex)", "hash", "sha256sum",
        "2dde1528 at f2a3eef", "record", "gate run 2026-10-12 (BUILD-LOG)")
    row("A-2.1a", A, "chk 2.1", "", "Board thickness at the edge", "mm", "calipers", "1.00", "0.90–1.10",
        "params.py BOSS_PCB_GAP note: boards 1.0 ± 0.1")
    row("A-2.1b", A, "chk 2.1", "2", "R9 resistance (leads nulled)", "Ω", "DMM", f"{R9}",
        f"{R9 * 0.99:.2f}–{R9 * 1.01:.2f}", "budget.json sense_resistor (1 %)")
    row("A-2.1c", A, "chk 2.1", "", "[Li] Cell voltage as delivered", "V", "DMM", "part-charged",
        "3.00–4.28", "readiness §2 (cell protection window)")
    row("A-2.1d", A, "chk 2.1", "19", "Foam tape thickness", "mm", "calipers", "1.0 or 1.6", "record",
        "Adafruit 5019 listing; params.py BATT_FOAM 1.6")
    row("A-2.1e", A, "chk 2.1", "19", "[Li] Cell thickness incl. protection board", "mm", "calipers", "≤ 5.40",
        "record", "params.py BATT_T (datasheet envelope)")
    row("A-2.1f", A, "chk 2.1", "19", "Tape + cell", "mm", "sum", "7.00 (1.6 + 5.4)", "≤ 7.40 and ≤ P-B2",
        "build §4.3; params.py")
    for k, (net, where) in zip("abc", [("VBAT–GND", "TP4–TP5"), ("VBUS–GND", "R5 pin 1–GND"), ("VOUT–GND", "C5")]):
        exp = "≈ 300 k (R5 + R6 + R7)" if net == "VBUS–GND" else "climbs as caps charge"
        row(f"A-2.3{k}", A, "chk 2.3", "", f"Resistance {net} ({where})", "Ω", "DMM", exp,
            "no steady reading < 10 Ω (PROPOSED, M1)", "build §2 step 11; design.py")
    row("A-2.4", A, "chk 2.4", "", "[CL] Idle current at first power-up, 3.70 V / 50 mA limit", "mA", "supply",
        "low (blank MCU)", "below the 50 mA limit; record (M4)", "checklist 2.4")
    row("A-2.6", A, "chk 2.6", "12b", "[CL] RT1 not fitted: ring LEDs light?", "obs", "eye",
        "never; seam double-blinks", "never lights", "verification §8 item 12")
    row("A-2.7", A, "chk 2.7", "", "[CL] Smoke test: levels, bank, 6 LEDs per string, seam", "obs", "eye",
        "firmware §1 behaviour", "all as documented", "firmware.md §1")
    row("A-2.8", A, "chk 2.8", "12a", "[CL] RT1 shorted at level 3: time to off; back on at release", "s", "eye/video",
        "off, seam double-blink", "≤ 0.3 s; back on", "verification §8 item 12")
    lv = budget["levels"]
    letters = iter("abcdefghijklmnopqr")
    # windows as printed in checklist 2.9 (documented current x 8.2 ohm, +-10 %)
    windows = {("660", 1): (9, 66, 81), ("660", 2): (16, 118, 144), ("660", 3): (23, 170, 207),
               ("625", 1): (10, 74, 90), ("625", 2): (17, 125, 153), ("625", 3): (25, 185, 225)}
    for bank, model in (("660", lv[0:3]), ("625", lv[3:6])):
        for n, m in enumerate(model, 1):
            i_doc, lo, hi = windows[(bank, n)]
            assert abs(lo - 0.9 * i_doc * R9) <= 1.0 and abs(hi - 1.1 * i_doc * R9) <= 1.0
            row(f"A-2.9{next(letters)}", A, "chk 2.9", "2", f"[CL] V across R9, {bank} nm level {n}", "mV", "DMM (mV)",
                f"{m['i_led_mA'] * R9:.1f} ({m['i_led_mA']} mA model)", f"{lo}–{hi} ({i_doc} mA ± 10 %); stop > 246",
                "verification §8 item 2; checklist 2.9; budget.json")
    for bank, model in [("660", lv[0:3]), ("625", lv[3:6])]:
        for n, m in enumerate(model, 1):
            row(f"A-2.9{next(letters)}", A, "chk 2.9", "", f"[CL] Supply current at 3.70 V, {bank} nm level {n}", "mA",
                "supply / DMM", f"{m['p_bat_W'] / budget['inputs']['batt_v_nom'] * 1000:.0f}", "record",
                "budget.json p_bat ÷ 3.7 V")
    for bank, model in [("660", lv[0:3]), ("625", lv[3:6])]:
        for n, m in enumerate(model, 1):
            row(f"A-2.9{next(letters)}", A, "chk 2.9", "", f"[CL] VOUT at C5, {bank} nm level {n}", "V", "DMM",
                f"{m['v_out']:.2f}", "record; ≤ 15.2 (worst case)", "budget.json v_out; electronics §5 worst case")
    for k, (bank, ev, drain) in zip("abcd", [("660", "4th tap off", "Q1"), ("660", "RT1-short cut-off", "Q1"),
                                            ("625", "4th tap off", "Q2"), ("625", "RT1-short cut-off", "Q2")]):
        before = lv[2]["v_out"] if bank == "660" else lv[5]["v_out"]
        row(f"A-2.10{k}", A, "chk 2.10", "16", f"[CL] {bank} nm, {ev}: VOUT before / peak after / {drain} drain max",
            "V", "scope", f"{before:.1f} before, then decay", "no peak above 'before'; drain < 30",
            "verification §8 item 16; electronics §2")
    row("A-2.11", A, "chk 2.11", "15", "[CL] Watchdog test image: dark after the tap", "s", "stopwatch",
        "6.0", "6 ± 1; stays dark", "verification §8 item 15; firmware §1.1")
    row("A-2.12", A, "chk 2.12", "13", "[CL] Stuck button: bank switch time / off after the switch", "s", "stopwatch",
        "0.6 / 180", "one switch; 162–198; off after release", "verification §8 item 13; logic.h AUTO_OFF_TICKS")
    for k in "abc":
        row(f"A-2.13{k}", A, "chk 2.13", "17", f"[CL] Auto-off time, run {'abc'.index(k) + 1}", "s", "stopwatch",
            "180", "162–198", "verification §8 item 17; firmware §1.1")
    row("A-2.13d", A, "chk 2.13", "17", "[CL] 5 presses of ~0.5 s: level steps", "n/5", "stopwatch", "5",
        "5/5 step", "firmware §1.1 (hold ≥ 594 ms, 535–653)")
    row("A-2.13e", A, "chk 2.13", "17", "[CL] 5 presses of ~0.7 s: bank switches", "n/5", "stopwatch", "5",
        "5/5 switch", "firmware §1.1")
    row("A-2.14a", A, "chk 2.14", "7", "[CL] Sleep current", "µA", "DMM µA, series", "≤ 3.7",
        "≤ 10", "verification §8 item 7; electronics §5")
    row("A-2.14b", A, "chk 2.14", "18", "[CL] Current with the button held, off", "mA", "DMM mA, series",
        "unverified (N14)", "≤ 1", "verification §8 item 18")
    row("A-2.15", A, "chk 2.15", "14a", "[CL] Wake on the first tap after > 1 min asleep", "n/20", "count",
        "20", "20/20", "verification §8 item 14")
    row("A-2.16a", A, "chk 2.16", "", "[CL] Supply voltage when the seam starts 1 Hz blinking", "V", "DMM TP4–TP5",
        "< 3.400", "record (M5)", "logic.h VBAT_LOW_MV")
    row("A-2.16b", A, "chk 2.16", "", "[CL] Supply voltage when the LEDs go off", "V", "DMM TP4–TP5",
        "< 3.200", "record (M5); must be > 3.00", "logic.h VBAT_CUTOFF_MV; cell protection 3.00")
    row("A-2.16c", A, "chk 2.16", "", "[CL] Tap at 3.49 V", "obs", "eye", "nothing", "stays off", "logic.h VBAT_RESUME_MV")
    row("A-2.16d", A, "chk 2.16", "", "[CL] Tap at 3.50 V", "obs", "eye", "lights", "lights", "logic.h VBAT_RESUME_MV")
    row("A-2.17", A, "chk 2.17", "", "[Li] Cell soldered red→TP1, black→TP2; tap lights", "obs", "DMM, eye",
        "lights", "polarity right", "build §3 step 1; N21")
    ch = budget["charger"]
    row("A-2.18a", A, "chk 2.18", "14b", "[Li] USB plugged while asleep: VBUS to seam PWM", "s", "scope",
        "breathes", "≤ 0.1", "verification §8 item 14")
    row("A-2.18b", A, "chk 2.18", "3", "[Li] Charge current at termination", "mA", "USB meter",
        f"{ch['i_term_mA']}", "stops near 25; then seam steady", "budget.json charger; item 3")
    for t in range(0, 241, 15):
        row(f"A-2.18-t{t:03d}", A, "chk 2.18", "3", f"[Li] Charge current at {t} min", "mA", "USB meter",
            f"{ch['i_charge_mA'][1]} (CC phase)", f"{ch['i_charge_mA'][0]}–{ch['i_charge_mA'][2]} while in CC",
            "budget.json charger; electronics §2 (K_ISET 490/540/590 ÷ 2.2 k)")
    row("A-2.19", A, "chk 2.19", "21", "[Li] Full cell, USB at 4.60 V: seam steady; tap lights?", "obs", "eye",
        "steady; does not light", "both", "verification §8 item 21; electronics §2")
    row("A-2.20a", A, "build-day 4.2", "19", "Board in the sole flat, no rocking", "obs", "eye", "flat",
        "no rocking", "verification §8 item 19")
    row("A-2.20b", A, "build-day 4.3", "19", "[Li] Tape + cell as fitted", "mm", "calipers", "7.00", "≤ 7.40 and ≤ P-B2",
        "build §4.3")
    row("A-2.20c", A, "build-day 4.4", "5", "Switch seated height (= P-B3, in place)", "mm", "calipers",
        f"{sw_top:.2f} / {sw_top - f['switch_seat'][2]:.2f}", "see P-B3", "print-packet §5")
    row("A-2.20d", A, "build-day 4.4", "5", "Shim count; click within the first 0.3 mm", "n", "count",
        "≈ 6–7 if B3 = 16.41", "click ≤ 0.3 mm", "build §4.4; print-packet §5")
    row("A-2.20e", A, "build-day 4.5", "", "Waterline gap when closed", "mm", "feeler / eye", "0", "record (M7)",
        "checklist 2.20")

    # ------------------------------------------------------------------ B: phantom
    B = "B phantom (stage B)"
    row("B-3.0a", B, "chk 3.0", "", "Phantom face temperature before each run", "°C", "reference thermometer",
        "33.5", "33.0–34.0 (PROPOSED)", "checklist 3.0; verification §4")
    row("B-3.0b", B, "chk 3.0", "", "Thermocouple 1 against the reference at ~37 °C", "°C", "TC + reference",
        "0", "± 0.5 (PROPOSED)", "checklist 3.0")
    row("B-3.0c", B, "chk 3.0", "", "Thermocouple 2 against the reference at ~37 °C", "°C", "TC + reference",
        "0", "± 0.5 (PROPOSED)", "checklist 3.0")
    row("B-3.1", B, "chk 3.1", "", "Closed unit: levels, bank, USB breathing", "obs", "eye", "as A-2.7", "all",
        "checklist 3.1")
    for p in range(1, 6):
        row(f"B-3.2-p{p}", B, "chk 3.2", "5", f"Button force at the click, press {p}", "g", "kitchen scale",
            "306–367 (3.0–3.6 N)", "204–510 (2–5 N), click felt", "verification §8 item 5; checks.json membrane")
    for p in range(1, 4):
        row(f"B-3.3-p{p}", B, "chk 3.3", "6", f"Magnet closure, pull {p}", "kg", "luggage scale",
            "2.46–2.63 (24.1–25.8 N)", "≥ 1.53 (15 N)", "verification §8 item 6; verification §1")
    for c in range(1, 4):
        row(f"B-3.4{'abc'[c - 1]}", B, "chk 3.4", "20", f"N19 gate: cable {c} latches; charge current", "mA",
            "USB meter", f"{ch['i_charge_mA'][1]}", f"{ch['i_charge_mA'][0]}–{ch['i_charge_mA'][2]}",
            "verification §8 items 3, 20")
    row("B-3.4d", B, "chk 3.4", "20", "N19 gate: straight plug cycles with the bulky cable", "n", "count", "20",
        "20", "verification §8 item 20")
    row("B-3.4e", B, "chk 3.4", "20", "N19 gate: lip after 20 cycles (photos before/after)", "obs", "loupe, camera",
        "unchanged", "no whitening, no cracks: N19 confirmed", "readiness N19; checklist 3.4")
    row("B-3.5", B, "chk 3.5", "9", "Light around the sole's edge, dark room, both banks", "obs", "eye, camera",
        "none", "none (seam glow intended)", "verification §8 item 9")
    for r in range(1, 4):
        row(f"B-3.6-r{r}-dim", B, "chk 3.6 (offset)", "11", f"Run {r}: TC on NTC window at first dimming; offset = TC − 38.0",
            "°C", "TC", "38.0 at the NTC (T_DERATE_DC)", "dims from about 38 (no tolerance)", "logic.h; item 11")
        row(f"B-3.6-r{r}-off", B, "chk 3.6 (offset)", "11", f"Run {r}: TC at cut-off (seam double-blink); offset = TC − 41.0",
            "°C", "TC", "41.0 at the NTC (T_CUTOFF_DC)", "TC ≤ 42.0 (offset ≤ 1.0)", "logic.h; item 11")
        row(f"B-3.6-r{r}-on", B, "chk 3.6 (offset)", "11", f"Run {r}: TC when it comes back on; offset = TC − 38.0",
            "°C", "TC", "≤ 38.0 at the NTC", "back on below 38", "logic.h; item 11")
    t660 = [r["T_face_C"] for r in thermal if r["bank"] == "660"]
    t625 = [r["T_face_C"] for r in thermal if r["bank"] == "625"]
    lo660, hi660 = min(min(t) for t in t660), max(max(t) for t in t660)
    lo625, hi625 = min(min(t) for t in t625), max(max(t) for t in t625)
    for bank, lo, hi in (("A", lo660, hi660), ("B", lo625, hi625)):
        nm = "660" if bank == "A" else "625"
        row(f"B-3.7-{bank}-max", B, "chk 3.7 (offset)", "4", f"{nm} nm, 20 min on the phantom: max TC1 (face, pocket edge)",
            "°C", "TC1 (log: bench-offset-log.csv)", f"{lo}–{hi} on perfused skin", "≤ 41.0 all 20 min",
            "thermal.json; verification §8 item 4; brief")
        row(f"B-3.7-{bank}-off", B, "chk 3.7 (offset)", "4", f"{nm} nm: TC1 − TC2 at minute 20 (face to NTC window)",
            "°C", "TC1, TC2", "not modelled (verification §4)", "record", "verification §4")
    for k, (ty, nm) in enumerate([("XZM2MR55W-3", "660")] * 3 + [("XZM2CRK55W-3", "625")] * 3):
        exp = "12 mW / ~110 lx" if nm == "660" else "2.2–6.6 mW"
        lim = "≥ 8 mW (≥ 71 lx); ≤ ~24 mW (~220 lx)" if nm == "660" else "record (M11); ≤ ~2× estimate"
        row(f"B-3.8{'abcdef'[k]}", B, "chk 3.8", "1", f"{nm} nm LED {k % 3 + 1}, 20 mA, 100 mm on axis; meter λ setting",
            "mW or lx", "optical power / lux meter", exp, lim, "verification §8 item 1, §6; optics.py")
    row("B-3.9", B, "chk 3.9", "8", "Runtime at 660 nm level 3 from full", "min", "stopwatch", "306 (5.1 h)",
        "≥ 45", "verification §3; item 8")

    # ------------------------------------------------------------------ C: skin
    C = "C skin (stage C, after GATE A and B)"
    row("C-4", C, "readiness §5 C", "4", "Briefly on skin: max TC1; duration", "°C", "TC1", "≤ phantom result",
        "≤ 41.0; stop at discomfort", "verification §8 item 4")
    row("C-10", C, "readiness §5 C", "10", "Veins visible at the rim: room light / dimmed", "obs", "eye, photo",
        "rim ≈ 1.5× veil (room); ≈ 7× at 100 lx", "record", "electronics §5 (optics.py)")


def check_bench_sheet(budget, logic_h):
    """Fail if a copied constant no longer matches its source."""
    def define_val(name):
        m = re.search(rf"#define\s+{name}\s+(\d+)", logic_h)
        return int(m.group(1))
    assert define_val("T_DERATE_DC") == 380 and define_val("T_CUTOFF_DC") == 410
    assert define_val("VBAT_LOW_MV") == 3400 and define_val("VBAT_CUTOFF_MV") == 3200
    assert define_val("VBAT_RESUME_MV") == 3500
    assert budget["sense_resistor"]["R_ohm"] == 8.2
    assert budget["charger"]["i_charge_mA"] == [223, 245, 268] and budget["charger"]["i_term_mA"] == 24.5
    assert [round(x["i_led_mA"]) for x in budget["levels"]] == [9, 16, 23, 10, 17, 25]
    ids = [r["id"] for r in ROWS]
    assert len(ids) == len(set(ids)), "duplicate row id"


def write(budget):
    with open(HERE / "bench-sheet.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        w.writerows(ROWS)
    with open(HERE / "bench-offset-log.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["bank", "minute", "tc1_face_C", "tc2_ntc_window_C", "tc1_minus_tc2_C", "event (dim / double-blink / none)"])
        for bank in ("660", "625"):
            for m in range(0, 21):
                w.writerow([bank, m, "", "", "", ""])

    out = [HEADER]
    section = None
    for r in ROWS:
        if r["section"] != section:
            section = r["section"]
            out.append(f"\n## {SECTION_TITLES[section[0]]}\n")
            out.append("| ID | What | Item | Expected | Limit | Source | Measured | P/F |")
            out.append("|---|---|---|---|---|---|---|---|")
        unit = "" if r["unit"] in ("obs", "go/no-go", "hash") else f" ({r['unit']})"
        out.append(f"| {r['id']} | {r['what']}{unit} | {r['item']} | {r['expected']} | {r['limit']} | "
                   f"{r['source']} | | |")
        if r["id"] == "B-3.6-r3-on":
            out.append(OFFSET_NOTE)
            out.append("| ID | What | Item | Expected | Limit | Source | Measured | P/F |")
            out.append("|---|---|---|---|---|---|---|---|")
    out.append(OFFSET_LOG)
    out.append(UART_NOTE)
    (HERE / "bench-sheet.md").write_text("\n".join(out) + "\n")


SECTION_TITLES = {
    "P": "P. Prints: first-article checks (print packet §4)",
    "A": "A. Bare board, stage A (build-day §2–4; checklist Stage 2)",
    "B": "B. Phantom, stage B (build-day §5; checklist Stage 3)",
    "C": "C. Skin, stage C: only after GATE A and GATE B (readiness §5)",
}

HEADER = """# Bench data sheet

> **Personal prototype for bench evaluation. Not a cleared medical device.**
> Not for diagnosis, treatment or clinical use.

Generated by [`make_bench_sheet.py`](make_bench_sheet.py), which also writes
[`bench-sheet.csv`](bench-sheet.csv) (fill this one in and send it back) and
[`bench-offset-log.csv`](bench-offset-log.csv) (the per-minute thermocouple log).

**How to use it:**
- Every row is a meter, scope, thermocouple, scale, caliper or stopwatch reading, or an
  observation. **No row needs a serial log**; the note at the end says what the debug UART
  would add.
- **Expected** is the model's or the document's value. **Limit** is the pass criterion
  (or "record" where none is documented; the M numbers are checklist §4's missing
  criteria). **Source** is the file it comes from.
- Row IDs match the [build-day checklist](build-day.md). [CL] = current-limited supply;
  [Li] = lithium cell.
- For a pass/fail row, write P or F. For a "record" row, write the value; it passes by
  being recorded.
"""

OFFSET_NOTE = """
**Section B offset rows: the skin-vs-thermistor offset, repeated.**
- The firmware cannot report the NTC temperature (checklist rule 4). Its thresholds are
  the readout: it dims when the NTC reads 38.0 °C and cuts off at 41.0 °C (`logic.h`).
- So:
  - the thermocouple on the NTC window at those moments, minus 38.0 or 41.0, is the
    **window-to-NTC offset** (B-3.6, three runs);
  - TC1 − TC2 in the per-minute log is the **face-to-window offset** (B-3.7).
- Their sum is the face-to-NTC offset that `T_*_DC` in `logic.h` must allow for
  (verification §4). No model predicts it (verification §4: "not yet known"), so the
  expected column says so.
"""

OFFSET_LOG = """
## B-3.7 per-minute log (bench-offset-log.csv)

Fill one row per minute, 0–20, for each bank: TC1 on the face at the edge of the 660 nm
pocket at +35°, TC2 on the NTC window, their difference, and any dimming or double-blink.
The limit is the B-3.7 row: TC1 ≤ 41.0 °C for all 20 minutes.

| Bank | Minute | TC1 face (°C) | TC2 NTC window (°C) | TC1 − TC2 | Event |
|---|---|---|---|---|---|
""" + "\n".join(f"| {b} | {m} | | | | |" for b in ("660", "625") for m in range(0, 21))

UART_NOTE = """
## Note U1: what the debug UART would add

The board has TX/RX pads (TP6/TP7, PB2/PB3) and no firmware for them (firmware §3). As
asked, none is written. **Every bench item above can be judged without it.** Only two
things cannot be measured, and neither is a bench item's pass criterion:

1. **The NTC's own reading error, apart from its thermal lag.** The threshold method
   (B-3.6) measures their sum at 38 and 41 °C, and the 41 °C limit acts on exactly that
   sum. Separating them would need the firmware's temperature (`t_dc`) while a
   thermocouple sits on RT1.
2. **The firmware's cell-voltage reading (`read_vdd_mv`).** Checklist 2.16's failure
   action says to check it if there is no cut-off. The trip points (A-2.16a–b) against the
   meter are the readout without it.

**What either would need:**
- a debug build that prints `t_dc` and `vbat_mv` on TX at each 250 ms reading;
- a USB-serial adapter with **5 V logic**, its RX on TP6 and GND on TP5. The board's
  logic runs at the cell's 3.0–4.2 V (firmware §4);
- every gate re-run for the new build. It must leave the release image byte-identical,
  as the watchdog test hook does.

Only if you ask for it.
"""


def main():
    budget, thermal, dims, logic_h = load()
    define(budget, thermal, dims)
    check_bench_sheet(budget, logic_h)
    write(budget)
    print(f"{len(ROWS)} rows -> bench-sheet.csv, bench-sheet.md; 42-row offset log")


if __name__ == "__main__":
    main()
