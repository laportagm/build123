"""
Electronics source of truth (gate 3): every part, its nets, footprint, placement and
sourcing.  The schematic writer, the PCB builder, the BOM and the firmware pin map are all
generated from this file.

Personal prototype for bench evaluation - NOT a medical device.

Coordinates for `place` are the device frame of the CAD (mm, window centre at the origin,
+x toward the tail, +y to the left), PCB bottom face at the waterline.  Angles are
device-frame CCW degrees.  side "B" = bottom (skin side, inside the sole's pockets).
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAYOUT = json.loads((ROOT / "build" / "device" / "layout.json").read_text())


@dataclass
class Part:
    ref: str
    value: str
    lib_id: str
    footprint: str
    pins: dict
    block: str = ""
    side: str = "F"
    place: tuple | None = None          # (x, y, angle) device frame
    mpn: str = ""
    mfr: str = ""
    dist: str = ""
    dist_pn: str = ""
    url: str = ""
    price: float | None = None          # USD, unit price at the order quantity
    qty_order: int = 1
    verify: str = ""                    # how the listing/price was verified
    datasheet: str = ""
    dnp: bool = False
    on_board: bool = True
    note: str = ""
    alt: str = ""                       # alternate source (distributor, part number, price)
    h: float = 0.0                      # mm, seated height (keep-out against the shell interior)


PARTS: list[Part] = []


def add(*a, **k):
    p = Part(*a, **k)
    PARTS.append(p)
    return p


# ----------------------------------------------------------------------------- pin map
# ATtiny1614 (SOIC-14).  Chosen for: runs straight off the cell (1.8-5.5 V), UPDI needs one
# pad, TCA0 gives 2 PWM outputs on PB0/PB1, PA6 is a fully asynchronous pin (button wake).
MCU_PINS = {
    "1": "VBAT", "14": "GND",
    "10": "UPDI",        # PA0
    "11": "NTC_SENSE",   # PA1  AIN1
    "12": "NTC_EN",      # PA2  divider supply (off in sleep)
    "13": "GATE_A",      # PA3  bank A (660 nm) low-side switch
    "2": "GATE_B",       # PA4  bank B (625 nm) low-side switch
    "3": "CHG_STAT",     # PA5  charger /CHG (open drain, internal pull-up)
    "4": "BTN",          # PA6  async pin: wake from power-down
    "5": "VBUS_SENSE",   # PA7  USB present (divided to 2/3)
    "9": "LED_CTRL",     # PB0  TCA0 WO0: boost enable + PWM (analog dimming)
    "8": "SEAM_PWM",     # PB1  TCA0 WO1: status seam
    "7": "DBG_TX",       # PB2  USART0 TXD (debug pad)
    "6": "DBG_RX",       # PB3  USART0 RXD (debug pad)
}

FW_PINS = {v: k for k, v in MCU_PINS.items()}

# ----------------------------------------------------------------------------- sourcing
# Verification levels (every page was read through search-engine snippets or aggregators:
# the distributors' own pages could not be opened from this environment, 2026-10-11/12):
#   A  = distributor listing seen (snippet/aggregator): part number, price and stock as quoted
#   D  = datasheet values only (no distributor listing seen)
#   NV = not verified
DK, LCSC, ADA = "Digi-Key", "LCSC", "Adafruit"


def dk(pn):
    return f"https://www.digikey.com/en/products/result?keywords={pn}"


def lcsc(c):
    return f"https://www.lcsc.com/product-detail/{c}.html"


def ada(n):
    return f"https://www.adafruit.com/product/{n}"


FP_R = "Resistor_SMD:R_0603_1608Metric_Pad0.98x0.95mm_HandSolder"
FP_C = "Capacitor_SMD:C_0603_1608Metric_Pad1.08x0.95mm_HandSolder"
FP_C0805 = "Capacitor_SMD:C_0805_2012Metric_Pad1.18x1.45mm_HandSolder"
FP_C1206 = "Capacitor_SMD:C_1206_3216Metric_Pad1.33x1.80mm_HandSolder"

# ----------------------------------------------------------------------------- power: USB-C, charger, cell
add("J1", "USB-C power-only", "Connector:USB_C_Receptacle_PowerOnly_6P", "vf:USB_C_GCT_USB4515-GF-A_MidMount",
    {"A9": "VBUS", "B9": "VBUS", "A12": "GND", "B12": "GND", "A5": "CC1", "B5": "CC2", "S1": "GND"},
    block="power", mpn="USB4515-GF-A", mfr="GCT", dist=DK, dist_pn="2073-USB4515-GF-ACT-ND",
    url=dk("USB4515-GF-A"), price=0.61, qty_order=2,
    verify="A (re-checked 2026-10-12): $0.61 @1, 11,429 in stock (digikey.com page); Mouser $0.67, 4,086 (snippet, PN NV)",
    datasheet="https://gct.co/files/specs/usb4515-spec.pdf", h=1.57,
    note="mid-mount, 1.6 mm offset: hangs 0.61 mm below the 1.0 mm board into the sole")
add("R1", "5.1k", "Device:R", FP_R, {"1": "CC1", "2": "GND"}, block="power",
    mpn="0603WAF5101T5E", mfr="UNI-ROYAL", dist=LCSC, dist_pn="C23186", url=lcsc("C23186"), price=0.0026, qty_order=100,
    verify="A (re-checked 2026-10-12): $0.0015-0.0026 @100+ (cached pages disagree; highest used), 2.4-23 M in stock", alt="LCSC C105580 Yageo RC0603FR-075K1L", h=0.55)
add("R2", "5.1k", "Device:R", FP_R, {"1": "CC2", "2": "GND"}, block="power",
    mpn="0603WAF5101T5E", mfr="UNI-ROYAL", dist=LCSC, dist_pn="C23186", url=lcsc("C23186"), price=0.0, qty_order=0,
    verify="see R1", h=0.55)
add("U2", "BQ21040DBVR", "vf:BQ21040DBV", "Package_TO_SOT_SMD:SOT-23-6",
    {"6": "VBUS", "2": "VBAT", "1": "TS", "4": "ISET", "3": "CHG_STAT", "5": "GND"}, block="power",
    mpn="BQ21040DBVR", mfr="Texas Instruments", dist=LCSC, dist_pn="C202311", url=lcsc("C202311"), price=0.3303, qty_order=5,
    verify="A (re-checked 2026-10-12): $0.2542-0.3303 @5+ (MOQ 5; cached pages disagree; highest used), 960-14,085 in stock; datasheet SLUSCE2D read",
    alt="Digi-Key 296-47315-1-ND, $0.89 @1, 70,422 in stock (snippet)",
    datasheet="https://www.ti.com/lit/ds/symlink/bq21040.pdf", h=1.45,
    note="4.2 V; I = K_ISET/R_ISET = 540/2200 = 245 mA (223-268 mA); input 30 V abs max, OVP 6.6 V")
add("R3", "2.2k", "Device:R", FP_R, {"1": "ISET", "2": "GND"}, block="power",
    mpn="0603WAF2201T5E", mfr="UNI-ROYAL", dist=LCSC, dist_pn="C4190", url=lcsc("C4190"), price=0.0041, qty_order=100,
    verify="A (re-checked 2026-10-12): $0.0018-0.0041 @100+ (cached pages disagree; highest used), 0.47-5.8 M in stock", alt="LCSC C114662 Yageo RC0603FR-072K2L", h=0.55)
add("R4", "10k", "Device:R", FP_R, {"1": "TS", "2": "GND"}, block="power",
    mpn="RC0603FR-0710KL", mfr="Yageo", dist=LCSC, dist_pn="C98220", url=lcsc("C98220"), price=0.0034, qty_order=100,
    verify="A (re-checked 2026-10-12): $0.0014-0.0034 @100+ (cached pages disagree; highest used), 7.7-9.0 M in stock (one copy 0)", alt="Digi-Key 311-10.0KHRCT-ND $0.10 @1", h=0.55,
    note="TS to VSS through 10 k: no pack thermistor (datasheet pin table)")
add("C1", "1u 25V", "Device:C", FP_C, {"1": "VBUS", "2": "GND"}, block="power",
    mpn="CL10B105KA8NNNC", mfr="Samsung", dist=LCSC, dist_pn="C29936", url=lcsc("C29936"), price=0.0225, qty_order=50,
    verify="A (re-checked 2026-10-12): $0.0064-0.0225 @50+ (MOQ 50; cached pages disagree; highest used), 3.0-6.5 M in stock", h=0.9)
add("C2", "1u 25V", "Device:C", FP_C, {"1": "VBAT", "2": "GND"}, block="power",
    mpn="CL10B105KA8NNNC", mfr="Samsung", dist=LCSC, dist_pn="C29936", url=lcsc("C29936"), price=0.0, qty_order=0,
    verify="see C1", h=0.9)
add("R5", "100k", "Device:R", FP_R, {"1": "VBUS", "2": "VBUS_SENSE"}, block="power",
    mpn="RC0603FR-07100KL", mfr="Yageo", dist=LCSC, dist_pn="C14675", url=lcsc("C14675"), price=0.0047, qty_order=100,
    verify="A (re-checked 2026-10-12): $0.0014-0.0047 @100+ (cached pages disagree; highest used), 2.3-8.0 M in stock", alt="LCSC C25803 UNI-ROYAL 0603WAF1003T5E", h=0.55,
    note="VBUS divider 100k / 200k: 5.0 V -> 3.33 V, a valid logic high at VDD 3.0-4.2 V")
add("R6", "100k", "Device:R", FP_R, {"1": "VBUS_SENSE", "2": "VDIV_MID"}, block="power",
    mpn="RC0603FR-07100KL", mfr="Yageo", dist=LCSC, dist_pn="C14675", url=lcsc("C14675"), price=0.0, qty_order=0, verify="see R5", h=0.55)
add("R7", "100k", "Device:R", FP_R, {"1": "VDIV_MID", "2": "GND"}, block="power",
    mpn="RC0603FR-07100KL", mfr="Yageo", dist=LCSC, dist_pn="C14675", url=lcsc("C14675"), price=0.0, qty_order=0, verify="see R5", h=0.55)
add("BT1", "LiPo 600 mAh", "Device:Battery_Cell", "", {"1": "VBAT", "2": "GND"}, block="power", on_board=False,
    mpn="LP503040JH+PCM+2 WIRES 50MM", mfr="Jauch", dist=DK, dist_pn="1908-LP503040JH+PCM+2WIRES50MM-ND",
    url="https://www.digikey.com/en/products/detail/jauch-quartz/LP503040JH-PCM-2-WIRES-50MM/9560983",
    price=10.81, qty_order=1,
    verify="A (re-checked 2026-10-12): $10.81 @1, 1,637 in stock (digikey.com page); no air shipping (Li-ion), 28-week lead time once stock runs out; datasheet 10/2022",
    datasheet="https://www.jauch.com/downloadfile/5bf529d2b6c3061ac0d91eb97d1d37b22/600mah_-_lp503040jh_1s1p_2_wire_50mm.pdf",
    note="600 mAh min / 650 typ; 0.5C max charge; PCM 4.28 / 3.00 V; leads soldered to TP_BAT+/-")
add("TP1", "BAT+", "Connector:TestPoint", "vf:WirePad_1.5x3.0mm", {"1": "VBAT"}, block="power", h=0.0)
add("TP2", "BAT-", "Connector:TestPoint", "vf:WirePad_1.5x3.0mm", {"1": "GND"}, block="power", h=0.0)

# ----------------------------------------------------------------------------- MCU
add("U1", "ATtiny1614", "MCU_Microchip_ATtiny:ATtiny1614-SS", "Package_SO:SOIC-14_3.9x8.7mm_P1.27mm",
    dict(MCU_PINS), block="mcu",
    mpn="ATTINY1614-SSNR", mfr="Microchip", dist=DK, dist_pn="ATTINY1614-SSNRCT-ND", url=dk("ATTINY1614-SSNR"),
    price=0.90, qty_order=2, verify="A (re-checked 2026-10-12): $0.90 @1, 33,040 in stock (digikey.com page)",
    alt="LCSC C481364, ~$1.78 @1, 648 in stock (snippet)",
    datasheet="https://ww1.microchip.com/downloads/en/DeviceDoc/ATtiny1614-16-17-DataSheet-DS40002204A.pdf", h=1.75)
add("C3", "100n", "Device:C", FP_C, {"1": "VBAT", "2": "GND"}, block="mcu",
    mpn="CL10B104KB8NNNC", mfr="Samsung", dist=LCSC, dist_pn="C1591", url=lcsc("C1591"), price=0.016, qty_order=100,
    verify="A (re-checked 2026-10-12): $0.0085-0.016 @100+ (cached pages disagree; highest used), 3.8-8.2 M in stock (one copy out of stock)", alt="Digi-Key 1276-1000-1-ND $0.08 @1", h=0.9)
add("C4", "1u 25V", "Device:C", FP_C, {"1": "VBAT", "2": "GND"}, block="mcu",
    mpn="CL10B105KA8NNNC", mfr="Samsung", dist=LCSC, dist_pn="C29936", url=lcsc("C29936"), price=0.0, qty_order=0,
    verify="see C1", h=0.9)
add("TP3", "UPDI", "Connector:TestPoint", "TestPoint:TestPoint_Pad_1.5x1.5mm", {"1": "UPDI"}, block="mcu")
add("TP4", "VBAT", "Connector:TestPoint", "TestPoint:TestPoint_Pad_1.5x1.5mm", {"1": "VBAT"}, block="mcu")
add("TP5", "GND", "Connector:TestPoint", "TestPoint:TestPoint_Pad_1.5x1.5mm", {"1": "GND"}, block="mcu")
add("TP6", "TX", "Connector:TestPoint", "TestPoint:TestPoint_Pad_1.5x1.5mm", {"1": "DBG_TX"}, block="mcu")
add("TP7", "RX", "Connector:TestPoint", "TestPoint:TestPoint_Pad_1.5x1.5mm", {"1": "DBG_RX"}, block="mcu")

# button: the switch sits on the printed bridge, wired to two pads
add("SW1", "B3F-1020", "Switch:SW_Push", "", {"1": "BTN", "2": "GND"}, block="mcu", on_board=False,
    mpn="B3F-1020", mfr="Omron (Aratas)", dist=LCSC, dist_pn="C722171", url=lcsc("C722171"), price=0.1523, qty_order=5,
    verify="A (re-checked 2026-10-12): $0.1523 @5+ (MOQ 5; the earlier $0.071 was the 5000+ tier), 700-1,940 in stock, one copy out of stock; 5.0 mm, 0.98 N, 0.25 mm travel",
    alt="Digi-Key SW402-ND $0.42 @1, ~14,081 in stock (one snippet)",
    note="6 x 6 THT, held by the printed bridge; legs wired to TP8/TP9 with 30 AWG")
add("TP8", "BTN", "Connector:TestPoint", "vf:WirePad_1.2x2.0mm", {"1": "BTN"}, block="mcu")
add("TP9", "BTN_GND", "Connector:TestPoint", "vf:WirePad_1.2x2.0mm", {"1": "GND"}, block="mcu")

# ----------------------------------------------------------------------------- thermal sense
add("RT1", "10k NTC", "Device:Thermistor_NTC", FP_R, {"1": "NTC_SENSE", "2": "GND"}, block="sense", side="B",
    mpn="NCP18XH103F03RB", mfr="Murata", dist=LCSC, dist_pn="C13564", url=lcsc("C13564"), price=0.0467, qty_order=10,
    verify="A (re-checked 2026-10-12): $0.0295-0.0467 @10+ (cached pages disagree; highest used), 256-722 k in stock; one copy marks it not recommended for new designs",
    alt="Mouser 81-NCP18XH103F03RB $0.16 @1; Digi-Key 490-4800-1-ND $0.18 @1", h=0.95,
    note="B25/50 3380 K +-1 %; underside, in the sole's 0.7 mm sensor window at theta = 0")
add("R8", "10k", "Device:R", FP_R, {"1": "NTC_EN", "2": "NTC_SENSE"}, block="sense",
    mpn="RC0603FR-0710KL", mfr="Yageo", dist=LCSC, dist_pn="C98220", url=lcsc("C98220"), price=0.0, qty_order=0,
    verify="see R4", h=0.55)

# ----------------------------------------------------------------------------- LED driver
add("U3", "TPS61169", "vf:TPS61169DCK", "vf:SC-70-5_HandSolder",
    {"5": "VBAT", "4": "LED_CTRL", "1": "SW", "3": "FB", "2": "GND"}, block="driver",
    mpn="TPS61169DCKR", mfr="Texas Instruments", dist=LCSC, dist_pn="C71045", url=lcsc("C71045"), price=0.3268, qty_order=5,
    verify="A (re-checked 2026-10-12): $0.1606-0.3268 @5+ (MOQ 5; cached pages disagree; highest used), 8,475-33,765 in stock (one copy out of stock); Digi-Key 296-40821-1-ND on backorder",
    alt="Mouser ~$1.08 @1, 4,740 in stock (aggregator; PN NV); Farnell DE 2,961",
    datasheet="https://www.ti.com/lit/ds/symlink/tps61169.pdf", h=1.1,
    note="VIN 2.7-5.5 V; VREF 188/204/220 mV; OVP 36-39 V at SW; CTRL PWM 5-100 kHz -> analog dimming")
add("L1", "10u", "Device:L", "Inductor_SMD:L_Sunlord_SWPA4018S", {"1": "VBAT", "2": "SW"}, block="driver",
    mpn="SWPA4018S100MT", mfr="Sunlord", dist=LCSC, dist_pn="C83442", url=lcsc("C83442"), price=0.0594, qty_order=10,
    verify="A (re-checked 2026-10-12): $0.0594 @10+, 1,459 in stock (one LCSC copy found); Isat 1.30 A, DCR 0.18 ohm",
    alt="Coilcraft LPS4018-103MRC: Mouser 994-LPS4018-103MRC (~18,910 in stock), Digi-Key 2457-LPS4018-103MRC-ND", h=1.8)
add("D1", "MBR0540", "Device:D_Schottky", "Diode_SMD:D_SOD-123", {"1": "VOUT", "2": "SW"}, block="driver",
    mpn="MBR0540T1G", mfr="onsemi", dist=LCSC, dist_pn="C21353", url=lcsc("C21353"), price=0.061, qty_order=10,
    verify="A (re-checked 2026-10-12): $0.055-0.061 @10+ (MOQ 10; highest used), 47,700-168,940 in stock",
    alt="LCSC C8598 B5819W SL $0.0244 @20+; Digi-Key NSR0240HT1GOSCT-ND (TI's pick)", h=1.35,
    note="40 V >= OVP max 39 V; 0.5 A")
add("C5", "1u 50V", "Device:C", FP_C1206, {"1": "VOUT", "2": "GND"}, block="driver",
    mpn="CL31B105KBHNNNE", mfr="Samsung", dist=LCSC, dist_pn="C1848", url=lcsc("C1848"), price=0.0492, qty_order=10,
    verify="A (re-checked 2026-10-12): $0.022-0.0492 @10+ (cached pages disagree; highest used), 102,630-573,000 in stock (one copy out of stock)", alt="Digi-Key 445-1423-1-ND TDK C3216X7R1H105K160AB $0.30", h=1.2,
    note="50 V: VOUT can reach the 39 V OVP; 2 x 1 uF for >= 1 uF after DC bias (datasheet: 1-4.7 uF)")
add("C6", "1u 50V", "Device:C", FP_C1206, {"1": "VOUT", "2": "GND"}, block="driver",
    mpn="CL31B105KBHNNNE", mfr="Samsung", dist=LCSC, dist_pn="C1848", url=lcsc("C1848"), price=0.0, qty_order=0, verify="see C5", h=1.2)
add("C7", "10u 25V", "Device:C", FP_C0805, {"1": "VBAT", "2": "GND"}, block="driver",
    mpn="GRM21BR61E106KA73L", mfr="Murata", dist=LCSC, dist_pn="C84416", url=lcsc("C84416"), price=0.1764, qty_order=5,
    verify="A (re-checked 2026-10-12): $0.1764 @5+ on the product page ($0.0191-0.0297 @20+ on image copies), 121,900-484,120 in stock; not recommended for new designs",
    alt="Digi-Key 1276-2891-1-ND Samsung CL21A106KAYNNNE $0.24 (aggregator)", h=1.35)
add("R9", "8.2", "Device:R", FP_R, {"1": "FB", "2": "GND"}, block="driver",
    mpn="RC0603FR-078R2L", mfr="Yageo", dist=LCSC, dist_pn="C137674", url=lcsc("C137674"), price=0.0054, qty_order=100,
    verify="A (re-checked 2026-10-12): $0.0054 @100+, 2,300 in stock", h=0.55,
    note="ceiling 24.9 mA typ (22.9-26.8 mA over VREF 188-220 mV) < 30 mA LED max; firmware sets the caps")
add("R10", "100k", "Device:R", FP_R, {"1": "LED_CTRL", "2": "GND"}, block="driver",
    mpn="RC0603FR-07100KL", mfr="Yageo", dist=LCSC, dist_pn="C14675", url=lcsc("C14675"), price=0.0, qty_order=0,
    verify="see R5", h=0.55, note="driver off while the MCU is in reset or unprogrammed")
for ref, gate, drain in (("Q1", "GATE_A", "STR_A"), ("Q2", "GATE_B", "STR_B")):
    add(ref, "AO3400A", "Transistor_FET:AO3400A", "Package_TO_SOT_SMD:SOT-23", {"1": gate, "2": "FB", "3": drain},
        block="driver", mpn="AO3400A", mfr="Alpha & Omega", dist=LCSC, dist_pn="C20917", url=lcsc("C20917"),
        price=0.0898 if ref == "Q1" else 0.0, qty_order=5 if ref == "Q1" else 0,
        verify="A (re-checked 2026-10-12): $0.0735-0.0898 @5+ (cached pages disagree; highest used), 100 k-1.14 M in stock; 30 V, 48 mOhm @ 2.5 V" if ref == "Q1" else "see Q1",
        alt="Digi-Key FDN337N (onsemi, 30 V, same pin-out), large stock (snippets)", h=1.1)
for ref, gate in (("R11", "GATE_A"), ("R12", "GATE_B")):
    add(ref, "100k", "Device:R", FP_R, {"1": gate, "2": "GND"}, block="driver",
        mpn="RC0603FR-07100KL", mfr="Yageo", dist=LCSC, dist_pn="C14675", url=lcsc("C14675"), price=0.0, qty_order=0,
        verify="see R5", h=0.55)

# the two strings: VOUT -> 6 LEDs -> Q drain.  Ring positions come from the CAD layout.
# Both strings start at the +y horn (one VOUT line crosses the board from the driver) and
# walk the ring to the -y horn, where their ends meet the bank FETs next to the driver.
_banks = {"660": [], "620": []}
for led in sorted(LAYOUT["leds"], key=lambda l: (l["bank"], -l["angle"])):
    _banks[led["bank"]].append(led)
LED_REF = {}
for bank, net_end, prefix, n0 in (("660", "STR_A", "A", 1), ("620", "STR_B", "B", 7)):
    leds = _banks[bank]
    for i, led in enumerate(leds):
        ref = f"D{n0 + i + 1}"
        anode = "VOUT" if i == 0 else f"{prefix}{i}"
        cathode = net_end if i == len(leds) - 1 else f"{prefix}{i + 1}"
        LED_REF[(round(led["angle"], 1))] = ref
        first = i == 0
        if bank == "660":
            src = dict(mpn="XZM2MR55W-3", mfr="SunLED", dist=DK, dist_pn="1497-1364-1-ND",
                       url="https://www.digikey.com/en/products/detail/sunled/XZM2MR55W-3/6709143",
                       price=0.54 if first else 0.0, qty_order=10 if first else 0,
                       verify="A (re-checked 2026-10-12): $0.69-0.70 @1, $0.48-0.54 @10 (two Digi-Key page copies; highest used), 3,264-17,861 in stock; 660 nm, 30 mA max, 2.10 mm max" if first else "see first 660 nm LED",
                       datasheet="https://www.sunledusa.com/products/spec/XZM2MR55W-3.pdf")
        else:
            src = dict(mpn="XZM2CRK55W-3", mfr="SunLED", dist=DK, dist_pn="1497-1405-1-ND",
                       url=dk("XZM2CRK55W-3"), price=0.326 if first else 0.0, qty_order=10 if first else 0,
                       verify="A (re-checked 2026-10-12): $0.48 @1, $0.326 @10, 16,312 in stock (digikey.com page; Octopart 14,519); 625 nm, 30 mA max, 1.80 mm max" if first else "see first 625 nm LED")
        add(ref, "660nm" if bank == "660" else "625nm", "Device:LED", "LED_SMD:LED_1206_3216Metric_Pad1.42x1.75mm_HandSolder",
            {"2": anode, "1": cathode}, block="leds", side="B", h=0.0, **src)

# ----------------------------------------------------------------------------- status seam
for i in range(len(LAYOUT["seam_leds"])):
    first = i == 0
    add(f"D{14 + i}", "amber", "Device:LED", "LED_SMD:LED_0603_1608Metric",
        {"2": f"SEAM{i + 1}", "1": "GND"}, block="seam",
        mpn="LTST-C190KSKT", mfr="Lite-On", dist=LCSC, dist_pn="C125095", url=lcsc("C125095"),
        price=0.0248 if first else 0.0, qty_order=20 if first else 0,
        verify="A (re-checked 2026-10-12): $0.0215-0.0248 @20+ (MOQ 20; highest used), 54-169 k in stock; 591 nm" if first else "see D14",
        alt="Digi-Key 160-1437-1-ND $0.081 @10, 499 k in stock", h=0.8)
    add(f"R{13 + i}", "1k", "Device:R", FP_R, {"1": "SEAM_PWM", "2": f"SEAM{i + 1}"}, block="seam",
        mpn="RC0603FR-071KL", mfr="Yageo", dist=LCSC, dist_pn="C22548", url=lcsc("C22548"),
        price=0.0058 if first else 0.0, qty_order=100 if first else 0,
        verify="A (re-checked 2026-10-12): $0.0037-0.0058 @100+ (cached pages disagree; highest used), 2.8-9.9 M in stock" if first else "see R13", h=0.55)

# ----------------------------------------------------------------------------- mechanical (board-mounted)
for i, (x, y) in enumerate(LAYOUT["mask_pins"] + LAYOUT["bridge_pins"]):
    add(f"H{i + 1}", "locating pin", "Connector:TestPoint", "vf:LocatingPin_D1.0mm", {"1": "GND"}, block="mech",
        place=(x, y, 0.0), mpn="PRPC040SAAN-RC" if i == 0 else "", mfr="Sullins" if i == 0 else "",
        dist=DK if i == 0 else "", dist_pn="S1011EC-40-ND" if i == 0 else "",
        url="https://www.digikey.com/en/products/detail/PRPC040SAAN-RC/S1011EC-40-ND/2775214" if i == 0 else "",
        price=1.23 if i == 0 else 0.0, qty_order=1 if i == 0 else 0,
        verify="A (re-checked 2026-10-12): $1.23 @1, $1.04 @10, 46-48 k in stock (digikey.com page; Octopart ~$1.23); one unattributed result shows $0.55 @1; 5.84 mm posts" if i == 0 else "see H1",
        alt="LCSC C2977586 2.54 mm 1x40 header ~$0.10 @5+ (aggregator)",
        note="posts pulled from a 2.54 mm header, soldered from the underside, cut flush")

# ----------------------------------------------------------------------------- off-board bought parts
OFFBOARD = [
    dict(item="Magnet 1/4 x 1/8 in N35 (horn dowels, sole)", qty=2, mpn="8193", mfr="Radial Magnets", dist=DK,
         dist_pn="469-1004-ND", url=dk("469-1004-ND"), price=0.40, qty_order=3,
         verify="A (re-checked 2026-10-12): $0.40 @1, 12.4-14.7 k in stock (digikey.com page)"),
    dict(item="Magnet 1/4 x 1/16 in N35 (horn tops, tail pairs)", qty=6, mpn="8195", mfr="Radial Magnets", dist=DK,
         dist_pn="469-1005-ND", url=dk("469-1005-ND"), price=0.19, qty_order=8,
         verify="A (re-checked 2026-10-12): $0.19 @1, $0.156 @10, 44-61 k in stock (digikey.com page)"),
    dict(item="Silicone wire 30 AWG, red, 2 m", qty=1, mpn="2001", mfr="Adafruit", dist=ADA, dist_pn="2001",
         url=ada(2001), price=0.75, qty_order=1, verify="A (re-checked 2026-10-12): $0.75 (1-9), in stock (adafruit.com); Mouser 485-2001, 59"),
    dict(item="Silicone wire 30 AWG, black, 2 m", qty=1, mpn="2003", mfr="Adafruit", dist=ADA, dist_pn="2003",
         url=ada(2003), price=0.75, qty_order=1, verify="A (re-checked 2026-10-12): $0.75 (1-9), in stock (adafruit.com)"),
    dict(item="Double-sided foam tape (battery), 1.0-1.6 mm", qty=1, mpn="5019", mfr="Adafruit", dist=ADA, dist_pn="5019",
         url=ada(5019), price=0.75, qty_order=1, verify="A (re-checked 2026-10-12): $0.75; current stock not found; the page gives both 0.063 in (1.6 mm) and 1 mm: measure it"),
]
TOOLS = [
    dict(item="UPDI programmer (USB-C, 3 V / 5 V)", mpn="5879", mfr="Adafruit (UPDI Friend)", dist=DK,
         dist_pn="1528-5879-ND (NV)", url="https://www.digikey.com/en/products/detail/adafruit-industries-llc/5879/22596413",
         price=6.95, qty_order=1, verify="A: $6.95, 40 in stock (digikey.com snippet); Adafruit $6.95"),
]

# PCB: fabricated to the gate-3 Gerbers (not a distributor part)
PCB = dict(item="PCB, 2-layer FR-4, 1.0 mm, black mask, ENIG or HASL, 5 pcs", fab="any PCB fab (e.g. JLCPCB, PCBWay, OSH Park)",
           price_estimate=(5.0, 15.0), verify="NV: fab quotes not reachable here; estimate incl. economy shipping")
