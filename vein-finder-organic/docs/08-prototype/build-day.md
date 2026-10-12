# Build-day checklist

> **Personal prototype for bench evaluation. Not a cleared medical device.**
> Not for diagnosis, treatment or clinical use. Lithium cell inside: never short, puncture
> or heat it; charge it only in this device or a proper Li-ion charger.

This list follows the [build guide](../05-build/build.md) section by section (§1 print,
§2 solder, §3 program and test, §4 assemble, §5 first use). It folds in the tests of the
[prototype checklist](checklist.md) at the point where each can first be run.
- Write each measurement in the [bench data sheet](bench-sheet.md); its row IDs are given
  as → **A-2.9** and so on.
- Numbers come from the files cited in brackets: [chk 2.9] is checklist 2.9, [item 2] is
  verification §8 item 2.

**Marks:**

| Mark | Meaning |
|---|---|
| **[CL]** | Powered from the bench supply with a current limit, wired to the cell pads: **3.70 V, 50 mA limit** for first power-up, then **300 mA** [chk Stage 2, 2.4]. |
| **[Li]** | The lithium cell is connected or handled. Never short its leads; keep the iron off the pouch and its leads; insulate the free lead while you solder the other. |
| ⚠ | Safety test. |
| ⛔ | Stop condition. Stop at the first one and follow its action before anything else [chk rule 2]. |
| **GATE** | Nothing after it starts until it passes. |

**Two departures from the build guide's order, on purpose:**
- **The cell goes on later.** Build §3.1 solders the cell first. Here the board runs from
  the current-limited supply until the electrical safety tests pass, and the cell goes on
  at step 3.14 [chk 2.17]. A fault then trips the supply's limit instead of draining a
  lithium cell into it.
- **The posts go in earlier.** Build §4.2 fits the locating posts; here they go in at
  step 2.5, before any power. Nothing is then soldered on the board with the cell
  connected, except the switch wires (4.4).

**Design, firmware or board changes are not made at the bench.** Where a step says
"return loop", send the data. The change is made in the repository with every gate re-run
([return loop](return-loop.md)), and you re-flash or rebuild from there.

---

## 0. Before the day

- [ ] Checklist Stage 1 is done: 1.1 repository gate, 1.2 images, 1.3 parts, 1.4 DFM,
  1.5 N19, 1.6 prints.
- [ ] **Firmware image.** Reference from this packet's gate run at `f2a3eef` (avr-gcc
  14.1.0 from `tools/fetch.sh`), recorded on 2026-10-12. Record your own hashes → **A-1.2**.
  A different toolchain gives different hashes; then the build checks passing is what
  counts [chk 1.2].
  - `fw.hex`: `e8bc8159cc9818c7d966df4100e13fc40109ac126823adff1deda3f43ae3d4e0`
  - `fw_wdt_test.hex`: `2dde15283cf8bb845302e7041c8e6faeb90dc23687c24d615c3e916912323eba`
  - flash 2208 B (`avr-size`)
- [ ] [Print packet](print-packet.md) done: preview checks, then the first-article checks
  → section **P**. No limit exceeded. Exceptions:
  - S5, T2, T3 and B2 need the board, tape and cell: they are done at 2.0;
  - M4 needs the populated board: it is done at 4.4.
- [ ] The equipment in [chk §0] is on the bench.

## 1. Print (build §1)

- [ ] The four parts are printed and cleaned up as in the print packet.
- [ ] **N19 checkpoint (print).**
  - Measure the USB-C lip at least 0.2 mm in from the landing face (S10), and record the
    preview layer count.
  - Photograph the lip through the loupe; GATE N19 (5.4) compares against this photo.
  → **P-S10**

## 2. Solder the board (build §2)

### 2.0 Incoming inspection [chk 2.1]
- [ ] **Board thickness** at the edge: **0.9–1.1 mm** ("boards are 1.0 ± 0.1",
  `params.py` BOSS_PCB_GAP). ⛔ Outside: don't use the board. → **A-2.1a**
- [ ] **Board against the shell's bosses** (T2): the board must be no thicker than the boss
  depth you measured. If it is, the bosses will hold the halves apart by the difference.
  Try another of the five boards; if none fits, record the expected gap for 4.5.
  → **P-T2**
- [ ] **Bare-board fits:** the bare board drops over the four dry magnets in the sole (S5),
  and sits inside the shell's waterline opening without touching (T3). → **P-S5, P-T3**
- [ ] Underside label "PERSONAL PROTOTYPE - NOT A MEDICAL DEVICE" legible (N18). The
  USB-C notch edges are clean.
- [ ] **R9 reads 8.2 Ω** within your meter's stated accuracy. Short the leads first and
  subtract that reading; record the meter.
  - The part is 1 % (`bom.csv`); a handheld meter cannot resolve that.
  - ⛔ A reading off by a factor of 10 (0.82, 82 Ω): wrong reel. → **A-2.1b**
- [ ] LED reels apart: XZM2MR55W-3 (660 nm) is for D2–D7; XZM2CRK55W-3 (625 nm) for
  D8–D13 [build §2 step 9].
- [ ] Magnets: 2 × 8193 and 6 × 8195 are needed [chk 2.1].
- [ ] **[Li] Cell voltage**, meter on the leads: **3.00–4.28 V**, the protection
  circuit's window (readiness §2). ⛔ Below 3.00 V or above 4.28 V: set the cell aside and
  ask. → **A-2.1c**
- [ ] **[Li] Cell thickness** including its protection board, and the **foam tape**.
  - **Tape + cell ≤ 7.40 mm** [item 19; build §4.3].
  - Tape + cell ≤ the bridge's deck height (B2, measured now).
  - ⛔ Over: use thinner tape. If none gets under, stop: the deck would press on the cell.
  → **A-2.1d–f, P-B2**

### 2.1 Top side [build §2 steps 1–8]
Iron ≤ 350 °C.
- [ ] **U3** (TPS61169, SC-70-5, **0.65 mm pitch**): tin one corner pad, pin 1 on the
  silkscreen dot, tack it, flux, drag the rest. Check for bridges under the loupe.
- [ ] **U1** (ATtiny1614): pin-1 dot at the end nearest C3/C4.
- [ ] **U2** (BQ21040), **Q1/Q2** (AO3400A).
- [ ] 0603 resistors and capacitors. **R9 = 8.2 Ω:** check the value before soldering.
- [ ] **D1:** band (cathode) to the silkscreen's cathode mark.
- [ ] **C5, C6** (1206), **C7** (0805), **L1**.
- [ ] **D14–D18**, amber 0603: cathode mark to the GND pad.
- [ ] **J1** (USB-C): the four shell slots first, then the six pads.

### 2.2 Underside [build §2 step 9]
- [ ] D2–D7 = 660 nm, D8–D13 = 625 nm. Each cathode mark to the silkscreen.
- [ ] At most **350 °C for 3 s** per joint, iron off the dome. Tin one pad, slide the LED
  in, then do the other pad.
- [ ] **Leave RT1 off** (build §2 step 10) until step 3.4 [chk 2.2].

### 2.3 Inspect
- [ ] Every joint under the loupe (≥ 5×): no bridges, U3 above all; every part fitted
  except RT1; LED cathodes as on the silkscreen. ⛔ Rework before going on.

### 2.4 Button wires [build §3 step 2]
- [ ] Two 30 AWG wires, about 60 mm, to **TP8 (BTN)** and **TP9 (BTN_GND)**. Touching
  them together is a press. They are fitted now so that every bench test can use them.

### 2.5 Locating posts [build §4.2 steps 1–4, moved before power]
1. Pull six posts from the header strip: two for the mask, four for the bridge. Four if
   the mask is deferred (print packet).
2. Push each through its plated hole from the top. Put the mask and bridge on them to
   square them.
3. Solder underneath, cut flush, and lift the printed parts off.

### 2.6 ⚠ Check before power [build §2 step 11; chk 2.3]
- [ ] Ohms: VBAT–GND (TP4–TP5), VBUS–GND (R5 pin 1 to GND), VOUT–GND (C5).
- **Expect:** VBUS–GND about **300 kΩ** (R5 + R6 + R7). VBAT and VOUT readings climb as
  their capacitors charge.
- ⛔ Any steady reading **under 10 Ω** (PROPOSED in chk M1): find the bridge before any
  power. → **A-2.3a–c**

## 3. Program and test on the bench (build §3)

**[CL] from 3.1 to 3.13.** The board runs from the bench supply wired to TP1/TP2.

- [ ] **3.1 [CL] ⚠ First power-up** [chk 2.4]
  1. Set **3.70 V, 50 mA limit**.
  2. Check the polarity of the leads with the meter.
  3. Connect + to **TP1 (BAT+)** and − to **TP2 (BAT−)**. Watch the current.
  - Record the idle current; no value is documented (M4). → **A-2.4**
  - ⛔ The supply reaches its limit: disconnect at once. Check the polarity, the orientation
    of U1/U2/U3, and for shorts.
  - Then set the limit to **300 mA** for the rest of §3.
- [ ] **3.2 [CL] Program** [build §3 step 3; chk 2.5]
  - UPDI Friend set to **5 V** logic. Only UPDI → **TP3** and GND → **TP5**; leave the
    programmer's power pin unconnected.
  - `make -C fw flash PORT=/dev/ttyACM0`.
  - Accept: pymcuprog reports the write as verified, from the image hashed in §0.
- [ ] **3.3 [CL] ⚠ NTC open**, RT1 not fitted [item 12 b; chk 2.6]
  - Tap 5 times, hold once, tap through the levels.
  - Accept: **the ring LEDs never light**. The seam double-blinks while "on".
  - ⛔ Any ring LED lights: the open-sensor protection fails. Check R8 and U1 pin 11
    (NTC_SENSE). → **A-2.6**
- [ ] **3.4 [CL] Fit RT1, then a smoke test** [build §2 step 10; chk 2.7; firmware §1]
  1. **Disconnect the supply.** Solder RT1. Reconnect at 3.70 V, 300 mA.
  2. Tap: 660 nm at level 1 (40 %). **Read the voltage across R9 now: 66–81 mV** [item 2].
     ⛔ Above 81 mV: tap off and stop. A wrong or bridged R9 would overdrive the LEDs at
     higher levels. → **A-2.9a**
  3. Only then: tap, tap for levels 2 and 3; tap: off.
  4. Tap on, then hold 0.7 s: 625 nm at the same level, and the seam flashes twice.
  5. All 6 LEDs of each string are lit; a faint seam line shows while on.
  - ⛔ A whole string dark: one LED is reversed or open. Turn it off and on (the driver
    latches off on an open string), then fix the LED [build §3 step 6]. Disconnect the
    supply before soldering. → **A-2.7**
- [ ] **3.5 [CL] ⚠ NTC short** [item 12 a; chk 2.8]
  - At level 3, short RT1's pads with tweezers for about 2 s, then let go.
  - Accept: **off within 0.3 s**, seam double-blinking; back on when released.
  - ⛔ Otherwise: stop. Check RT1, R8 and U1 pin 11. → **A-2.8**
- [ ] **3.6 [CL] ⚠ LED current** [item 2; chk 2.9]
  - Meter on mV **across R9** (FB to GND); I = V ÷ 8.2 Ω. Do **not** insert a shunt in R9's
    ground: it sits inside the driver's loop and lowers the current by about 11 %.
  - Read levels 1–3 on 660 nm; hold; read levels 1–3 on 625 nm.

    | Bank | Level 1 | Level 2 | Level 3 |
    |---|---|---|---|
    | 660 nm | 66–81 mV (9 mA) | 118–144 mV (16 mA) | 170–207 mV (23 mA) |
    | 625 nm | 74–90 mV (10 mA) | 125–153 mV (17 mA) | 185–225 mV (25 mA) |

    These are the documented currents ± 10 % [item 2]. The model gives 9.2 / 16.1 /
    23.0 mA and 10.0 / 17.4 / 24.9 mA (`budget.json`).
  - **Also record** the supply current at each level and VOUT at C5. Expected at 3.7 V
    (`budget.json`):
    - supply = battery power ÷ 3.7 V: 660 nm 45 / 75 / 106 mA; 625 nm 50 / 84 / 119 mA;
    - VOUT: 660 nm 12.5 / 12.7 / 12.9 V; 625 nm 13.1 / 13.4 / 13.5 V.
  - ⛔ **Any reading above 246 mV** (the LEDs' 30 mA): power off.
  - If readings are off by one common factor, suspect R9 or the driver's VREF (188–220 mV);
    wrong ratios between levels, the CTRL PWM; a bank at 0, an open string or its FET.
    → **A-2.9a–r**
- [ ] **3.7 [CL] ⚠ VOUT at turn-off** [item 16; chk 2.10]
  - Scope in roll mode, 0.5 s/div. CH1 on C5 + (VOUT), CH2 on Q1's drain.
  - Light 660 nm at level 3, then turn it off with the fourth tap. Repeat, and this time
    end with the RT1 short (the cut-off path).
  - Repeat on 625 nm with CH2 on Q2's drain.
  - Accept: VOUT decays, with **no peak above the VOUT just before the event**; the drains
    stay **below 30 V** (the FETs' rating).
  - Expect: about 12.9 V (660) or 13.5 V (625) before, then a decay.
  - ⛔ Any rise: stop and send the captures (return loop). The pre-authorised fix in item 16
    (keep the gate on one tick after CTRL goes low) is made in the repository with every
    gate re-run; then re-flash and repeat. → **A-2.10a–d**
- [ ] **3.8 [CL] ⚠ Watchdog** [item 15; chk 2.11]
  - `make -C fw flash HEX=build/fw_wdt_test.hex`. Tap and start the stopwatch.
  - Accept: **dark 6 ± 1 s after the tap** (5 s, then the 1 s watchdog), and dark until
    the next tap.
  - Then re-flash the normal image with `make -C fw flash`, verified, and repeat 3.4's taps.
  - ⛔ It never goes dark: stop. **Never leave the test image on the board.** → **A-2.11**
- [ ] **3.9 [CL] ⚠ Stuck button** [item 13; chk 2.12]
  - Light level 1 (660 nm). Twist the TP8/TP9 wires together and start the stopwatch.
    Untwist after 4 min.
  - Accept: the bank switches once at about 0.6 s; **off 162–198 s after the switch**;
    still off after the release.
  - ⛔ Still on past 198 s: the N01 fix does not work on hardware. → **A-2.12**
- [ ] **3.10 [CL] Timing** [item 17; chk 2.13]
  - Auto-off three times: **162–198 s** each (180 s nominal).
  - Five presses of about 0.5 s step the level; five of about 0.7 s switch the bank. The
    hold threshold is 594 ms (535–653 ms) [firmware §1.1].
  - Out of range: record it; no correction is documented (M13). → **A-2.13a–e**
- [ ] **3.11 [CL] Sleep current and held-button current** [items 7, 18; chk 2.14]
  - Meter in series with the supply's + lead. Start on the mA range.
  - **Item 7:** off, button released, wait > 1 min, then switch to µA.
    Accept **≤ 10 µA**; expect ≤ 3.7 µA (the sum of datasheet maxima). Do not tap on the
    µA range.
  - **Item 18:** off, wires joined, read after 10 s on mA. Accept **≤ 1 mA**.
  - Item 7 over: check NTC_EN or a gate stuck high. Item 18 over: record it as N14.
    → **A-2.14a–b**
- [ ] **3.12 [CL] ⚠ Sleep and wake** [item 14 a; chk 2.15]
  - 20 times: leave it alone > 1 min, then one normal tap.
  - Accept: **on at the first tap, 20 of 20**. ⛔ A missed wake: stop; note which try.
    → **A-2.15**
- [ ] **3.13 [CL] Battery warning and cut-off** [chk 2.16; `logic.h` VBAT_*]
  - Light 625 nm at level 3. Lower the supply in 20 mV steps, 5 s apart, reading TP4–TP5.
  - Accept:
    - seam blinks at 1 Hz **below 3.40 V**;
    - LEDs off **below 3.20 V**;
    - a tap at **3.49 V** does nothing; at **3.50 V** it lights.
  - No tolerance is documented (M5): record the trip points.
  - ⛔ No cut-off above **3.00 V** (the cell's own protection): stop.
    The firmware's VDD reading itself cannot be read without the debug UART (bench sheet,
    note U1). → **A-2.16a–d**
- [ ] **3.14 [Li] ⚠ Connect the cell** [build §3 step 1; chk 2.17; N21]
  1. Disconnect the supply.
  2. Check TP1/TP2 against the board figure (`docs/03-electronics/figures/pcb_top.png`),
     and the cell's lead polarity with the meter.
  3. Solder **red → TP1 (BAT+)** and **black → TP2 (BAT−)**, about 40 mm of lead, one
     lead at a time.
  - There is **no reverse-polarity protection**.
  - Accept: a tap lights the LEDs from the cell.
  - ⛔ Reversed: stop and inspect; the charger and MCU may be damaged. → **A-2.17**
- [ ] **3.15 [Li] ⚠ USB wake and charging** [items 14 b and 3; chk 2.18]
  - **Item 14 b:** asleep > 1 min. Scope CH1 on VBUS (R5 pin 1), CH2 on U1 pin 8 (SEAM).
    Plug in USB. Accept: **seam PWM within 0.1 s of VBUS**, and the seam breathes.
  - **Item 3:** leave it charging; read the inline meter every 15 min.
    - Accept **223–268 mA** while charging (245 mA nominal), stopping near **25 mA**
      (24.5 mA, `budget.json`); then the seam is steady.
    - About 3 h is an estimate (M6).
    - **Do not leave it unattended until this has passed.**
  - ⛔ Out of range, or **it never stops**: unplug. Check R3 (2.2 kΩ: I = 540 / R) and U2.
    Charger termination protects the cell. → **A-2.18a–b, A-2.18-t000…t240**
- [ ] **3.16 [Li] USB detected at full charge** [item 21; chk 2.19]
  - Cell full. Plug in the breakout fed with **4.60 V** (or a long thin cable giving
    ≤ 4.6 V at the board). Tap.
  - Accept: seam steady (full); **a tap does not light the LEDs**.
  - Fail: record it. The documented fix (R7 → 200 kΩ, electronics §2) is a board change:
    return loop. → **A-2.19**

**GATE A (bare board).** Every step in §2–§3 passed: each pass/fail row passed, each
record row recorded (readiness §5: stop at the first failure). Otherwise ⛔: stop and send
the sheet (return loop).

## 4. Assemble (build §4)

- [ ] **4.1 Magnets into the sole** [build §4.1]
  - Stack each sole magnet on its partner so they attract. Dot the sole magnet's free face.
  - Glue dot up: 8193 at the horns, 8195 at the tail. Let it cure.
  - Then re-measure S3: the magnet tops must stay **below 2.20 mm (horns) and 1.35 mm
    (tails)** above the waterline face, or they touch the top magnets. Glue under a magnet
    adds height.
  - ⛔ At or over: re-seat it. → **P-S3g**
- [ ] **4.2 Board into the sole** [build §4.2 steps 5–7; item 19]. The posts went in at
  2.5.
  - Lay the board in: the magnets through the board holes, the LEDs into the channels, the
    NTC into its pocket.
  - **Dry fit:** the board lies **flat, without rocking**. The channels leave 0.20 mm a
    side, the NTC pocket 0.225 mm (readiness §4).
  - ⛔ **Never force the board down**: the LEDs would crack the channel walls. Find the part
    that is out of its pocket and re-seat it. → **A-2.20a**
- [ ] **4.3 [Li] Cell onto the board** [build §4.3]
  - Tape + cell **≤ 7.40 mm** and ≤ B2 (from 2.0).
  - One piece of tape inside the "CELL" outline; the cell on it, leads toward the +y arm;
    dress the leads flat.
  - Don't bend or press the pouch. → **A-2.20b**
- [ ] **4.4 [Li] Mask, switch and bridge** [build §4.4]
  1. Mask onto its two posts, over the five amber LEDs: none touched (M4). → **P-M4**
  2. Switch into the bridge's seat, four legs through the holes. Measure B3 now. → **P-B3**
  3. Wires to two diagonally opposite legs; insulate the joints.
     - **The board is live** (the cell is on). Solder only the switch legs, away from the
       board. Keep the iron off the cell and its leads.
  4. Bridge onto its four posts, straddling the cell.
  5. **Shim** with the top shell on: the click must come within the first **0.3 mm**. Add
     0.1 mm paper shims (80 g/m²) under the switch until it does.
  - **Expect about 6–7 shims** if B3 read 16.41 mm: the 0.60 mm seat pocket (print packet
    §5).
  - ⛔ The deck touches the cell: thinner tape. → **A-2.20c–d** (B3, shim count)
- [ ] **4.5 Close** [build §4.5]
  - Top magnets in the horn bosses and at the tail, polarity as in 4.1. Let them cure.
  - Lower the shell straight down: the horn dowels engage, then the halves pull shut.
  - Record any gap at the waterline (M7).
  - ⛔ They won't close: check polarity, stray glue, T2 against the board's thickness, and
    S3. → **A-2.20e**
- [ ] **4.6 Closed-unit re-check** [chk 3.1]: levels, bank switch, USB breathing, unplug.
  As in 3.4. ⛔ Fail: open it and look for a pinched wire or a part that moved. → **B-3.1**

## 5. First use: bench and phantom only, **not on skin** (build §5; readiness §5)

**Order.** This follows checklist Stage 3 with three moves:
- the runtime test (chk 3.9) comes before GATE N19, so the gate's charging check meets a
  cell below full;
- the magnet test (chk 3.3) comes after the gate: a reprinted sole would void it;
- so do the light-leak and thermal tests.

- [ ] **5.0 [Li] Charge fully.** The seam breathes, then glows steady; about 3 h
  (estimate).
- [ ] **5.1 Phantom and thermocouples** [chk 3.0, PROPOSED]
  - Phantom: 2–3 % agar, ≥ 100 × 100 × 30 mm, at **33.5 ± 0.5 °C**, on 20 mm of foam.
  - Thermocouples within **±0.5 °C** of the reference at about 37 °C. → **B-3.0a–c**
- [ ] **5.2 Button force** [item 5; chk 3.2]
  - Stone window-down on a cloth on the kitchen scale; press the dish slowly; read at the
    click; 5 times.
  - Accept **2–5 N (204–510 g)**, click felt.
  - Expect 3.02–3.61 N (308–368 g) once shimmed (checks.json `press_force_N`).
  - Fail: shims. → **B-3.2**
- [ ] **5.3 Runtime** [item 8; chk 3.9]
  - From the full charge of 5.0: 660 nm, level 3, face-up on the bench (not the phantom,
    so derating does not lower the current). Two holds every 2.5 min [chk rule 5].
  - Accept **≥ 45 min** at full brightness. Expect 5.1 h (660) and 4.5 h (625)
    (verification §3).
  - Run on to the battery cut-off if you have the time. Either way the cell is now below
    full, which 5.4 needs. → **B-3.9**
- [ ] **5.4 ⛔ GATE N19 — USB-C plug, bench item 20. Required: it decides N19**
  [item 20; chk 3.4; readiness N19]
  1. Cell below full (after 5.3). With each of 3 cables (one with a bulky plug): plug in
     fully. Each must latch and charge.
     - "Charges" means the seam breathes and the inline meter shows more than **24.5 mA**,
       the termination current.
     - Record the current. The 223–268 mA window applies only while the charger is in
       constant current (`budget.json`), and was already checked in 3.15.
  2. Photograph the lip through the loupe; compare with the §1 photo.
  3. **20 straight in-and-out cycles** with the bulky cable.
  4. Inspect and photograph the lip again.
  - **Pass:** no whitening and no cracks. N19 is confirmed for the lip as printed (P-S10).
  - **Fail:** N19 fails. **Stop here.** Don't use that cable. Send the photos and the
    sheet.
    - If P-S10 (at least 0.2 mm in from the face) read under 0.91 mm, say so: the print,
      not the design, may have failed.
    - The next steps are your call. Checklist 3.4 proposes a reprint at 245 °C (PROPOSED).
      The options beyond that are N19's own, in readiness N19: raise the receptacle or
      deepen the sole, a gate-2 redesign. Nothing changes without you.
  - **Why the gate sits here:** 5.6–5.9 depend on the sole (the magnets glued into it, its
    edge, the NTC window, the LED channels). A reprinted sole would void them, so they wait
    for this pass. → **B-3.4a–e**
- [ ] **5.5 [Li] Charge fully again** before the thermal tests.
- [ ] **5.6 Magnet closure** [item 6; chk 3.3]
  - Luggage scale, 3 pulls. Accept **≥ 15 N (1.53 kg)**.
  - Expect 24.1–25.8 N (2.46–2.63 kg) (verification §1). That model assumes the CAD's
    0.15 mm magnet gap; magnets seated fully in their pockets leave 0.25 mm (print packet
    S3), which pulls less (not modelled). → **B-3.3**
- [ ] **5.7 Light leaks** [item 9; chk 3.5]
  - Dark room, level 3, window-down on white paper, both banks.
  - Accept: no light around the sole's edge; the seam's glow is intended. Photograph any
    leak (M12). → **B-3.5**
- [ ] **5.8 ⚠ Thermal cut-off, end to end** [item 11; chk 3.6]. **3 runs (PROPOSED)**:
  the window-to-NTC offset repeats.
  - Thermocouple taped to the NTC window. Face-up, 660 nm, level 3. Hair dryer on low
    from about 20 cm, or a 45 °C water bag (then judge only the cut-off).
  - Keep it on with two holds every 2.5 min [chk rule 5].
  - Record the thermocouple at the first dimming, at the cut-off (seam double-blinks), and
    when it comes back on.
  - Accept: dims from **about 38 °C**; off **before the thermocouple passes 42 °C**; back on
    after cooling **below 38 °C**.
  - ⛔ No dimming or cut-off: stop; the NTC chain is faulty (e.g. U1 pin 11).
  - ⛔ Cut-off only above 42 °C: thermal paste on RT1 (N20) and repeat. Still failing:
    stop, return loop (limits). → **B-3.6-r1…r3**
- [ ] **5.9 ⚠ Face temperature on the phantom** [item 4; chk 3.7]. Per-minute rows: the
  face-to-window offset log.
  - **Thermocouple 1 on the face at the edge of a lit pocket:**
    - 660 nm run: the 660 nm pocket at +35°;
    - 625 nm run: the 625 nm pocket at +11.7°.
    These are the lit pockets nearest the NTC (`layout.json` LED angles and banks). The
    hottest pocket is not identified (M10).
  - Thermocouple 2 on the NTC window.
  - Face-down on the phantom at 33.5 °C, level 3, 20 min, two holds every 2.5 min. Log
    both thermocouples every minute; note any dimming or double-blink. Cool down between
    banks.
  - Accept: **thermocouple 1 ≤ 41 °C for all 20 min, on both banks.**
  - Expect 36.7–38.0 °C (660 nm) and 35.4–37.0 °C (625 nm) on perfused skin
    (`thermal.json`). The phantom has no blood flow and may run warmer.
  - ⛔ Over 41 °C:
    1. Check thermocouple 1's contact.
    2. Thermal paste on RT1 (N20), then repeat.
    3. Still over: stop, return loop. The documented rule lowers `T_DERATE_DC`,
       `T_LIMIT_DC` and `T_CUTOFF_DC` in `fw/src/logic.h` by the overshoot
       (thermocouple 1's maximum − 41 °C; verification §4). The predictions in `cad/`,
       `calc/` and `ee/` change with them, and every gate is re-run before you re-flash.
    → **B-3.7-A/B rows** and `bench-offset-log.csv`
- [ ] **5.10 ⚠ Optical power** [item 1; chk 3.8]
  - Spare LEDs at **20.0 mA** (constant current, or 5 V through 150 Ω); sensor 100 mm
    on axis; dark room; 3 LEDs of each type.
  - Set the meter's wavelength to 660 nm for XZM2MR55W-3. For XZM2CRK55W-3, Digi-Key
    gives "625 nm" and a 640 nm peak (order list F10): record the setting you used.
  - Accept:
    - 660 nm **≥ 8 mW** (≥ 1.5 W/m² or ≥ 71 lx at 100 mm, under optics.py's 40° beam);
    - **≤ about 24 mW (about 220 lx)**, 2× the estimate, which the IEC 62471 result
      holds to (verification §6);
    - 625 nm: record (M11).
  - Expect 12 mW, about 110 lx (660 nm); 2.2–6.6 mW (625 nm).
  - ⛔ Above about 2× the estimate: no eye exposure until `iec62471.py` is re-run with the
    measured power (return loop). → **B-3.8a–f**

**GATE B (phantom).** Every step in §5 passed: each pass/fail row passed, each record row
recorded, and GATE N19 passed (readiness §5). **Send the data sheet back now**
([return loop](return-loop.md)), whether or not you go on.

## 6. Skin: only after GATE A and GATE B (readiness §5, stage C)

It stays a personal prototype.
- [ ] Item 4, briefly on skin, to confirm the phantom result: thermocouple 1 **≤ 41 °C**.
  Stop at once at any discomfort. → **C-4**
- [ ] Item 10, vein visibility: forearm, room light and dimmed; veins visible at the rim
  (record). → **C-10**
