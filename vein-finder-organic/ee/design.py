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
    "2": "GATE_B",       # PA4  bank B (620 nm) low-side switch
    "3": "CHG_STAT",     # PA5  charger status (tri-state)
    "4": "BTN",          # PA6  async pin: wake from power-down
    "5": "VBUS_SENSE",   # PA7  AIN7, USB present
    "9": "LED_CTRL",     # PB0  TCA0 WO0: boost enable + PWM (analog dimming)
    "8": "SEAM_PWM",     # PB1  TCA0 WO1: status seam
    "7": "DBG_TX",       # PB2  USART0 TXD (debug pad)
    "6": "DBG_RX",       # PB3  USART0 RXD (debug pad)
}

FW_PINS = {v: k for k, v in MCU_PINS.items()}
