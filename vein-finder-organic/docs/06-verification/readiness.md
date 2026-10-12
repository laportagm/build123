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
| 1 | Safety-critical firmware | PASS (simulated); hardware validation open | this chunk |
| 2 | Firmware reliability | pending | |
| 3 | PCB and manufacturing integrity | pending | |
| 4 | Mechanical and electrical integration | pending | |
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
| N05 | Auto-off and hold timing rest on the 32 kHz oscillator's accuracy | risk | 2 | |
| N06 | No tests for debounce glitches or the tap/hold boundary | test gap | 2 | |
| N07 | VBUS-sense input level against the MCU's high threshold with a full cell | hardware risk | 4 | |
| N08 | Nothing checks schematic, PCB, BOM, fab files and order pack against each other; the order pack's board facts were copied by hand | gap | 3 | |
| N09 | Silkscreen line width against the fab's minimum | fab risk | 3 | |
| N10 | USB-C pads 0.20 mm from the board edge (the 0.3 mm rule's one exception) | documented exception | 3 | |
| N11 | R29: the board is not rerouted | documented decision | 3 | |
| N12 | Brown-out detector off (default fuses) | optional improvement | 2 | |
| N13 | The PR text counts 30 review findings; there were 29 | doc error | 5 | |
| N14 | With the button held down, the MCU stays out of power-down (it waits for the release); the LEDs stay off | reliability (battery drain) | 2 | found in chunk 1 |
| N15 | At turn-off, CTRL goes low and both gates open together, while the driver runs for up to 2.5 ms more. VOUT may rise toward the 36–39 V open-LED limit. The parts are rated for it ([electronics §2](../03-electronics/electronics.md#2-circuit)) | hardware risk | 1 → bench | bench item 16 |

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
