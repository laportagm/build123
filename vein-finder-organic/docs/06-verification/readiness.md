# Readiness record: fixes, evidence and GO / NO-GO

> **Personal prototype for bench evaluation. Not a cleared medical device.**
> Not for diagnosis, treatment or clinical use.

This record covers the fix-and-verify pass of 2026-10-12. It started from `e93df07`.
- Every issue has an ID (N01…). Each change names the issue it fixes, the evidence, and
  its commit.
- **Simulated** means host unit tests, mutation checks or static checks of the compiled
  code. These show that the code matches its specification. They are not evidence of the
  physical, thermal, optical or electrical behaviour of a board.
- **HARDWARE VALIDATION REQUIRED** marks what only a built board can show. No board
  exists yet. The steps are in [verification.md §8](verification.md#8-bench-checks-for-the-first-build).

## Progress

| Chunk | Scope | Status | Commit |
|---|---|---|---|
| 0 | Current state and issue register | done | — (no changes) |
| 1 | Safety-critical firmware | PASS (simulated); hardware validation open | `6863abd` |
| 2 | Firmware reliability | PASS (simulated); hardware validation open | `ab70f86` |
| 3 | PCB and manufacturing integrity | PASS, one warning accepted (silkscreen references) | `a6b9e90` |
| 4 | Mechanical and electrical integration | PASS on the models; one decision open (N19); physical checks listed | this chunk |
| 5 | Final verification, GO / NO-GO | pending | |

## 0. Starting point (`e93df07`)

- **Branch and PR:**
  - The working tree was clean, and HEAD matched origin.
  - PR #1 was open, ready for review and mergeable, with no reviews, comments or CI.
- **Earlier self-review (29 findings):**
  - R01–R28 are fixed. A script confirmed that each fix is present in the source.
  - R29 was deferred on purpose: Freerouting does not know the 0.3 mm edge rule.
    `finish_route.py` enforces it after routing instead, and DRC confirms it.
  - The PR text said 30 findings: that is N13.
- **Baseline:**
  - host tests pass;
  - the AVR build is 2192 B with `-Werror`;
  - the calculator tests pass (11 of 11).

### Issue register

| ID | Issue | Kind | Chunk | Status |
|---|---|---|---|---|
| N01 | A button held down kept resetting the idle count (`logic.c`), so the 3-min auto-off never fired while it was held | defect, safety-relevant | 1 | fixed |
| N02 | The first NTC reading came 250 ms after power-up. A tap in that window lit the LEDs at the full level with no temperature reading | defect, safety-relevant | 1 | fixed |
| N03 | No tests for: a shorted sensor, the exact 41.0 / 38.0 °C boundaries, inputs while hot-locked, safe initial outputs, random input sequences | test gap | 1 | closed |
| N04 | The sleep entry, wake-up and watchdog cannot be host-tested, and the watchdog could not be made to fire on the bench | verification gap | 1 | closed (static check, bench build); hardware open |
| N05 | Auto-off and hold timing rest on the 32 kHz oscillator's accuracy | risk | 2 | documented (±10 %), bench item 17 |
| N06 | No tests for debounce glitches or the tap/hold boundary | test gap | 2 | closed |
| N07 | VBUS-sense input level against the MCU's high threshold with a full cell | hardware risk | 4 | threshold not verified; margin documented; bench item 21, with a ready fix |
| N08 | Nothing checks schematic, PCB, BOM, fab files and order pack against each other; the order pack's board facts were copied by hand | gap | 3 | closed: `ee/check_fab.py` |
| N09 | Silkscreen line width against the fab's minimum | fab risk | 3 | board labels enlarged; references and outlines accepted |
| N10 | USB-C pads 0.20 mm from the board edge (the 0.3 mm rule's one exception) | documented exception | 3 | measured 0.2002 mm; meets JLCPCB's 0.2 mm |
| N11 | R29: the board is not rerouted | documented decision | 3 | evidence recorded: closest copper 0.300 mm |
| N12 | Brown-out detector off (default fuses) | optional improvement | 2 | not needed, reasons documented |
| N13 | The PR text counts 30 review findings; there were 29 | doc error | 5 | |
| N14 | With the button held down, the MCU stays out of power-down (it waits for the release); the LEDs stay off | reliability (battery drain) | 2 | accepted limitation, tested; bench item 18 |
| N15 | At turn-off, CTRL goes low and both gates open together, while the driver runs for up to 2.5 ms more. VOUT may rise toward the 36–39 V open-LED limit. The parts are rated for it ([electronics §2](../03-electronics/electronics.md#2-circuit)) | hardware risk | 1 → bench | bench item 16 |
| N16 | A cell-voltage reading under 18 overflowed 16 bits, giving a random voltage. A reading of 17 gave 0.658 V and a spurious battery lock | defect (error handling) | 2 | fixed |
| N17 | The order pack gave the board size over the 0.1 mm edge line (85.8 × 54.5 mm; the outline is 85.7 × 54.4 mm), and left out the 0.7 / 0.35 mm power-net vias | doc error | 3 | fixed |
| N18 | The board's own "PERSONAL PROTOTYPE – NOT A MEDICAL DEVICE" label was 0.8 mm text with a 0.12 mm stroke, under JLCPCB's published 1.0 mm / 0.153 mm, so it might not print legibly | defect (fab) | 3 | fixed: 1.0 / 0.16 mm |
| N19 | The sole is 0.91 mm thick under the USB-C opening's lip, under the brief's 1.6 mm. It is listed in verification §2, but was missing from the §1 summary and never put to you as a decision | requirement conflict | 4 | **open: needs your decision** (recommend: accept, bench item 20) |
| N20 | The CAD leaves 0.15 mm of air between the NTC body and its 0.7 mm window, which weakens the coupling the 41 °C cut-off relies on | thermal integration risk | 4 | documented; bench items 4 and 11; thermal paste if the offset is large or unsteady |
| N21 | No reverse-polarity protection on the cell pads TP1/TP2; their silkscreen labels are small | assembly risk | 4 | build-guide warning added |
| N22 | The cell stack depends on the foam tape (1.0 or 1.6 mm, unknown) and the real cell thickness: tape + cell ≤ 7.4 mm | measurement | 4 | build-guide step and bench item 19 |

**Order of work:**
- Chunks 1 and 2 change the same firmware files, so they go in order.
- Chunk 4 uses Chunk 3's board data.
- Chunk 5 depends on all of them.

## 1. Safety-critical firmware

**Scope:**
- NTC failure detection and LED shutdown;
- the 41 °C cut-off;
- sleep, wake-up and missed presses;
- the watchdog;
- any path to uncontrolled LED operation.

### What was inspected

- `fw/src/logic.c`, `logic.h`, `main.c`, `fw/test/test_logic.c`.
- The NTC divider and LED driver in `ee/design.py`:
  - RT1 runs from NTC_SENSE to GND, and R8 from NTC_EN to NTC_SENSE.
  - Q1/Q2 are low-side switches with their sources on FB, over a shared R9.
- The compiled power-down entry and watchdog code (avr-objdump).

**Findings:**

| Path | Result |
|---|---|
| Open NTC | full scale, so the fault value, so hot lock: LEDs off (already tested) |
| Shorted NTC, open R8, NTC_EN stuck low | near 0 V, so 70 °C, so hot lock: LEDs off (now tested) |
| Broken joint at the MCU pin, or NTC thermally detached | **cannot be detected** by firmware → bench items 11 and 12 |
| 41 °C cut-off | `>=` at 41.0 °C, released at ≤ 38.0 °C, applied on the tick of the reading (now tested at the exact boundaries) |
| Hot lock against taps, holds, USB replug | holds (now tested) |
| Button held down | **N01**: auto-off defeated |
| First tick after power-up | **N02**: no reading for 250 ms |
| Power-down entry | race-free: pins re-read with interrupts off, SEI immediately before SLEEP (now checked on every build) |
| Wake-up | a press or USB edge wakes; the first tick takes a fresh reading before the logic runs (unchanged; bench item 14) |
| Watchdog | 1 s, fed only by the tick, off only in power-down, where the LEDs are already off (now checked on every build; bench item 15) |
| Driver without a string | not possible in the logic (random-test rule 2). The turn-off order is N15 (bench item 16) |

### Changes

| Issue | Change | File |
|---|---|---|
| N01 | Only a tap or a hold restarts the auto-off count (was: also any tick with the button down) | `fw/src/logic.c` |
| N02 | The first tick after power-up takes the readings (`slow = 15`, as after waking) | `fw/src/main.c` |
| N02 | The logic never drives the LEDs while `t_dc` is unset (defence in depth) | `fw/src/logic.c` |
| N03 | Seven new tests, including random inputs against nine safety rules | `fw/test/test_logic.c` |
| N03 | Mutation check: 16 planted bugs | `fw/test/mutants.py`, `make -C fw mutants` |
| N04 | Static check of the compiled sleep entry and watchdog, run by every `make -C fw` | `fw/tools/check_build.py`, `fw/Makefile` |
| N04 | Watchdog bench-test build. It hangs with the LEDs lit 5 s after they come on. It is compiled only with `-DVF_WDT_TEST` | `fw/src/main.c`, `make -C fw wdt-test` |
| docs | Behaviour, tests and bench items 11–16 | `docs/04-firmware/firmware.md`, `verification.md`, `docs/05-build/build.md` |

No BOM, PCB, CAD or fab-file change.

### Verification (simulated)

| Command | Result |
|---|---|
| `make -C fw test` | all logic tests pass. Includes 3 × 4 M ticks (52 h of device time) of random inputs with 0 rule breaks, with coverage: 1.17–1.33 M lit ticks, 0.46–0.52 M hot-while-on, 864–1101 bank switches, 30–41 stuck presses |
| New tests against the old `logic.c` (`e93df07`) | 10 failures, all where expected: lit 68 ticks before the first reading (N02); a stuck button stays on and rule 5 breaks on 56 k–128 k ticks (N01); rule 0 breaks while there is no reading. The other seven rules pass on both versions |
| `make -C fw mutants` | 16 / 16 planted bugs caught |
| `make -C fw` | 2200 B flash (was 2192), 1 B RAM, `-Werror` clean. Build checks: CLI at 0x0328, pins read, SEI;SLEEP at 0x0340 with 8 instructions under CLI; watchdog 1K-cycle with a SYNCBUSY wait; WDR only in main |
| `check_build.py` against six broken builds | all six caught: a NOP between SEI and SLEEP, pins read before CLI, no CLI, watchdog not fed, an 8 s period, no SYNCBUSY wait |
| Release hex with and without the test hook in the source | byte-identical: the hook never reaches a normal build |

### HARDWARE VALIDATION REQUIRED

These are [verification §8](verification.md#8-bench-checks-for-the-first-build) items:

| Item | Check |
|---|---|
| 4 | NTC-to-face offset |
| 11 | Thermal cut-off, end to end |
| 12 | NTC faults |
| 13 | Stuck button |
| 14 | Sleep and wake, 20 of 20 |
| 15 | Watchdog fires |
| 16 | VOUT at turn-off (N15) |

### Remaining limitations

- The hot lock and the battery lock live in RAM. A reset clears them, so after a reset
  at 39 °C the LEDs may light again, derated to 60 % or less. The 41 °C cut-off still
  applies on the first reading, 16 ms after the reset.
- After the hot lock clears at 38 °C, the LEDs come back on by themselves at the same
  level, as documented.
- A tap shorter than about 30 ms is ignored by design: two 15.6 ms samples.

## 2. Firmware reliability

**Scope:**
- the 3-min auto-off and other timing;
- debounce;
- state transitions;
- power management;
- error recovery.

### What was inspected

`fw/src/logic.c`, `main.c` and `logic.h` again, against [firmware.md](../04-firmware/firmware.md) §1.

| Area | Result |
|---|---|
| Auto-off | 11 520 ticks after the last tap or hold, which is exactly 180.000 s at the nominal tick (chunk 1 fixed the stuck button) |
| Timing source | RTC and watchdog both run from the internal 32 kHz oscillator, ±10 % in the datasheet's feature list (**N05**). Not verified against the full characteristics table, which was not reached; family documents show wider spreads over temperature |
| Debounce | two equal samples. A one-sample glitch is rejected; the shortest tap is 2 samples (31 ms); the hold starts at 38 samples (594 ms). Untested before (**N06**) |
| States | each turn-on starts at level 1 on the last bank; a reset returns to off and 660 nm; USB removal and battery unlock leave it off until a tap. Matches the docs, which did not say all of it |
| Power | every way of turning off ends in power-down once the button is up. A held button keeps the MCU in idle (**N14**) |
| Error recovery | the watchdog (chunk 1); ADC hangs are covered by the watchdog. A cell reading under 18 overflowed (**N16**). Brown-out detector off (**N12**) |
| Brown-out | the cell's protection keeps VDD within 3.00–4.28 V (cell datasheet, in `ee/design.py`), inside the MCU's 1.8–5.5 V at 3.33 MHz. No flash or EEPROM writes. So the BOD is not needed |

### Changes

| Issue | Change | File |
|---|---|---|
| N16 | The cell-voltage conversion moved into the tested logic as `vdd_mv_from_adc()`. Readings outside 1.8–5.5 V return 0, "not measured" | `fw/src/logic.c`, `logic.h`, `main.c` |
| N06 | Nine new tests: debounce, the tap/hold boundary, exact auto-off, auto-off while hot, state memory, battery boundaries, VDD conversion, seam patterns, power | `fw/test/test_logic.c` |
| N06 | A tenth random-test rule: it does sleep when off, unplugged and released | `fw/test/test_logic.c` |
| N06 | Ten more mutants (26 in all) | `fw/test/mutants.py` |
| N05, N12, N14 | Timing table with tolerances; power states; BOD decision; the stuck-button limitation | `docs/04-firmware/firmware.md` |
| — | Bench items 17 (timing) and 18 (current with the button held) | `verification.md` |
| — | The user guide says each turn-on starts at the lowest level on the last wavelength | `docs/05-build/build.md` |

No BOM, PCB, CAD or fab-file change. N14 is documented rather than fixed. Sleeping with
the button held would change the race-free sleep entry, and only a board can validate
that.

### Verification (simulated)

| Command | Result |
|---|---|
| `make -C fw test` | all 23 tests pass (14 before, 9 new). Random runs 3 × 4 M ticks with ten rules, 0 breaks. The new sleep rule was exercised with 0.75–0.94 M asleep ticks per run |
| `make -C fw mutants` | 26 / 26 caught. The new ones include one-sample debounce, a hold one tick late, a release counted as a tap, auto-off a minute early, a bank reset at turn-on, unlock above 3.5 V, a 1.56 s hot blink, never sleeping, and the old VDD guard (2 failing checks) |
| Old VDD code, readings 1–17 | 658–59 497 mV, none of them real; a reading of 17 gives 658 mV, which locks the LEDs off |
| `make -C fw` | 2208 B (was 2200), `-Werror` clean, build checks pass |
| `make -C fw wdt-test` | builds |

### HARDWARE VALIDATION REQUIRED

| Item | Check |
|---|---|
| 7 | Sleep current |
| 14 | Wake on the first tap |
| 17 | Auto-off time and the tap/hold boundary, by stopwatch |
| 18 | Current with the button held (N14) |

### Remaining limitations

- Timing is only as good as the internal oscillator: about ±10 % per the datasheet
  summary, possibly more at temperature extremes.
- With the button held down the MCU idles. The current is unverified, and bench item 18
  limits it to ≤ 1 mA.

## 3. PCB and manufacturing integrity

**Scope:**
- edge clearance, including the autorouter limitation (R29);
- DRC;
- connectivity;
- silkscreen and placement;
- DXF and exports;
- consistency between schematic, PCB, BOM, order pack and fabrication files.

The board was not rerouted, and no part moved.

### What was inspected

KiCad 7.0.11's command line has only export commands: no DRC and no ERC. DRC runs
through the pcbnew Python API, as it did when the board was made. In place of ERC,
the netlist is checked against `design.py`: single-pad nets and unassigned IC pins.

A new read-only script, `ee/check_fab.py`, makes ten checks. On the board at `ab70f86`
the first run found:

| Check | Result |
|---|---|
| 1 DRC as saved | 0 errors, 0 unconnected; 12 warnings, all `lib_footprint_mismatch` on the ring LEDs (documented); same items as the committed report |
| 2 Pours current | refill changes 0.0000 mm² |
| 3 Design = PCB = schematic | 65 footprints, 144 pads, 40 nets; the fresh schematic export = `design.py` = the committed `.net`; no single-pad nets; every IC pin assigned |
| 4 BOM, order pack | regenerate byte for byte |
| 5 Position file | regenerates identically |
| 6 Gerbers, drill | identical apart from creation dates; zip = folder |
| 7 Order-pack facts | **2 mismatches (N17):** size quoted over the 0.1 mm edge line; the 0.7 / 0.35 mm vias on the 12 power-net vias missing |
| 8 Copper to edge | closest outside J1: 0.300 mm (GND pour); J1 signal pads 0.2002–0.2009 mm, shell pads 0.44 mm |
| 9 Outline | PCB vs CAD within 0.0200 mm (the 0.02 mm simplification in `make_pcb.py`); DXF = CAD exactly once its y mirror is undone; the outline is mirror-symmetric to 0.034 mm |
| 10 Silkscreen | all text 0.8 mm with a 0.12 mm stroke and lines 0.12 mm, including the safety label (**N18**), against JLCPCB's 1.0 mm and 0.153 mm |

The first run also failed checks 6 and 9 on two faults in the checker itself, not the
board. Its date filter missed the drill files' date format, and it read the DXF without
undoing its y mirror. Both were fixed before the results above.

**Fab limits** (JLCPCB, the order pack's first example, from its capabilities and
ordering pages; not checked against PCBWay or OSH Park):
- trace to outline 0.2 mm on routed boards;
- silkscreen line 0.153 mm;
- text height 1.0 mm;
- pad to silkscreen 0.15 mm.

### Changes

| Issue | Change | Files |
|---|---|---|
| N08 | `ee/check_fab.py`, read-only, ten checks | new |
| N17 | The order pack quotes the outline's size (85.7 × 54.4 mm, and 85.8 × 54.5 mm over the line) and both via sizes. It also notes JLCPCB's 0.2 mm edge figure and the silkscreen sizes | `ee/make_order.py` → `docs/07-order/order.md`; `electronics.md` |
| N18 | The two underside labels are now 1.0 mm text with a 0.16 mm stroke. Their start positions are 2.25 mm apart. `silk.tidy`, unchanged, then found free spots: the name at the tail (y = 1.25 mm), the prototype label further along it (y = −7.4 mm) | `ee/make_pcb.py` → board, `drc.rpt`, fab files |
| N09 | The references (0.8 / 0.12 mm) and outlines (0.12 mm, KiCad library standard) are kept. Larger references would not fit, and the board figures name every part. Documented in the order pack and `electronics.md` §4 | docs |
| N10, N11 | Measured values and the reasoning recorded | `electronics.md` §4 |

**What the N18 change touched:**
- **Board file:** only the two label texts changed (position and size). One silk line
  endpoint moved by 1 nm when the existing clip re-ran; an unchanged re-run of the finish
  stage does the same.
- **Fab files:** only `B_Silkscreen.gbo` changed. The other 13 Gerber and drill files
  differ only in their date lines. Copper, mask, paste, outline and drill are untouched.
- **Process:**
  - The change was first run on a scratch copy.
  - An unchanged re-run there showed the pipeline is idempotent to within that 1 nm.
  - The new labels were checked on a plot of the underside silkscreen.
- **Not changed:** the BOM, the parts and the placement.

### Verification

| Command | Result |
|---|---|
| `python ee/make_pcb.py --stage finish` | DRC: 12 violations (all the documented `lib_footprint_mismatch` warnings), 0 unconnected, 0 footprint errors; R11's reference still hidden, as before |
| `python ee/make_order.py` | order pack regenerated |
| `python ee/check_fab.py` | **10 of 10 without failures.** Check 10 is a warning for the references only; the labels now pass |
| Six faults planted in a scratch copy | all caught. A pad on the wrong net failed checks 1–3; a moved Gerber coordinate, check 6; a moved position, check 5; a wrong thickness in the order-pack generator, check 7; a moved DXF vertex, check 9 |
| `git status` after the read-only checks | unchanged |

### Remaining limitations

- The fab's own DFM has not been run: the fab sites cannot be reached from here. Upload
  the zip and read its report before paying.
- The USB-C pads meet JLCPCB's 0.2 mm with 0.0002 mm to spare. Another fab may ask to
  pull them back.
- The references may print thin.

## 4. Mechanical and electrical integration

**Scope:**
- the PCB in the enclosure;
- LEDs against their apertures;
- the cell, the USB-C opening, the NTC mounting;
- wiring, fasteners (magnets and posts), clearances and assembly order.

No dimension was invented. Every number below comes from `layout.json`,
`cad/device/params.py`, `checks.json` or a part entry in `design.py`. Anything that only
a part in hand can show is listed as a measurement.

### What was inspected

- **The CAD's own checks** (`build/device/checks.json`, newer than the final
  `layout.json`):
  - no interference among the 13 parts and stand-ins;
  - top shell 1.80 mm minimum;
  - sole floors;
  - magnet pull 24.1–25.8 N.
  These prove the enclosure against the layout.
- **The board against the same layout:** new `ee/check_fit.py`, read-only, 7 checks. All
  pass:

| Check | Result |
|---|---|
| 1 Ring LEDs | all 12 LEDs' pads within 0.0025 mm of their pockets' centre lines, on the underside. The pocket leaves 0.20 mm a side radially for placement error past a maximum-size body |
| 2 NTC | pads within 0.0025 mm. Pocket 3.10 × 1.25 mm around a 1.6 × 0.8 mm body: 0.75 mm along it, 0.225 mm across. **0.15 mm of air** under the 0.70 mm window at nominal heights (N20) |
| 3 Seam LEDs | on the channel positions (0.0000 mm) |
| 4 USB-C | the contact pads put the receptacle face at x = 61.100 (CAD 61.1); the shell slots match the CAD's legs. Opening 9.44 × 3.67 mm around the 8.94 × 3.17 mm shell; a 13.8 mm landing plane 0.1 mm in front of the face |
| 5 Pins, magnets | 6 post holes at the CAD positions (1.0 mm drill; 0.64 mm square posts, diagonal 0.905 mm; printed holes 1.05 mm, reamed if tight, per the build guide). Horn magnet holes 6.75 mm round 6.35 mm magnets |
| 6 Headroom and keep-outs | the original `room.Room` proof, re-run on the 65 as-built courtyards: every top part ≥ 0.3 mm under the shell and clear of the cell, mask, bosses, bridge feet and USB-C |
| 7 Cell stack | board top z 5.18; foam 1.60 mm (the thicker of the two listed); cell 5.40 mm; 0.4 mm to the bridge deck |

Four planted misplacements were all caught, on an in-memory copy (nothing saved):
- an LED moved 0.05 mm;
- the NTC moved 0.05 mm;
- J1 moved 0.2 mm;
- a capacitor moved onto the cell.

**Other interfaces read from the CAD and the part entries:**
- **Button:** an Omron B3F-1020, 5.0 mm tall per its listing, with 0.05 mm nominal gap to
  the membrane. The build guide shims it with paper.
- **Cell:** Jauch LP503040JH+PCM, with 50 mm leads to TP1/TP2 on the +y arm, next to the
  cell's lead end.
- **Button wires:** two 30 AWG wires of about 60 mm.
- **USB-C:** power-only. 5.1 k on CC1 and CC2 (R1, R2) asks a USB-C source for 5 V.
- **N07:** the USB-detect divider's margin against the MCU's input threshold. The 1614's
  threshold was not found in the datasheet extracts that could be reached. The margin is
  worked out for 0.7 × VDD, marked as unconfirmed.
- **N21:** the cell pads have no reverse-polarity protection.

### Changes

| Issue | Change | File |
|---|---|---|
| — | `ee/check_fit.py`: the board as built against the CAD layout, 7 read-only checks | new |
| N19 | The 0.91 mm lip is in §1's summary row as an open decision | `verification.md` |
| N20 | Dry-fit step; thermal paste on RT1 if bench item 4 shows a large or unsteady offset | `build.md` §4.2 |
| N21 | Polarity warning at the cell-soldering step | `build.md` §3 |
| N22 | Measure tape + cell (≤ 7.4 mm) before sticking the cell | `build.md` §4.3 |
| N07 | Margin, consequence and the contingency (R7 → 200 k, after checking the pin's injection limit) | `electronics.md` §2 |
| — | Bench items 19 (fit before closing), 20 (USB-C plug and lip), 21 (USB detection at full charge) | `verification.md` §8 |

**Not changed:** the board, the BOM, the CAD and the fab files. No fit conflict was found
on the models.

### Decision needed (N19)

The USB-C opening's lower lip is 0.91 mm of PETG, under the brief's 1.6 mm wall.
- It is set by the receptacle's height. The mid-mount part hangs 0.61 mm below the board,
  and the plug enters just above the sole's bottom skin.
- **Smallest change: accept it** as a fifth thin spot, like the 1.15 mm pocket behind
  it. The strip is 9.4 × 1.5 mm, held on three sides; the tail is 6.3 mm tall there.
  Bench item 20 checks 20 plug cycles for whitening or cracks.
- The alternative is to move the receptacle up or deepen the sole. That changes the
  skin, the USB-C height and the board, which is a gate-2 redesign.
- This does not block ordering. It only matters once the sole is printed.

### PHYSICAL MEASUREMENT REQUIRED

| # | What | Why | Where |
|---|---|---|---|
| 1 | Foam tape thickness, and the cell's thickness including the PCM | tape + cell ≤ 7.4 mm, or the bridge deck touches the cell | build §4.3, bench 19 |
| 2 | Dry fit of the soldered board in the sole | 0.20 mm a side for an LED off centre, 0.225 mm for the NTC; the board must lie flat | build §4.2, bench 19 |
| 3 | NTC-to-face offset and its steadiness | 0.15 mm air gap; the cut-off thresholds are at the NTC | bench 4, 11 |
| 4 | Button gap and force | 0.05 mm nominal gap; shim | build §4.4, bench 5 |
| 5 | Post fit in the printed holes | 1.05 mm printed holes for a 0.905 mm diagonal; ream if tight | build §1 |
| 6 | Magnet pocket fit and closure force | 0.15 mm diametral clearance, glued; 24–26 N modelled | build §4.1, bench 6 |
| 7 | USB-C plug engagement and the lip | 0.1 mm landing in front of the face; 0.91 mm lip | bench 20 |
| 8 | Mask tops to shell (0.10 mm) and bridge to shell (≥ 0.6 mm) | tight CAD clearances | bench 19 (closing) |
| 9 | USB detection at full charge | unverified input threshold | bench 21 |

### Remaining limitations

- Printed parts will differ from the model. FDM holes come out undersize, and PETG
  shrinks. Only items 1–8 can show the real fit.
- N19 is waiting for your decision.
