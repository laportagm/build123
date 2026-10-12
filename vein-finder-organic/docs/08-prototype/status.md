# Status before the first build (2026-10-12)

> **Personal prototype for bench evaluation. Not a cleared medical device.**
> Not for diagnosis, treatment or clinical use.

**Nothing has been printed, built or measured.** Everything verified so far is software:
simulation, static checks of the compiled code, and models. **Those are not evidence of
physical, thermal, optical or electrical safety** (readiness §5). The right-hand column
names the bench row that proves each item.

## 1. Verified in software, unproven on hardware

Gate run of 2026-10-12 at `f2a3eef`, the head of PR #1 and the base of this packet: §2.

| Area | Verified in software (evidence) | Unproven on hardware | Bench rows |
|---|---|---|---|
| **Firmware logic**: levels, bank switch, 3-min auto-off, stuck button, debounce, tap/hold, USB, battery lock | 23 host tests pass. 3 × 4 M ticks of random inputs (52 h) against 10 rules, 0 breaks. 26/26 planted bugs caught (`make -C fw test`, `mutants`) | real tick rate (±10 % oscillator, N05); real button; the behaviour on a board | A-2.7, A-2.12, A-2.13a–e, A-2.16a–d |
| **Thermal protection logic**: derate from 38.0 °C, off at 41.0 °C, back on at 38.0 °C; open or shorted NTC locks the LEDs off; no light before the first reading | exact boundary tests; NTC table within 0.2 °C of the Beta model; fault tests (same runs) | ADC readings; a broken joint at U1 pin 11 (undetectable by firmware); the NTC's thermal contact (N20) | A-2.6, A-2.8, B-3.6 r1–r3 |
| **Sleep entry and watchdog** | every build checks the compiled code: race-free CLI → pins → SEI;SLEEP; 1 s watchdog after a SYNCBUSY wait; WDR only in main | the watchdog firing; sleep current; waking on the first tap | A-2.11, A-2.14a, A-2.15 |
| **Firmware image** | 2208 B flash, `-Werror` clean; hashes in §2 | flashing and verify over UPDI | A-1.2a–b, build-day 3.2 |
| **LED current**: 24.9 mA ceiling (VREF / R9), caps 23 / 24.9 mA | `budget.py` reproduces `budget.json`: 9.2 / 16.1 / 23.0 and 10.0 / 17.4 / 24.9 mA | real currents (R9, VREF 188–220 mV, CTRL PWM) | A-2.9a–f |
| **Boost turn-off (N15)** | parts rated for the 36–39 V open-LED limit (30 V FETs see VOUT minus the string) | VOUT at turn-off and at the cut-off | A-2.10a–d |
| **Charging and USB detect (N07)** | 245 mA (223–268), terminates at 24.5 mA (`budget.json`) | real charge current; USB detection with a full cell (input threshold not verified) | A-2.18*, A-2.19 |
| **Face temperature** ≤ 41 °C | `thermal.py` reproduces: 35.4–38.0 °C at full power on perfused skin | the face temperature; the face-to-NTC offset (not modelled, verification §4) | B-3.6, B-3.7, offset log |
| **Optics and IEC 62471** | `optics.py`, `iec62471.py` reproduce: exempt group, 1.2–1.5 % and 38–48 % of the limits (secondary sources) | LED power: the 12 mW / 660 nm figure is an estimate from luminous intensity | B-3.8a–f |
| **Runtime** | 5.1 h (660) / 4.5 h (625) from 600 mAh (`budget.json`) | real runtime | B-3.9 |
| **PCB** | `check_fab.py` 10/10 (DRC 0 errors / 0 unconnected; design = PCB = schematic; fab files regenerate; edge 0.300 mm, J1 0.200 mm); `check_fit.py` 7/7 against the CAD layout | the fab's DFM; board thickness; assembly | checklist 1.4; A-2.1a, A-2.3a–c |
| **Enclosure** | `checks.json`: walls, sole floors, no interference among 13 parts, overhangs, mass 56 g, magnet pull 24.1–25.8 N at the CAD's 0.15 mm magnet gap, button 3.02–3.61 N. The pockets allow a 0.25 mm gap with the magnets fully seated, which is not modelled (`print_dims.json`) | print tolerances; every fit; closure; button force; light leaks | section P; A-2.20a–e; B-3.2, B-3.3, B-3.5 |
| **N19, the USB-C lip** | `checks.json` 0.91 mm; provisionally accepted for printing (readiness N19). The print mesh gives 0.91–0.95 mm from 0.2 mm in, and 0.87 mm at the landing face itself, where the checks.json probe does not reach (`print_dims.json`). **Added to N19's record on 2026-10-12, at your decision**; the acceptance and item 20 are unchanged | 20 plug cycles without whitening or cracks | P-S10, **GATE N19: B-3.4a–e** |
| **Switch seat (N23, new in this packet)** | not modelled. The seat pocket is 0.60 mm deep (`bridge.3mf` has it), but the CAD's stand-in sits on the pedestal top | the play before the actuator (0.65 mm if the switch sits in the seat; click at about 0.90 mm); the shim count | P-B3, A-2.20c–d, B-3.2 |
| **Sourcing** | every BOM line re-checked 2026-10-12 from search snippets ([order list](order-list.md)) | live stock and price at checkout | checklist 1.3 |

## 2. Gate run, 2026-10-12

Branch `claude/vein-finder-build-packet` at `f2a3eef`. The packet adds docs only;
nothing in `cad/`, `fw/`, `ee/` or `calc/` changed.

| Command | Result |
|---|---|
| `make -C fw clean all` | 2208 B text, 1 B bss, `-Werror` clean. Build checks: CLI at 0x030e, pins read, SEI;SLEEP at 0x0326 (8 instructions with interrupts off); watchdog 1K-cycle after a SYNCBUSY wait; WDR only in main |
| `make -C fw test` | all logic tests passed; random seeds 625341585, 2654435769 and 12345, 4 M ticks each, 0 rule breaks |
| `make -C fw mutants` | 26/26 caught |
| `make -C fw wdt-test` | builds |
| `cd calc && python -m pytest -q` | 11 passed |
| `python ee/check_fab.py` | 10/10 without failures; check 10 is the accepted silkscreen warning (N09) |
| `python ee/check_fit.py` | 7/7 |
| `thermal.py`, `iec62471.py`, `budget.py`, `optics.py` | outputs identical to the committed files (`git status` clean) |
| `sha256sum` | `fw.hex` `e8bc8159cc9818c7d966df4100e13fc40109ac126823adff1deda3f43ae3d4e0`; `fw_wdt_test.hex` `2dde15283cf8bb845302e7041c8e6faeb90dc23687c24d615c3e916912323eba` |

## 3. PR #1 and its watchers

- **PR #1:** open and ready for review (not a draft). GitHub reports it mergeable with
  no conflicts against `main` (`mergeable_state: clean`) at head `f2a3eef`. It has no CI
  checks and no reviews. **You merge it**; it has not been merged from here.
- **Scheduled check-in** `trig_01SAH7nDY3B2nv2aUTeR5inf` (one-shot, 20:31 UTC): deleted
  on 2026-10-12 at your request. The four earlier check-ins had already fired and were
  disabled. Nothing scheduled watches PR #1 now.
- **GitHub events:** this session unsubscribed from PR #1 on 2026-10-12.
- **This packet's branch** is built on `f2a3eef`, so its pull request is based on PR #1's
  branch and shows only the packet.
