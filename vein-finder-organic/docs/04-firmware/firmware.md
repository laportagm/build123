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
| Tests | host unit tests of all device logic, `make -C fw test` (all pass); 16 planted bugs, all caught, `make -C fw mutants`; checks of the compiled sleep and watchdog code on every `make -C fw` |

## 1. What it does

| Input | Effect |
|---|---|
| Tap (press < 0.6 s) | off → level 1 (40 %) → level 2 (70 %) → level 3 (100 %) → off |
| Hold (≥ 0.6 s) while on | switch bank, 660 nm ↔ 625 nm, at the same level; the seam flashes twice |
| Hold while off | nothing (no accidental turn-on in a pocket) |
| 3 min after the last tap or hold | off. A button held down (stuck, or pressed in a bag) does not keep it on |
| USB power present | LEDs off; the seam breathes while charging and glows steadily when full |
| NTC ≥ 38 °C | current falls linearly to 20 % of the level at 40 °C |
| NTC ≥ 41 °C | LEDs off, seam double-blinks; back on (same level) once the NTC is ≤ 38 °C |
| No NTC reading yet | LEDs off. The first reading is taken on the first tick, 16 ms after power-up |
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
  - It then re-reads the button and VBUS pins with interrupts off.
  - It sleeps only if neither is active, with SEI immediately followed by SLEEP. The AVR
    always runs the instruction after SEI before it takes an interrupt, so a press that
    arrives after the pin check still wakes the part.
  - `make -C fw` checks this order in the compiled code (`fw/tools/check_build.py`).
- **Hardware defaults:** R10 (100 k) holds CTRL low during reset or with blank flash.
  R11/R12 hold both bank FETs off.
- **Make-before-break:** when switching banks, both strings are on for one tick, then the
  old one goes off. With both strings off and the driver running, VOUT would climb to the
  driver's 36–39 V open-LED protection and latch it off.
- **Watchdog:** about 1 s, running whenever the device is awake. A hung loop resets the
  MCU, and R10 then keeps the LEDs off.
  - The build check confirms the 1 s setting and that only the tick feeds it.
  - `make -C fw wdt-test` builds a bench-test firmware that hangs with the LEDs lit, so
    you can see the watchdog fire (verification §8). It is never for use.
- **Temperature control:** the NTC is read every 250 ms, on the first tick after
  power-up and on waking. The LEDs never light before the first reading. The NTC sits
  0.7 mm under the skin-contact face, just outside the LED ring on the tail side.
  - The limits (38 / 40 / 41 °C) are set below the brief's 41 °C surface limit with about
    1 °C margin.
  - The offset between the NTC and the face hottest spot is **not yet measured**. Gate 5
    has a bench procedure to calibrate it.
  - An open sensor reads at full scale (below about −50 °C on the Beta model). The code
    treats that as over-temperature: LEDs off, seam double-blinks.
  - A shorted sensor reads near 0 V, which converts to 70 °C, so the LEDs lock off too.
    So does an open R8 or NTC_EN stuck low.
  - **Cannot be detected by the firmware:** a broken joint at the MCU's NTC_SENSE pin,
    which leaves the input floating. Neither can an NTC that has lost thermal contact
    with the face. Both are bench checks (verification §8).
- **Stuck button:** only a tap or a hold restarts the 3-min auto-off. A button held
  down cannot keep the light on, and switches the bank at most once.

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
make -C fw            # needs avr-gcc >= 12 with ATtiny1614 support (see README for the toolchain);
                      # also checks the compiled sleep entry and watchdog
make -C fw test       # host unit tests
make -C fw mutants    # do the tests catch 16 planted bugs in the safety logic?
make -C fw flash PORT=/dev/ttyACM0     # pymcuprog over UPDI
make -C fw wdt-test   # watchdog bench test only; flash with HEX=build/fw_wdt_test.hex,
                      # then flash the normal build again
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
| NTC | table against the Beta model, worst 0.20 °C; an open sensor locks the LEDs off |
| init | starts off, driver and gates off, no reading; never lights with no input |
| no reading | taps and holds before the first NTC reading never light the LEDs |
| thermal boundaries | 40.9 °C lit at the floor, 41.0 °C off on the same tick, 38.1 °C still off, 38.0 °C back on |
| hot lock | taps, holds and a USB replug never light the LEDs while locked hot |
| NTC faults | a shorted sensor (70 °C) locks the LEDs off; the conversion is in range and monotonic over all 1024 readings |
| stuck button | one hold, then off 3 min later; stays off; the release is not a tap |
| random | 3 × 4 million ticks (52 h) of random button, USB, temperature, sensor-fault and battery inputs. Nine safety rules, written from the specification, are checked after every tick: no light when hot, low, on USB, without a reading or off; never above the derated cap; never the driver without a string; never a gate without the driver; overlap ≤ 1 tick; never lit 3 min after the last use; only sleep when dark and idle; the right bank; a valid level |

`make -C fw mutants` plants 16 small bugs in `logic.c`, such as a wrong comparison at
41 °C or a missing auto-off. It checks that the tests catch every one.

**These are simulations.** They show that the logic does what the specification says
for the inputs it is given. They say nothing about the board.

**HARDWARE VALIDATION REQUIRED** (no board exists yet; verification §8 has the steps):
- ADC readings and PWM levels;
- sleep current, and waking on the first press;
- the watchdog firing;
- the NTC's thermal contact and its offset to the face;
- the cut-off on a real heat source;
- VOUT at turn-off.
