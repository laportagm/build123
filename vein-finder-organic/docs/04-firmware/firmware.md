# Gate 4 — Firmware

> **Personal prototype for bench evaluation. Not a cleared medical device.**
> Not for diagnosis, treatment or clinical use.

ATtiny1614, plain C (avr-gcc 14.1, avr-libc), no Arduino core. Source: `fw/src/`.

| | |
|---|---|
| Size | 2.2 KB (2208 B) flash of 16 KB, 1 byte of static RAM (the state lives on the stack) |
| Clock | 20 MHz oscillator / 6 = 3.33 MHz (the default; valid down to 1.8 V) |
| Tick | RTC periodic interrupt, 1.024 kHz / 16 = 15.625 ms, from the internal 32 kHz oscillator (±10 %; see §1.1) |
| LED current control | TCA0 PWM at 20 kHz on the TPS61169 CTRL pin; the driver turns duty into its feedback reference (analog dimming, no flicker) |
| Hard ceiling | VREF / R9 = 204 mV / 8.2 Ω = 24.9 mA per LED (22.7–27.1 mA over the driver's VREF and resistor tolerance), whatever the code does |
| Sleep | power-down, RTC off, watchdog off: about 0.1 µA (secondary source for the datasheet value); the button, USB power and charger status wake it |
| Tests | host unit tests of all device logic, `make -C fw test` (all pass); 26 planted bugs, all caught, `make -C fw mutants`; checks of the compiled sleep and watchdog code on every `make -C fw` |

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
| Cell < 3.2 V | LEDs off; allowed again at ≥ 3.5 V (after a rest or a charge), then a tap turns them on |
| Turning on | always at level 1, on the bank last used. A reset (power loss, watchdog) returns to off and 660 nm |
| USB removed | stays off, then sleeps |

Levels are fractions of each bank's cap, set as CTRL duty:
- **Bank A, 660 nm:** cap 23 mA, from the concept's thermal study for dark skin (the
  binding case). Duty 92.5 %. At the driver's worst-case VREF this gives 25.1 mA, still
  under the LED's 30 mA rating.
- **Bank B, 625 nm:** cap 24.9 mA, which is the hardware ceiling itself. Duty 100 %.

### 1.1 Timing

Everything counts ticks of the RTC, and the RTC and the watchdog both run from the internal
32.768 kHz low-power oscillator. The ATtiny1614 datasheet's feature list gives it as
±10 %. The times below are nominal, with the ±10 % range in brackets.

| What | Ticks | Time |
|---|---|---|
| Button sample | 1 | 15.6 ms. A press shorter than this is sampled once at most, so it never counts |
| Debounce | 2 equal samples | a level change counts after 31 ms (28–34 ms). The shortest tap is 2 samples |
| Tap / hold boundary | 38 samples down | 594 ms (535–653 ms) is a hold; 37 samples (578 ms) is still a tap |
| Auto-off | 11 520 after the last tap or hold | 180.0 s (162–198 s) |
| NTC and cell readings | every 16 | 250 ms, and on the first tick after power-up or waking |
| Watchdog | 64 ticks' worth | 1.0 s (0.9–1.1 s). It runs from the same oscillator, so it always allows 64 ticks |
| Seam: breathing (charging) | period 192 | 3.0 s |
| Seam: hot | double blink every 125 | 1.95 s |
| Seam: low cell | period 62 | 0.97 s (1.03 Hz) |
| Seam: bank switch | 24 | two flashes in 375 ms |

**Not verified:** the ±10 % figure comes from the datasheet's summary. The full
characteristics table was not reached, and Microchip's family documents give wider
spreads over the full temperature range. Bench item 17 times the auto-off.

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
- **Implausible cell readings:** a VDD reading outside the MCU's 1.8–5.5 V range is
  treated as "not measured" and changes nothing. The cell's protection keeps VDD within
  3.00–4.28 V. Before this guard, a reading under 18 overflowed 16 bits and gave a random
  voltage.

### 2.1 Power

| State | MCU | Wakes on |
|---|---|---|
| Lit | idle sleep between ticks, TCA0 running | every tick |
| Off, button up, no USB | **power-down**, about 0.1 µA (secondary source) plus the board's standby | button, USB power, charger status |
| On USB | idle sleep, ticks running, to show the charge | — |
| Off, button held down | idle sleep: it waits for the release (N14) | the release |

**Known limitation (N14).** While the button is held down, the MCU does not power down.
Sleeping would need the release as the wake source. That means changing the race-free
sleep entry in §2, which only a board can validate. The LEDs stay off, but the idle
current drains the cell.
- The ATtiny1614's idle current at 3.33 MHz was **not verified**. A sibling part, the
  ATtiny816, lists 0.9 mA typical at 8 MHz and 3 V. The button's pull-up adds to it.
- Bench item 18 measures it. The limit set there is ≤ 1 mA, which still leaves at least
  25 days from a full cell.
- Revisit this if a stuck button turns out to be likely in use.

**Brown-out detector: off** (the default fuses), and not needed:
- The cell's protection keeps VDD within 3.00–4.28 V. That is inside the 1.8–5.5 V range
  the MCU is specified for at 3.33 MHz.
- The firmware writes no flash or EEPROM, so a brown-out cannot corrupt stored data.
- Turning it on (BODCFG, sampled mode) is an optional fuse change.
- **Power loss** while the device is lit is like a reset: it comes back off, on 660 nm.


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
make -C fw mutants    # do the tests catch 26 planted bugs in the device logic?
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
- BOD off (§2.1);
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
| debounce | 50 one-sample glitches are ignored; a two-sample press is a tap; a bouncy press is one tap; a one-sample glitch inside a hold neither ends it nor adds a tap |
| tap / hold boundary | 37 samples (578 ms) is a tap, 38 samples (594 ms) is a hold |
| auto-off, exact | off exactly 11 520 ticks (180.000 s) after the last tap, and after a hold that restarted the count |
| auto-off while hot | it still runs while the hot lock holds the LEDs off; cooling afterwards does not relight |
| state memory | each turn-on starts at level 1 on the last bank; USB in and out leaves it off; a reset returns to off and 660 nm |
| battery boundaries | 3.200 V on, 3.199 V off on the same tick, 3.499 V still locked, 3.500 V unlocked but off until a tap; no reading changes nothing |
| VDD reading | known points, range ends, implausible readings give 0, strictly falling over the valid range |
| seam patterns | breathing every 192 ticks between 2 and 30 %; steady when full; faint line when on; two flashes on a bank switch; 1.03 Hz low-cell blink; a double blink every 125 ticks when hot |
| power | sleeps after each way of turning off (tap, auto-off, battery lock, unplug); awake on USB; with the button held it stays off but does not sleep (N14) until the release |
| random | 3 × 4 million ticks (52 h) of random button, USB, temperature, sensor-fault and battery inputs. Ten rules, written from the specification, are checked after every tick: no light when hot, low, on USB, without a reading or off; never above the derated cap; never the driver without a string; never a gate without the driver; overlap ≤ 1 tick; never lit 3 min after the last use; only sleep when dark and idle; the right bank; a valid level; and it does sleep when off, unplugged and released |

`make -C fw mutants` plants 26 small bugs in `logic.c`, one at a time. Examples are a
wrong comparison at 41 °C, a missing auto-off, debouncing on one sample, a hold one tick
late, or a bank that resets at turn-on. It checks that the tests catch every one.

**These are simulations.** They show that the logic does what the specification says
for the inputs it is given. They say nothing about the board.

**HARDWARE VALIDATION REQUIRED** (no board exists yet; verification §8 has the steps):
- ADC readings and PWM levels;
- sleep current, and waking on the first press;
- the watchdog firing;
- the NTC's thermal contact and its offset to the face;
- the cut-off on a real heat source;
- VOUT at turn-off;
- the real tick rate, and so the auto-off time;
- the current with the button held down.
