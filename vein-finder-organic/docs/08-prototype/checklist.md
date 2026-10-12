# Prototype build and test checklist

> **Personal prototype for bench evaluation. Not a cleared medical device.**
> Not for diagnosis, treatment or clinical use. Lithium cell inside: never short, puncture
> or heat it.

One pass through this list orders, builds and tests the first prototype.

**First unit:** the [build packet](README.md) puts these tests in build order
([build-day checklist](build-day.md)) and records them in the
[bench data sheet](bench-sheet.md), which replaces the results log in §5.

**Where the numbers come from:**
- Every pass/fail number comes from the repository's documents, cited as [doc §x].
- The bench checks keep their numbers from [verification §8](../06-verification/verification.md#8-bench-checks-for-the-first-build)
  ("item 1"–"item 21").
- **MISSING** means the documents give no acceptance criterion; the gaps are listed in §4.
- **PROPOSED** marks a value or method added here, not a documented requirement. Confirm
  or replace it before you rely on it.

**Rules:**
1. Work top to bottom. Tick each box, and write what you measured in the log (§5).
2. **⚠ marks a safety test. Stop at the first ⚠ failure** and follow its "If it fails"
   line before going on.
3. Do not change the PCB, firmware or enclosure unless a test below proves it is needed.
   Then re-run `python ee/check_fab.py`, `python ee/check_fit.py`, `make -C fw test` and
   `make -C fw mutants` before building again.
4. The firmware cannot report the NTC temperature: the TX/RX pads are unused. Judge the
   temperature limits by what the device does (it dims, cuts off, or the seam
   double-blinks), against thermocouples.
5. **Keeping it on for long tests:** the device turns off 3 min after the last tap or hold,
   and a tap at level 3 turns it off. Two holds of about 0.7 s each switch the bank and
   back, keep the level, and restart the 3 minutes [firmware §1]. Do this every 2.5 min in
   3.6, 3.7 and 3.9.

**N19, provisional resolution (2026-10-12).** The sole is 0.91 mm thick under the USB-C
opening's lip, under the brief's 1.6 mm wall.
- It is **accepted provisionally for printing the first prototype**.
- Final acceptance needs test **3.4** (item 20, 20 plug cycles) to pass. That test is
  required, not optional.
- See [readiness N19](../06-verification/readiness.md).

## 0. Equipment

| Item | Used in | Source |
|---|---|---|
| Multimeter with mV, µA and mA ranges | 2.3, 2.9, 2.14, 2.16 | build §1, items 2, 7, 18 |
| Bench supply 0–5 V with a current limit (constant-current mode helps) | 2.4–2.16, 2.19, 3.8 | **PROPOSED**: the docs power the board from the cell. A current-limited supply is safer for first power-up |
| Oscilloscope, 2 channels, 10× probes rated ≥ 50 V | 2.10, 2.18 | item 16 |
| USB-C charger (5 V, ≥ 0.5 A) and an inline USB-C power meter | 2.18, 3.4 | item 3 |
| USB-C plug breakout (VBUS, GND) fed by the bench supply, or a long thin cable | 2.19 | item 21 |
| 3 USB-C cables, one with a bulky plug | 3.4 | item 20 |
| Thermocouple thermometer, 2 channels, fine-wire probes, Kapton tape | 3.6, 3.7 | items 4, 11 (accuracy MISSING, see 3.0) |
| Reference thermometer | 3.0 | **PROPOSED** |
| Skin phantom: agar, warm water bath, 20 mm foam | 3.0, 3.7 | MISSING specification; **PROPOSED** in 3.0 |
| Hair dryer (low setting) or a 45 °C water bag | 3.6 | item 11 |
| Photodiode optical power meter (set to 660 / 625 nm), or a lux meter | 3.8 | item 1 |
| Kitchen scale (1 g); luggage scale | 3.2; 3.3 | items 5, 6 |
| Stopwatch, and a phone that records slow-motion video | 2.11–2.15 | items 13, 15, 17 |
| Calipers (0.01 mm), loupe (≥ 5×) | 1.6, 2.1, 2.2 | build §1, §4.3 |
| Soldering iron ≤ 350 °C, 0.5 mm solder, flux, wick, fine tweezers, flush cutters | 2.2, 2.20 | build §1 |
| Adafruit UPDI Friend (5 V logic), a computer with `pymcuprog` and this repository | 2.5, 2.11 | build §3 |
| 2-part epoxy or CA, isopropyl alcohol, 1.0 mm drill bit, clip or tape, white paper | 1.6, 2.12, 2.20, 3.5 | build §1, items 9, 13 |
| Thermal paste: only if 3.6 or 3.7 calls for it | 3.6, 3.7 | build §4.2 step 7 (N20) |

---

## Stage 1. Pre-order verification and manufacturing approval

### 1.1 Repository gate
- [ ] **Equipment:** the repository at the commit you will build from; KiCad 7.0; the
  toolchain (README).
- **Procedure:** record `git log -1`. Then run:
  - `python ee/check_fab.py`
  - `python ee/check_fit.py`
  - `make -C fw test`
  - `make -C fw mutants`
  - `make -C fw`
- **Accept:** "10/10 checks without failures" (check 10, the silkscreen warning, is
  accepted: readiness N09); "7/7 fit checks pass"; "all logic tests passed"; "26/26
  mutants caught"; "build checks passed".
- **Expect:** the same results as the regression run at `f35a559` [readiness §5].
- **If it fails:** do not order. Something changed after verification; find it with
  `git diff` and resolve it first.

### 1.2 Firmware images
- [ ] **Procedure:**
  - `make -C fw clean all`
  - `make -C fw wdt-test`
  - record `sha256sum fw/build/fw.hex fw/build/fw_wdt_test.hex`
- **Accept:** both build. "build checks passed". `fw.hex` is the one you flash for
  use; `fw_wdt_test.hex` is only for 2.11.
- **Expect:** 2208 bytes of flash (`avr-size`) at `f35a559`.
- **If it fails:** fix the toolchain (README). Never flash an image that failed its build
  checks.

### 1.3 Parts: live check and order
- [ ] **Equipment:** [order pack](../07-order/order.md) and its cart files.
- **Procedure:**
  - Open every line's live page and confirm the exact part number, stock ≥ order
    quantity, and price.
  - Apply order §6:
    - ship the cell by ground;
    - if LCSC lacks the B3F-1020 switch, order the alternate SW402-ND;
    - magnet 8193 is 1/8″ and 8195 is 1/16″;
    - keep the two LED reels apart.
- **Accept:**
  - every line is in stock at its order quantity, with the exact part number (brief:
    in-stock parts only);
  - parts plus PCB cost ≤ $75, shipping excluded (brief).
- **Expect:** Digi-Key $27.31, LCSC $13.35, Adafruit $2.25; device $47.91–57.91, with 11
  ring LEDs of each type ([order list](order-list.md); the order pack's cart has 10: edit
  the two LED lines after uploading). The order pack alone gives $47–57 [verification §7].
- **If it fails:**
  - Out of stock: order the BOM's alternate for that line (`bom.md`, "alternate").
  - No alternate: stop. That is a verified blocker that needs a BOM change.
  - Over $75: record it and decide; it breaks the brief.

### 1.4 PCB: fab settings and DFM approval
- [ ] **Procedure:**
  1. Upload `docs/03-electronics/fab/vein_finder-gerbers.zip`.
  2. Set order §1: 2 layers, **1.0 mm**, 1 oz, HASL or ENIG, 5 boards, no assembly or
     stencil.
  3. Read the fab's DFM report.
- **Accept:**
  - The size reads 85.7 × 54.4 mm (85.8 × 54.5 mm over the outline line).
  - The thickness is set to 1.0 mm.
  - No DFM errors.
  - Only two warnings are acceptable:
    - thin silkscreen references (N09);
    - USB-C pads at 0.2002 mm from the edge (N10), and only if the fab's minimum is
      ≤ 0.20 mm. JLCPCB publishes 0.2 mm.
- **Expect:** JLCPCB accepts it, with the USB-C pads right at its limit.
- **If it fails:**
  - USB-C edge rejected: ask the fab to pull the copper back at the notch, or use a fab
    with ≤ 0.2 mm [order §1]. Changing the board is a last resort; it needs `check_fab` and
    `check_fit` re-run.
  - No 1.0 mm option: use another fab. A 1.6 mm board does not fit the stone.
  - Any other DFM error: stop and investigate.

### 1.5 N19: provisional decision
- [ ] **Procedure:** none. The decision is recorded in readiness N19, electronics §7 and
  verification §1.
- **Accept:** provisional acceptance for this print; 3.4 must pass.
- **If 3.4 fails:** follow 3.4's "If it fails".

### 1.6 Print and inspect the enclosure
- [ ] **Equipment:**
  - Creality K2 Pro, 0.4 mm nozzle;
  - PETG, black and warm grey;
  - `docs/02-cad/3mf/`;
  - calipers, loupe, a 1.0 mm drill bit, a header post.
- **Procedure:**
  1. Print the four parts with the settings in [build §1](../05-build/build.md#1-print).
  2. Turn on "detect thin walls". Before printing, check the preview at the 0.40 mm button
     skin, the 0.7 mm seam and the 0.7 mm NTC window.
  3. Clip out the shell's interior supports.
  4. Inspect:
     - the 12 LED channels are clear;
     - the USB-C opening is clear;
     - the NTC window is a closed rectangle on the sole's skin face;
     - the button skin and seam slot are intact;
     - a header post slides into every 1.05 mm hole (ream with the 1.0 mm bit if not).
  5. Measure the lip under the USB-C opening with calipers (N19), at least 0.2 mm in from
     the landing face. The print mesh gives 0.91–0.95 mm there and 0.87 mm at the face
     itself ([print packet](print-packet.md) S10).
- **Accept:** every documented inspection point holds [build §1], and the posts fit
  snugly. No dimensional tolerances are documented (MISSING); fit is proved in 2.20,
  3.2 and 3.3.
- **Expect:** lip 0.91 mm (checks.json, "usb opening lip").
- **If it fails:**
  - A hole in the NTC window or button skin: reprint (check the thin-wall preview).
  - A channel blocked: clear it by hand or reprint.
  - The lip under 0.91 mm: record it with the slicer's layer count (print packet S10).
    No tolerance is documented, so 3.4 then judges the lip as printed.

**Gate 1:** every box in Stage 1 is ticked. Then order, and print.

---

## Stage 2. Physical assembly and bare-board electrical safety

Until 2.17, the board runs from the bench supply wired to the cell pads (PROPOSED). After
2.4, use 3.70 V with a 300 mA limit.

### 2.1 Incoming inspection
- [ ] **Equipment:** calipers, loupe, multimeter.
- **Procedure:**
  - **PCB:**
    - measure the thickness at the edge;
    - check the underside label "PERSONAL PROTOTYPE - NOT A MEDICAL DEVICE" is legible;
    - check the USB-C notch edges are clean.
  - **Parts:**
    - separate the reels: 660 nm XZM2MR55W-3 goes on D2–D7, 625 nm XZM2CRK55W-3 on
      D8–D13;
    - measure R9 (8.2 Ω);
    - count the magnets: 2 × 8193 and 6 × 8195.
  - **Cell and tape:** measure the cell's voltage, the cell's thickness including its
    protection board, and the foam tape's thickness.
- **Accept:**
  - board 0.9–1.1 mm (`params.py` BOSS_PCB_GAP: "boards are 1.0 ± 0.1");
  - label legible (N18);
  - tape + cell ≤ 7.4 mm [item 19, build §4.3].
- **Expect:** tape 1.0 or 1.6 mm; cell ≤ 5.4 mm (datasheet envelope).
- **If it fails:**
  - Wrong board thickness: do not use the board.
  - Tape + cell > 7.4 mm: use thinner tape. If no tape gets under the limit, stop: the
    bridge deck would press on the cell.

### 2.2 Solder everything except RT1
- [ ] **Procedure:** follow [build §2](../05-build/build.md#2-solder-the-board) steps 1–9.
  - Top side, in order: U3, U1, U2, Q1/Q2, the 0603 parts (**R9 = 8.2 Ω**), D1,
    C5/C6/C7/L1, D14–D18, then J1 (shell slots first).
  - Underside: D2–D13, matched to their reels and cathode marks.
  - **Leave RT1 off** until 2.6 is done.
  - Inspect every joint under the loupe.
- **Accept:** no bridges; every part fitted except RT1; LED cathodes as on the silkscreen.
- **If it fails:** rework before going on.

### 2.3 Short check before power
- [ ] **Equipment:** multimeter (Ω).
- **Procedure:** measure VBAT–GND (TP4–TP5), VBUS–GND (R5 pin 1 to GND) and VOUT–GND
  (C5) [build §2 step 11].
- **Accept:** none is a short. The numeric threshold is MISSING; **PROPOSED:** no steady
  reading below 10 Ω.
- **Expect:** VBUS–GND about 300 kΩ (R5 + R6 + R7). VOUT and VBAT readings climb as their
  capacitors charge.
- **If it fails:** find and clear the bridge before any power.

### 2.4 ⚠ First power-up, current-limited
- [ ] **Equipment:** bench supply, multimeter.
- **Procedure:**
  1. Set 3.70 V and a 50 mA limit (PROPOSED).
  2. Confirm the polarity of the leads with the meter.
  3. Connect + to TP1 (BAT+) and − to TP2 (BAT−). Watch the supply current.
- **Accept:** the supply never reaches its current limit. The idle current is not
  documented (MISSING): record it.
- **Expect:** low mA or less; the MCU is still blank.
- **If it fails:** current at the limit: disconnect at once. Check the polarity, the
  orientation of U1/U2/U3, and for shorts.

### 2.5 Program
- [ ] **Procedure** [build §3.3]:
  1. Set the UPDI Friend to **5 V** logic.
  2. Connect UPDI → TP3 and GND → TP5. Leave the programmer's power pin unconnected.
  3. Run `make -C fw flash PORT=…`.
- **Accept:** pymcuprog reports the write as verified.
- **If it fails:** check the wiring, the 5 V logic setting and the supply.

### 2.6 ⚠ NTC open (item 12 b), with RT1 not fitted
- [ ] **Procedure:** tap 5 times, hold once, and tap through the levels.
- **Accept:** the ring LEDs never light [item 12].
- **Expect:** the seam double-blinks while the device is "on" (the hot lock).
- **If it fails:** stop. The open-sensor protection does not work on this board. Check R8
  and U1 pin 11 (NTC_SENSE).

### 2.7 Fit RT1, then a smoke test
- [ ] **Procedure:**
  1. Solder RT1 [build §2 step 10].
  2. Tap: 660 nm at level 1. Read the voltage across R9 before going higher: 66–81 mV
     (2.9). Above that, tap off and stop: a wrong or bridged R9 would overdrive the LEDs.
     Then tap, tap: levels 2 and 3. Tap: off.
  3. Tap on, then hold 0.7 s: 625 nm at the same level, and the seam flashes twice.
  4. Check all 6 LEDs of each string, and the faint seam line while on.
- **Accept:** the behaviour in [firmware §1](../04-firmware/firmware.md#1-what-it-does).
- **If it fails:** if a whole string is dark, one of its LEDs is reversed or open. Turn
  the device off and on (the driver latches off on an open string), then fix the LED
  [build §3.6].

### 2.8 ⚠ NTC short (item 12 a)
- [ ] **Procedure:** light it at level 3. Short RT1's pads with tweezers for about 2 s,
  then let go.
- **Accept:** off within 0.3 s, seam double-blinking; back on when released [item 12].
- **If it fails:** stop. Check RT1, R8 and U1 pin 11.

### 2.9 ⚠ LED current at each level (item 2)
- [ ] **Equipment:** multimeter (mV).
- **Procedure:**
  1. Probe across R9 (FB to GND). I = V ÷ 8.2 Ω.
  2. Read levels 1–3 on 660 nm, then hold and read levels 1–3 on 625 nm.
  3. Note the supply current at level 3.
  - Do not insert a shunt in R9's ground path. It would sit inside the driver's
    regulation loop and lower the current by about 11 %. This replaces item 2's
    earlier wording.
- **Accept** [item 2]: ± 10 % of the documented currents, never above the LEDs' 30 mA
  (246 mV):

  | Bank | Level 1 | Level 2 | Level 3 |
  |---|---|---|---|
  | 660 nm | 9 mA: 66–81 mV | 16 mA: 118–144 mV | 23 mA: 170–207 mV |
  | 625 nm | 10 mA: 74–90 mV | 17 mA: 125–153 mV | 25 mA: 185–225 mV |
- **Expect** [electronics §5]:
  - 660 nm: 9.2 / 16.1 / 23.0 mA; 625 nm: 10.0 / 17.4 / 24.9 mA.
  - VOUT 12.5–12.9 V (660 nm) and 13.1–13.5 V (625 nm).
  - Supply about 106 mA (660 nm) and 119 mA (625 nm) at level 3 and 3.7 V (battery power
    ÷ 3.7 V).
- **If it fails:**
  - All readings off by the same factor: R9's value or the driver's VREF (188–220 mV).
  - Wrong ratios between levels: CTRL PWM or firmware.
  - One bank reads 0: an open string or its FET.
  - **Any reading above 246 mV: stop and power off.**

### 2.10 ⚠ VOUT at turn-off (item 16)
- [ ] **Equipment:** oscilloscope in roll mode, 0.5 s/div.
- **Procedure:**
  1. Put channel 1 on C5 + (VOUT) and channel 2 on Q1's drain.
  2. Light 660 nm at level 3, then turn it off with the fourth tap.
  3. Light it again, and short RT1 as in 2.8 (the cut-off path).
  4. Repeat on 625 nm with channel 2 on Q2's drain.
- **Accept** [item 16]:
  - VOUT decays and never rises toward the 36–39 V open-LED limit: no peak above the
    VOUT just before the event;
  - the drains stay below the FETs' 30 V rating [electronics §2].
- **Expect:** about 12.9 V (660 nm) or 13.5 V (625 nm) before, then a decay.
- **If it fails:** stop and send the captures ([return loop](return-loop.md)). The fix item 16
  pre-authorises (keep the gate on one tick after CTRL goes low, `fw/src/logic.c`) is
  made in the repository with every gate re-run; then re-flash and repeat this test.

### 2.11 ⚠ Watchdog (item 15)
- [ ] **Procedure:**
  1. `make -C fw flash HEX=build/fw_wdt_test.hex`.
  2. Tap, start the stopwatch, and watch.
  3. Re-flash the normal image with `make -C fw flash` and repeat 2.7's steps 2–3.
- **Accept** [item 15]:
  - dark 6 ± 1 s after the tap, and dark until the next tap;
  - the normal image is back: the write is verified, and its sha256 matches 1.2.
- **Expect:** 6.0 s: 5 s plus the 1 s watchdog, both ±10 % [firmware §1.1].
- **If it fails:** if it never goes dark, the watchdog does not reset the MCU. Stop.
  **Never leave the test image on the board.**

### 2.12 ⚠ Stuck button (item 13)
- [ ] **Procedure:**
  1. Light it at level 1 (660 nm).
  2. Twist the button wires (TP8/TP9) together and start the stopwatch.
  3. Wait 4 min, then untwist.
- **Accept** [item 13, with item 17's tolerance]:
  - the bank switches once, at about 0.6 s;
  - off **162–198 s** after the switch;
  - still off after the release.
- **If it fails:** if it stays on past 198 s, the N01 fix is not working on hardware.
  Stop. Repeated bank switches point to debounce.

### 2.13 Timing (item 17)
- [ ] **Procedure:**
  1. Three times: tap on, start the stopwatch, and time the auto-off.
  2. Then make five presses of about 0.5 s, and five of about 0.7 s while on.
- **Accept** [item 17]: auto-off 162–198 s; 0.5 s presses step the level; 0.7 s presses
  switch the bank.
- **Expect:** 180 s auto-off; the hold threshold is 594 ms (535–653 ms) [firmware §1.1].
- **If it fails:** if it is consistently out of range, the 32 kHz oscillator is outside
  ±10 %, which shifts every time. Record it. No correction is documented (MISSING). The
  safety-relevant timing is the auto-off with a stuck button, tested in 2.12.

### 2.14 Sleep current and held-button current (items 7 and 18)
- [ ] **Equipment:** multimeter in series with the supply's + lead. Start on the mA
  range.
- **Procedure:**
  - **Item 7:** turn it off, release the button, and wait > 1 min. Switch to µA and read.
    Do not tap while on the µA range.
  - **Item 18:** with the device off, join the button wires and read after 10 s, on the
    mA range.
- **Accept:** item 7 ≤ 10 µA; item 18 ≤ 1 mA [items 7, 18].
- **Expect:**
  - item 7 ≤ 3.7 µA: the sum of the datasheet maxima, without the cell's own protection
    circuit;
  - item 18 is unverified [firmware §2.1].
- **If it fails:**
  - Item 7: check whether NTC_EN or a gate is stuck high; measure net by net.
  - Item 18: record it as known limitation N14. It matters only with a stuck button.

### 2.15 Sleep and wake (item 14 a)
- [ ] **Procedure:** 20 times: leave it alone > 1 min, then one normal tap.
- **Accept:** on at the first tap, 20 of 20 [item 14].
- **If it fails:** a missed wake: stop, and record which attempt failed.

### 2.16 Battery warning and cut-off
This check is not in verification §8. The thresholds are documented in firmware §1.
- [ ] **Equipment:** bench supply; multimeter on TP4–TP5.
- **Procedure:**
  1. Light 625 nm at level 3.
  2. Lower the supply in 20 mV steps, 5 s apart, reading TP4–TP5. Note when the seam
     starts to blink at 1 Hz, and when the LEDs go off.
  3. Raise to 3.49 V and tap; then to 3.50 V and tap.
- **Accept** [firmware §1]:
  - the seam blinks below 3.4 V;
  - the LEDs go off below 3.2 V;
  - a tap at 3.49 V does nothing;
  - a tap at ≥ 3.5 V lights.
  The tolerance is MISSING. **PROPOSED:** record the trip points; the cut-off must
  happen above the cell's own 3.00 V protection.
- **If it fails:** with no cut-off at all, the cell's protection circuit is the only
  backstop. Record it, and check the VDD reading (`read_vdd_mv`) before using the cell.

### 2.17 Connect the cell
- [ ] **Procedure** [build §3.1]:
  1. Disconnect the supply.
  2. Check TP1/TP2 against the board figure, and the cell's lead polarity with the meter.
  3. Solder red → TP1 (BAT+) and black → TP2 (BAT−), leaving about 40 mm of lead.
- **Accept:** a tap lights the LEDs from the cell.
- **If it fails:** a reversed cell can damage the charger and the MCU; there is no
  reverse protection. Stop and inspect.

### 2.18 USB wake and charging (items 14 b and 3)
- [ ] **Equipment:** USB-C charger, inline USB-C meter, oscilloscope.
- **Procedure:**
  - **Item 14 b:** with the device asleep (> 1 min), put channel 1 on VBUS (R5 pin 1)
    and channel 2 on U1 pin 8 (SEAM_PWM). Plug in USB.
  - **Item 3:** leave it charging. Read the current every 15 min until it stops.
- **Accept:**
  - item 14 b: seam PWM within 0.1 s of VBUS, and the seam breathes;
  - item 3: 223–268 mA while charging; stops near 25 mA; then the seam is steady
    [items 3, 14].
- **Expect:** 245 mA; terminates at 24.5 mA. About 3 h is an estimate; there is no
  charge-time criterion (MISSING).
- **If it fails:**
  - Current out of range: check the charger's ISET resistor (2.2 kΩ: I = 540 / R) and U2.
  - No breathing: check /CHG (PA5) and VBUS sensing.
  - Charging never stops: unplug, and check the cell and U2. Never leave this charger
    unattended until it has passed.

### 2.19 USB detected at full charge (item 21)
- [ ] **Procedure:**
  1. Wait until the cell is full (2.18).
  2. Plug in the breakout fed with 4.60 V (or a long thin cable that gives ≤ 4.6 V at the
     board).
  3. Tap.
- **Accept:** the seam is steady (full), and a tap does not light the LEDs [item 21].
- **If it fails:** the documented fix is R7 → 200 kΩ, after checking the pin's injection
  limit [electronics §2]. It affects only the USB-present behaviour, not charging.
  It is a board change: decide whether to make it, through the
  [return loop](return-loop.md).

### 2.20 Mechanical assembly and dry fit (item 19)
- [ ] **Procedure:** follow [build §4](../05-build/build.md#4-assemble).
  1. **§4.1 Magnets:** every pair must attract; sole magnets go in dot up. Let the glue
     cure.
  2. **§4.2 Posts and board:**
     - fit the posts;
     - square them with the mask and bridge, then solder;
     - lay the board in the sole;
     - **dry-fit check.**
  3. **§4.3 Cell:** tape, then the cell, with its leads toward the +y arm.
  4. **§4.4 Mask, button and bridge:**
     - fit the mask;
     - solder the switch on diagonally opposite legs and insulate it;
     - fit the bridge;
     - shim with the top shell on.
  5. **§4.5 Close:** fit the top magnets (polarity), then close.
- **Accept:**
  - the board lies flat without rocking, with every LED and the NTC in its pocket;
  - the mask and bridge are seated;
  - tape + cell ≤ 7.4 mm [item 19];
  - the button clicks within the first 0.3 mm of travel [build §4.4];
  - the halves pull shut. A closed-gap criterion is MISSING: record any gap.
- **If it fails:**
  - Board rocks: re-seat the part that is out of its pocket. Never force the board, or
    the LEDs will crack the channel walls.
  - Bridge touches the cell: use thinner tape.
  - Free play before the click: add 0.1 mm paper shims.
  - Halves won't close: check magnet polarity and stray glue.

**Gate 2:** every box in Stage 2 is ticked, with no ⚠ failure.

---

## Stage 3. Thermal, optical and functional tests on a skin phantom

### 3.0 Phantom and thermocouples
These are **PROPOSED**: the documents do not specify either (MISSING).
- [ ] **Phantom:**
  - 2–3 % agar in water, set in a block ≥ 100 × 100 × 30 mm.
  - Before each run, bring it to **33.5 ± 0.5 °C** (the thermal model's skin temperature
    [verification §4]) in a warm water bath, dry the face, and stand it on 20 mm of foam.
  - It has no blood flow, so it runs warmer than skin. That makes the test conservative.
- [ ] **Thermocouples:** check both against the reference thermometer at about 37 °C.
  Accept them within ±0.5 °C.

### 3.1 Functional re-check after closing
- [ ] **Procedure:** tap through the levels; hold to switch the bank; plug in USB (the
  seam breathes); unplug.
- **Accept:** as in 2.7.
- **If it fails:** open it again and look for a pinched wire or a part that moved.

### 3.2 Button force (item 5)
- [ ] **Equipment:** kitchen scale.
- **Procedure:** put the stone window-down on a cloth on the scale. Press the dish slowly
  with a fingertip and read the scale at the click. Do it 5 times.
- **Accept:** 2–5 N (204–510 g), with the click felt [item 5].
- **Expect:** 3.02–3.61 N (308–368 g) [checks.json `press_force_N`; verification §1].
- **If it fails:** no click, or free play: add a shim. Too stiff: remove a shim. Then
  check the switch seat.

### 3.3 Magnet closure (item 6)
- [ ] **Equipment:** luggage scale, a loop of string.
- **Procedure:** hold the sole down. Loop the string around the top shell's waist, pull
  straight up slowly, and read the peak at separation. Do it 3 times.
- **Accept:** ≥ 15 N (1.53 kg) [item 6].
- **Expect:** 24–26 N (2.5–2.6 kg) [verification §1].
- **If it fails:** check polarity, glue holding the faces apart, and how far each magnet
  is seated. Reglue or replace.

### 3.4 USB-C plug and N19 durability (item 20). **Required: this decides N19.**
- [ ] **Equipment:** 3 USB-C cables (one with a bulky plug), inline meter, loupe, camera.
- **Procedure:**
  1. With the cell below full (after 3.9's runtime run, for example), plug in fully with
     each cable and confirm on the meter that it charges: the seam breathes and the current
     is above the 24.5 mA termination level. Record it. A full cell draws nothing; the
     223–268 mA window holds only in the constant-current phase (2.18).
  2. Photograph the lip under the opening through the loupe.
  3. Make 20 straight in-and-out cycles with the bulky cable.
  4. Inspect and photograph the lip again.
- **Accept:** each cable latches and charges; no whitening or cracks at the lip
  [item 20]. A pass confirms N19.
- **If it fails:**
  1. N19 fails: record it, and do not use that cable.
  2. **PROPOSED**: reprint the sole at the hot end of the PETG range (245 °C) for
     better layer bonding, and repeat 3.4.
  3. If it fails again, N19 is a verified blocker for the next revision. The options
     are N19's own: raise the receptacle or deepen the sole [readiness N19].

### 3.5 Light leaks (item 9)
- [ ] **Procedure:** in a dark room, light level 3 window-down on white paper. Look around
  the sole's edge on both banks.
- **Accept:** no light around the sole's edge [item 9]. The seam's glow is intended.
- **If it fails:** photograph the leak path. No fix is documented (MISSING); **PROPOSED:**
  black tape or paint inside the sole's edge, then repeat.

### 3.6 ⚠ Thermal cut-off, end to end (item 11)
- [ ] **Equipment:** a thermocouple taped on the sole's NTC window; a hair dryer on low
  (or a 45 °C water bag); a stopwatch.
- **Procedure:**
  1. Lie the device face-up at 660 nm, level 3.
  2. Heat the face from about 20 cm. If you use the water bag, judge only the cut-off,
     from the seam.
  3. Keep it on with two holds every 2.5 min (rule 5).
  4. Note the thermocouple reading at the first dimming, at the cut-off (seam
     double-blinks), and when it comes back on as it cools.
- **Accept** [item 11]:
  - dims from about 38 °C;
  - off, with the seam double-blinking, before the thermocouple passes 42 °C;
  - back on after cooling below 38 °C.
- **If it fails:**
  - No dimming or cut-off: stop. The NTC chain is faulty, for example a broken joint at
    U1 pin 11.
  - Cut-off only above 42 °C: the NTC lags the face. Put thermal paste on RT1 (N20) and
    repeat. If it still fails, lower the limits as in 3.7.

### 3.7 ⚠ Face temperature at full power on the phantom (item 4)
- [ ] **Equipment:** the phantom (3.0), 2 thermocouples, a stopwatch.
- **Procedure:**
  1. Tape thermocouple 1 on the face at the edge of a lit pocket nearest the NTC: for
     660 nm the pocket at +35°, for 625 nm the pocket at +11.7° (`layout.json` LED
     angles and banks). The hottest pocket is not identified in the documents (MISSING);
     find it with a thermal camera if you have one.
  2. Tape thermocouple 2 on the NTC window.
  3. Put the device face-down on the phantom at 33.5 °C.
  4. Run 660 nm at level 3 for 20 min, with two holds every 2.5 min. Log both
     thermocouples every minute, and note any dimming or seam double-blink.
  5. Cool it down, move thermocouple 1 to the 625 nm pocket, then repeat on 625 nm.
- **Accept:** thermocouple 1 stays **≤ 41 °C** for all 20 min, on both banks [item 4,
  brief].
- **Expect** [verification §4]: 36.7–38.0 °C at 660 nm and 35.4–37.0 °C at 625 nm on
  perfused skin. The phantom may run warmer.
- **If it fails:**
  1. Check thermocouple 1's contact.
  2. Put thermal paste on RT1 (N20) and repeat.
  3. If it still fails, stop and send the data ([return loop](return-loop.md)).
     `T_DERATE_DC`, `T_LIMIT_DC` and `T_CUTOFF_DC` in `fw/src/logic.h` are lowered by
     the overshoot (thermocouple 1's maximum − 41 °C) [verification §4]. The tests and
     the predictions in `cad/`, `calc/` and `ee/` change with them, and every gate is
     re-run.
  4. Re-flash, then repeat 3.6 and 3.7.

### 3.8 Optical power (item 1)
- [ ] **Equipment:**
  - an optical power meter, or a lux meter;
  - a bench supply in constant-current mode at 20.0 mA (or 5 V through 150 Ω);
  - spare LEDs: 11 of each type are ordered, 6 fitted, so 3 for this test and 2 spare
    ([order list](order-list.md) §1).
- **Procedure:** in a dark room, drive one spare LED at 20 mA with the sensor 100 mm away
  on axis. Measure 3 LEDs of each type.
- **Accept** [item 1]: 660 nm ≥ 8 mW. On axis at 100 mm, under the estimate's 40° beam
  model [optics.py], that is ≥ 1.5 W/m², or ≥ 71 lx.
  - The IEC 62471 exempt result holds up to about 2× the estimate [verification §6]: so
    ≤ about 24 mW (about 220 lx).
  - 625 nm: no minimum is documented (MISSING). Record it.
- **Expect:**
  - 660 nm: 12 mW, about 110 lx (1095 mcd, from one listing);
  - 625 nm: 2.2–6.6 mW (model bracket).
- **If it fails:**
  - 660 nm under 8 mW: the rim light (modelled at about 1.5× the room-light veil) drops.
    Record it, and expect to need a dimmer room.
  - Above 2× the estimate: re-run `iec62471.py` with the measured power before any eye
    exposure.
  - Lux meters are often inaccurate in deep red: prefer the photodiode meter.

### 3.9 Runtime (item 8)
- [ ] **Procedure:**
  1. Charge fully, as in 2.18.
  2. Run 660 nm at level 3 face-up on the bench, not on the phantom, so that thermal
     derating does not lower the current.
  3. Keep it on with two holds every 2.5 min.
  4. Time 45 min. Optionally carry on to the battery cut-off.
- **Accept:** ≥ 45 min at full brightness [item 8, brief].
- **Expect:** 5.1 h at 660 nm and 4.5 h at 625 nm [verification §3].
- **If it fails:** check the currents (2.9), the supply current, the cell's charge
  (2.18) and the cut-off point (2.16).

### 3.10 Optional: vein phantom (no criterion)
- [ ] **PROPOSED**, not in the documents:
  - Make an agar phantom with milk or lipid emulsion for scattering, and 2–3 mm tubes of
    diluted dark ink at 2–4 mm depth.
  - Photograph it at 500 lx and 100 lx, the room lights in the optics model.
- **Accept:** record only (MISSING). The documented acceptance, item 10, uses a forearm
  and comes after the skin gate.

**Gate 3:** every box in Stage 3 is ticked, with no ⚠ failure and 3.4 passed.

**Then the skin-contact gate** [readiness §5, stage C]. Only after Stages 2 and 3 have
passed:
- item 4, briefly on skin, to confirm the phantom result;
- then item 10, vein visibility.

It stays a personal prototype.

---

## 4. Missing acceptance criteria

| # | Test | What the documents do not define | Handling here |
|---|---|---|---|
| M1 | 2.3 | A numeric "short" threshold | PROPOSED: no steady reading < 10 Ω |
| M2 | 2.1 | PCB thickness tolerance | Found in `params.py` (BOSS_PCB_GAP: "boards are 1.0 ± 0.1"); no longer missing |
| M3 | 1.6 | Printed-part dimensional tolerances | Fit tests 2.20, 3.2 and 3.3 decide |
| M4 | 2.4 | Current at first power-up | Record only |
| M5 | 2.16 | Tolerance on the 3.4 / 3.2 / 3.5 V thresholds | Record; the cut-off must be > 3.00 V (cell protection) |
| M6 | 2.18 | Charge time | Record (about 3 h estimated) |
| M7 | 2.20 | Closed gap at the waterline | Record |
| M8 | 3.0 | Skin-phantom specification | PROPOSED: 2–3 % agar at 33.5 °C on foam |
| M9 | 3.0 | Thermocouple accuracy | PROPOSED: ±0.5 °C against a reference |
| M10 | 3.7 | Which LED pocket is hottest | PROPOSED: the lit pocket nearest the NTC (660 nm at +35°, 625 nm at +11.7°), or a thermal camera |
| M11 | 3.8 | 625 nm optical power minimum | Record; IEC check as for 660 nm |
| M12 | 3.5 | Remedy for a light leak | PROPOSED: black tape or paint inside the edge |
| M13 | 2.13 | What to do if timing is outside ±10 % | Record |
| M14 | 3.10 | Vein visibility on a phantom | Record only |
| M15 | — | Seam brightness and visibility | Judged by eye |

**Documentation corrected with this checklist:**
- **Item 2's method:** the "1 Ω shunt in series with R9's ground" would lower the
  current it measures. It now reads the voltage across R9.
- **Item 13's tolerance:** ± 10 s became 162–198 s, consistent with item 17 and the
  ±10 % oscillator.

## 5. Results log

For the first unit, use the [bench data sheet](bench-sheet.md) instead: it has a row
per measurement.

| Test | Measured | Pass / fail | Date | Notes |
|---|---|---|---|---|
| 1.1 repository gate | commit: | | | |
| 1.2 images | sha256: | | | |
| 1.3 parts | total $: | | | |
| 1.4 DFM | warnings: | | | |
| 1.6 print | lip mm: | | | |
| 2.1 incoming | board mm; tape mm; cell mm, V: | | | |
| 2.3 shorts | VBAT / VBUS / VOUT Ω: | | | |
| 2.4 power-up | mA: | | | |
| 2.6 NTC open | | | | |
| 2.8 NTC short | | | | |
| 2.9 LED current | mV A: / / ; B: / / ; supply mA: | | | |
| 2.10 VOUT | V before / peak after: | | | |
| 2.11 watchdog | s: | | | |
| 2.12 stuck button | s: | | | |
| 2.13 timing | s: / / | | | |
| 2.14 currents | µA: ; mA: | | | |
| 2.15 wake | n / 20: | | | |
| 2.16 battery | V warn / off / on: | | | |
| 2.18 charging | mA: ; end mA: ; h: | | | |
| 2.19 USB at full | | | | |
| 2.20 assembly | gap mm: | | | |
| 3.2 button | g: | | | |
| 3.3 magnets | kg: | | | |
| 3.4 USB-C, N19 | cycles: ; lip: | | | |
| 3.5 light leaks | | | | |
| 3.6 cut-off | dim °C / off °C / on °C: | | | |
| 3.7 face | max °C 660 / 625: | | | |
| 3.8 optical | mW or lx, 660 / 625: | | | |
| 3.9 runtime | min: | | | |
