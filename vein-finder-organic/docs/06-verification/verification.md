# Verification report

> **Personal prototype for bench evaluation. Not a cleared medical device.**
> Not for diagnosis, treatment or clinical use. This report checks the design against
> the brief. It is not a safety case, and nothing here has been measured on hardware yet:
> §8 lists the bench checks to run on the first build.

## 1. Results against the brief

| Requirement (brief) | Result | How it was checked | Status |
|---|---|---|---|
| Palm-sized river stone, G2 surfaces | 90.2 × 58.9 × 24.7 mm, 56 g; G2 everywhere, poles included | `cad/device/verify_skin.py`, zebra renders | met |
| Walls ≥ 1.6 mm, two approved thin spots | top shell 1.80 mm min (805 k samples); thin spots 0.68 mm (seam) and 0.40 mm (button) | `checks.py` wall map, probes | met |
| … sole floors | magnets 1.82 / 1.67 mm, pins 1.94–3.10 mm; **NTC window 0.70 mm** and **USB-C pocket 1.15 mm** | `checks.py sole_floors` | 2 decisions open (§6) |
| Cosmetic surfaces without supports | top-shell skin max overhang 21.0°; sole skin none (one 0.01 mm² tessellation speck) | `checks.py` overhang | met |
| Parts fit, no interference | 13 parts and stand-ins, pairwise: none | `checks.py` interference | met |
| Magnet closure (your choice) | 24.1–25.8 N with N35 (4 pairs) | coaxial current-loop model | met |
| Button hidden under a flexing membrane | 3.0–3.6 N press (±30 %) | shallow-shell Ritz model | met |
| LEDs 660 / 620 nm | 660 nm (XZM2MR55W-3) and 625 nm (XZM2CRK55W-3), six each | parts | met (625, not 620: nearest stocked part) |
| Tap = 3 brightness levels, hold = bank, 3-min auto-off | as specified; host unit tests pass | `fw/test/test_logic.c` | met (bench test open) |
| Skin-contact surface ≤ 41 °C | model 35.4–38.0 °C at full power; firmware derates from 38 °C (NTC) and cuts off at 41 °C | `thermal.py`, firmware | met in model; NTC offset to calibrate (§8) |
| ≥ 45 min at full brightness | 4.5 h (625 nm) / 5.1 h (660 nm) | `budget.py` | met |
| IEC 62471 | Exempt group: retinal thermal 1.2–1.5 % and blue light 38–48 % of the exempt limits | `iec62471.py` | met (limits from secondary sources) |
| Only in-stock parts, every part number and price looked up | every line has distributor, PN, price, stock, level | BOM | met, 1 price NV |
| Cost ≤ $75 | $36.13 parts + $5–15 PCB = $41–51 (shipping excluded) | BOM | met |
| KiCad schematic, PCB outline, BOM with links and prices | schematic (netlist round trip), routed 2-layer PCB with DRC 0 errors / 0 unconnected, Gerbers, BOM | `ee/` | met (§5) |
| Print settings, illustrated assembly guide | [build guide](../05-build/build.md) | — | done |
| Personal prototype label on all docs | every document, the schematic title block and the board silkscreen | — | done |

## 2. Walls, floors and fits

The results below come from the built solids in `build/device/checks.json`.

**Top shell:**
- 1.800 mm general minimum and median, over 804 701 skin samples.
- The button skin is 0.400 mm.
- The seam slot leaves 0.68 mm normal to the wall.

**Sole floors** (PETG under each blind pocket, probed through the built solid):

| Pocket | Floor | Note |
|---|---|---|
| Horn magnets (−12, ±20) | 1.82 mm | dowel magnet 2.0 mm proud |
| Tail magnets (56.6, ±12) | 1.67 mm | 1/16″ pair |
| Mask-ear pins | 1.94 mm | |
| Bridge pins | 3.10 mm | |
| NTC | **0.70 mm** | sensor window: designed thin, decision open |
| USB-C body pocket | **1.15 mm** | receptacle hangs 0.61 mm below the board: decision open |
| USB-C opening lip | 0.91 mm | edge of the port opening; the tail is 6.3 mm tall here |

**LEDs against the sole:**
- 1206 domes at their maximum datasheet height; none stands proud of the skin face.
- The worst positions (±35°, 660 nm) are flush. The 625 nm parts at ±11.7° are recessed
  0.01 mm.

**Clearances:** as designed in gate 2 ([cad.md §5.4](../02-cad/cad.md)). New in gate 3:
- pin pads to LED lands: 1.13 mm;
- NTC land to LED lands: 0.91 mm;
- magnet holes to LED lands: 0.61 mm;
- LED lands to each other: 2.77 mm.

**Cell:** it sits on the board on 1.0–1.6 mm foam tape.
- At least 2.15 mm of headroom to the shell over its whole footprint.
- 0.4 mm to the bridge deck.
- Inside the cavity with 0.4 mm all round.

**Interference:** none between any pair of the 13 parts and stand-ins.

## 3. Runtime and charging

| Bank | 40 % | 70 % | 100 % |
|---|---|---|---|
| 660 nm | 12.1 h | 7.2 h | **5.1 h** |
| 625 nm | 10.8 h | 6.4 h | **4.5 h** |

- 600 mAh minimum capacity, 90 % usable.
- 80 % boost efficiency (assumed from the datasheet's curves).
- MCU 1.5 mA, seam 4 mA.
- **Charging:** 245 mA (223–268 mA), about 3 h, within the cell's 0.5 C.
- **Standby:** 3.7 µA plus the cell's protection circuit. Shelf life is set by the cell's
  self-discharge.

## 4. Thermal

**Model** ([`thermal.py`](thermal.py)): the concept's skin model uses the real LED
positions and the estimated optical power (14 mW per 660 nm LED, 2.7–8.2 mW per 625 nm
LED). Skin 33.5 °C, plus 1.5 K for the device's own heat.

| Bank | Light skin | Medium | Dark |
|---|---|---|---|
| 660 nm, full | 36.7 °C | 37.2 °C | 38.0 °C |
| 625 nm, full | 35.4–36.2 °C | 35.5–36.5 °C | 35.7–37.0 °C |

**Control:** the NTC sits 0.7 mm under the face, just outside the LED ring on the tail
side (θ = 0, r = 20.4 mm), and is read every 250 ms. The firmware:
- derates linearly from 38 °C to 20 % at 40 °C;
- turns the LEDs off at 41 °C;
- resumes at 38 °C.

**Not yet known:** the offset between the NTC reading and the hottest point of the face,
which is next to an LED pocket. Calibrate it on the bench (§8, item 4) and adjust
`T_DERATE_DC` / `T_LIMIT_DC` / `T_CUTOFF_DC` in `fw/src/logic.h`.

## 5. Electronics checks

- **Schematic ↔ design:** the netlist exported by kicad-cli matches `ee/design.py` for all
  40 nets (two off-board parts, the cell and the switch, are excluded by design).
- **Placement:** every top-side courtyard is checked by `ee/placement.py`:
  - inside the free board area;
  - clear of the seam mask, magnet bosses, bridge feet and USB-C;
  - under the shell's inner surface by ≥ 0.3 mm.
- **PCB DRC** (KiCad 7.0.11, this board's rules): **0 errors, 0 unconnected items.**
  - Rules: 0.2 mm clearance; copper 0.3 mm from the board edge, with two documented
    exceptions (USB-C land pattern 0.20 mm, outer ring LEDs 0.27 mm). See
    [electronics.md §4](../03-electronics/electronics.md).
  - 12 warnings, all `lib_footprint_mismatch`: the ring LEDs' silk outlines are cut back
    at the board edge on purpose.
  - Every pad's position is checked against its intended placement when the board is
    built.
- **Electrical margins:**
  - Boost worst case at 3.0 V: 278 mA peak, against a 1.2 A limit and 1.3 A saturation.
  - VOUT 15.2 V max, 20.8 V under OVP.
  - Bank FETs are rated 30 V against VOUT ≤ 39 V minus the string.
  - Schottky 40 V ≥ OVP max 39 V.
  - Output capacitors 50 V.
  - Charger input 30 V abs max.
- **Firmware:** 2.1 KB; host unit tests pass (levels, bank switch with make-before-break,
  3-min auto-off, USB, thermal derate and hysteresis, battery lock-out, NTC table within
  0.2 °C).

## 6. IEC 62471

Method and numbers: [`iec62471.py`](iec62471.py) → `iec62471.json`.
- Bare LEDs at the hardware current ceiling (27.1 mA), viewed from 200 mm.
- All six LEDs of a bank in view at once (the worst case).

| Hazard | 660 nm bank | 625 nm bank | Exempt limit |
|---|---|---|---|
| Retinal thermal, L_R | 1.5 % of limit | 1.2 % | 28 000 / α W·m⁻²·sr⁻¹ |
| Blue light, small source, E_B | 48 % of limit | 38 % | 0.01 W·m⁻² |
| UV, IR eye | none emitted | none emitted | — |
| Skin thermal | in contact: held ≤ 41 °C by the NTC limit | same | — |

**Exempt group.** The limits and weighting functions were taken from secondary sources that
reproduce IEC 62471:2006 Tables 4 and 6. The standard itself was not available here, so
check against it before relying on this result. The LEDs' radiant power is an estimate
from luminous intensity (§8, item 1). The blue-light margin is the smaller one; it holds
unless the true power is more than about 2× the estimate.

## 7. Cost

| | USD |
|---|---|
| Parts, Digi-Key | 24.57 |
| Parts, LCSC | 9.31 |
| Parts, Adafruit | 2.25 |
| PCB, 5 boards (estimate) | 5–15 |
| **One device** | **41–51** |
| UPDI programmer (tool) | 6.95 |

Shipping and filament (about 30 g of PETG) are not included.

## 8. Bench checks for the first build

| # | Check | How | Pass |
|---|---|---|---|
| 1 | LED optical power | photodiode / lux meter at 100 mm on axis, one LED at 20 mA | 660 nm ≥ 8 mW (the estimate is 12 mW) |
| 2 | LED current at each level | 1 Ω shunt in series with R9's ground, or VOUT current | 9 / 16 / 23 mA (A), 10 / 17 / 25 mA (B) ± 10 % |
| 3 | Charge current and termination | USB meter | 223–268 mA; stops near 25 mA |
| 4 | NTC vs face temperature | thermocouple taped on the face next to the hottest LED pocket, full power on a skin phantom (or your arm) for 20 min | set the firmware limits so the face stays ≤ 41 °C |
| 5 | Button force and click | kitchen scale under the stone | 2–5 N, click felt |
| 6 | Magnet closure | luggage scale | ≥ 15 N |
| 7 | Sleep current | µA meter in the cell lead | ≤ 10 µA |
| 8 | Runtime | full brightness from full charge | ≥ 45 min (expect > 4 h) |
| 9 | Seam and window light leaks | dark room, device on a sheet of paper | no light around the sole's edge |
| 10 | Vein visibility | forearm, room light and dimmed | veins visible at the rim |
