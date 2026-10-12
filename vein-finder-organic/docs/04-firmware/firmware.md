# Gate 4 — Firmware

> **Personal prototype for bench evaluation. Not a cleared medical device.**
> Not for diagnosis, treatment or clinical use.

ATtiny1614, plain C (avr-gcc 14.1, avr-libc), no Arduino core. Source: `fw/src/`.

| | |
|---|---|
| Size | 2.1 KB flash of 16 KB, 1 byte of static RAM (the state lives on the stack) |
| Clock | 20 MHz oscillator / 6 = 3.33 MHz (the default; valid down to 1.8 V) |
| Tick | RTC periodic interrupt, 1.024 kHz / 16 = 15.6 ms |
| LED current control | TCA0 PWM at 20 kHz on the TPS61169 CTRL pin; the driver turns duty into its feedback reference (analog dimming, no flicker) |
| Hard ceiling | VREF / R9 = 204 mV / 8.2 Ω = 24.9 mA per LED (22.7–27.1 mA over the driver's VREF and resistor tolerance), whatever the code does |
| Sleep | power-down, RTC off, watchdog off: about 0.1 µA (secondary source for the datasheet value); the button, USB power and charger status wake it |
| Tests | host unit tests of all device logic: `make -C fw test` (all pass) |

## 1. What it does

| Input | Effect |
|---|---|
| Tap (press < 0.6 s) | off → level 1 (40 %) → level 2 (70 %) → level 3 (100 %) → off |
| Hold (≥ 0.6 s) while on | switch bank, 660 nm ↔ 625 nm, at the same level; the seam flashes twice |
| Hold while off | nothing (no accidental turn-on in a pocket) |
| No press for 3 min | off |
| USB power present | LEDs off; the seam breathes while charging and glows steadily when full |
| NTC ≥ 38 °C | current falls linearly to 20 % of the level at 40 °C |
| NTC ≥ 41 °C | LEDs off, seam double-blinks; back on (same level) once the NTC is ≤ 38 °C |
| Cell < 3.4 V under load | seam blinks at 1 Hz |
| Cell < 3.2 V | LEDs off; allowed again at ≥ 3.5 V (after a rest or a charge) |

Levels are fractions of each bank's cap, set as CTRL duty:
- **Bank A, 660 nm:** cap 23 mA, from the concept's thermal study for dark skin (the
  binding case). Duty 92.5 %. At the driver's worst-case VREF this gives 25.1 mA, still
  under the LED's 30 mA rating.
- **Bank B, 625 nm:** cap 24.9 mA, which is the hardware ceiling itself. Duty 100 %.

## 2. Safety-relevant behaviour

- **Driver off really means off.** A compare value of zero still gives a one-clock pulse
  every PWM period. That would be 0.6 % duty, and the TPS61169 would stay on. The code
  therefore disconnects the waveform and drives CTRL low. Low for more than 2.5 ms shuts
  the driver down, drawing under 2 µA.
- **Before sleeping:** the code drives CTRL, both bank gates and NTC_EN low.
- **Hardware defaults:** R10 (100 k) holds CTRL low during reset or with blank flash.
  R11/R12 hold both bank FETs off.
- **Make-before-break:** when switching banks, both strings are on for one tick, then the
  old one goes off. With both strings off and the driver running, VOUT would climb to the
  driver's 36–39 V open-LED protection and latch it off.
- **Watchdog:** about 1 s, running whenever the device is awake. A hung loop resets the
  MCU, and R10 then keeps the LEDs off.
- **Temperature control:** the NTC is read every 250 ms and on waking. It sits 0.7 mm
  under the skin-contact face, just outside the LED ring on the tail side.
  - The limits (38 / 40 / 41 °C) are set below the brief's 41 °C surface limit with about
    1 °C margin.
  - The offset between the NTC and the face hottest spot is **not yet measured**. Gate 5
    has a bench procedure to calibrate it.

## 3. Pins and peripherals

| Pin | Function | Configuration |
|---|---|---|
| PA0 | UPDI | programming pad TP3 |
| PA1 | NTC_SENSE | AIN1, digital input disabled |
| PA2 | NTC_EN | output, high only during a reading (200 µs settle) |
| PA3 / PA4 | GATE_A / GATE_B | outputs to Q1 / Q2 |
| PA5 | /CHG | input, pull-up (BQ21040 open drain), both-edge wake |
| PA6 | BTN | input, pull-up, both-edge wake (fully asynchronous pin) |
| PA7 | VBUS_SENSE | input (100 k / 200 k divider: 3.33 V at 5 V), both-edge wake |
| PB0 | LED_CTRL | TCA0 WO0, 20 kHz single-slope PWM |
| PB1 | SEAM | TCA0 WO1, same timer |
| PB2 / PB3 | TX / RX | debug pads, pulled up when unused |

**Battery voltage:** the MCU runs from the cell, so it reads its own VDD against the internal
1.1 V reference: VDD = 1.1 V × 1023 / reading. No divider is needed.

**Temperature:** the reading is ratiometric (ADC reference = VDD = divider supply). A table
generated from the NTC's Beta model by `fw/tools/ntc_table.py` converts it, with a worst
error of 0.20 °C over 5–65 °C (unit test).

## 4. Build and flash

```sh
make -C fw            # needs avr-gcc >= 12 with ATtiny1614 support (see README for the toolchain)
make -C fw test       # host unit tests
make -C fw flash PORT=/dev/ttyACM0     # pymcuprog over UPDI
```

**Programmer:** Adafruit UPDI Friend (5879), set to **5 V** logic.
- Wire only TP3 (UPDI) and TP5 (GND). TP4 (VBAT) is for measuring.
- Program with the cell connected: the board takes its power from the cell (3.0–4.2 V),
  and a 3 V adapter's input would see up to 4.2 V. The UPDI pin itself tolerates the
  adapter's 5 V.

The default fuses are fine:
- UPDI on PA0;
- BOD off;
- 20 MHz oscillator.

## 5. Tests (`fw/test/test_logic.c`)

| Test | Checks |
|---|---|
| levels | tap sequence and the duty at each level |
| bank switch | hold switches the bank, overlap is exactly one tick, hold while off does nothing |
| auto-off | still on just before 3 min, off just after |
| USB | LEDs off while USB is present, taps ignored, seam modes, sleeps once unplugged |
| thermal | derating curve, cut-off at 41 °C, hysteresis back to 38 °C |
| battery | warning, cut-off, lock-out and unlock |
| NTC | table against the Beta model, worst 0.20 °C |

Not tested on hardware yet (no board exists): ADC readings, PWM levels and sleep current.
Gate 5 lists the bench checks.
