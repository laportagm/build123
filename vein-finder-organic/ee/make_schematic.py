"""
Write the gate-3 schematic (KiCad 7) from design.py, export its netlist with kicad-cli and
prove it matches the design net for net.  Also writes a PDF of the sheet.

    python make_schematic.py      ->  ee/kicad/vein_finder.kicad_sch (+ .net, .pdf)

Personal prototype for bench evaluation - NOT a medical device.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import design as D
from schematic import Sheet, SymbolLib, export_netlist, nets_from_netlist

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / "kicad"
SYM_DIRS = [ROOT / "build" / "kicadlib" / "sym", HERE / "lib"]

# block frames (sheet mm, y down) and part positions inside them
BLOCKS = {
    "USB-C input, charger, cell": (15, 20, 150, 128),
    "Microcontroller, button, programming": (155, 20, 290, 128),
    "Boost LED driver and bank select": (295, 20, 410, 128),
    "LED ring (PCB underside): string A 660 nm, string B 625 nm": (15, 138, 215, 282),
    "Status seam": (220, 138, 300, 282),
    "Temperature sense, locating pins": (305, 138, 410, 238),
}

POS = {
    # power
    "J1": (35, 60), "R1": (35, 100), "R2": (50, 100), "C1": (68, 75), "U2": (95, 60),
    "R3": (80, 100), "R4": (95, 100), "C2": (125, 75), "R5": (68, 108), "R6": (68, 118), "R7": (82, 118),
    "BT1": (140, 100), "TP1": (125, 100), "TP2": (125, 112),
    # mcu
    "U1": (210, 70), "C3": (175, 55), "C4": (188, 55), "SW1": (255, 112), "TP8": (240, 112), "TP9": (270, 112),
    "TP3": (250, 35), "TP4": (263, 35), "TP5": (276, 35), "TP6": (250, 48), "TP7": (263, 48),
    # driver
    "C7": (305, 55), "L1": (320, 45), "U3": (340, 65), "D1": (365, 45), "C5": (385, 55), "C6": (398, 55),
    "R10": (318, 95), "R9": (360, 112), "Q1": (380, 90), "Q2": (398, 90), "R11": (372, 112), "R12": (390, 112),
    # seam
    **{f"R{13 + i}": (235, 155 + 25 * i) for i in range(5)},
    **{f"D{14 + i}": (265, 160 + 25 * i) for i in range(5)},
    # sense + mech
    "R8": (330, 160), "RT1": (330, 178),
    **{f"H{i + 1}": (325 + 25 * (i % 3), 200 + 20 * (i // 3)) for i in range(6)},
}
# LED strings: two columns of six
for col, (prefix, refs) in enumerate((("A", [f"D{n}" for n in range(2, 8)]), ("B", [f"D{n}" for n in range(8, 14)]))):
    for i, r in enumerate(refs):
        POS[r] = (45 + 95 * col, 160 + 20 * i)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    lib = SymbolLib(SYM_DIRS)
    sh = Sheet(lib, "Vein finder (organic) - main board", "vein_finder", rev="A", date="2026-10-12",
               comments=("Personal prototype for bench evaluation - NOT a medical device",
                         "Generated from ee/design.py (gate 3); nets by label",
                         "LED ring and NTC on the PCB underside; ring positions from the CAD layout"))
    for title, (x0, y0, x1, y1) in BLOCKS.items():
        sh.rect(x0, y0, x1, y1)
        sh.text(title, x0 + 2, y0 + 5, size=2.0, bold=True)
    notes = {
        "USB-C input, charger, cell": "BQ21040: I_CHG = 540 / 2.2k = 245 mA (0.41C); 4.20 V; IN 30 V abs max, OVP 6.6 V",
        "Boost LED driver and bank select": "I_LED max = VREF / R9 = 204 mV / 8.2 = 24.9 mA (22.9-26.8); CTRL PWM 20 kHz",
        "Temperature sense, locating pins": "RT1 sits in the sole's 0.7 mm sensor window",
    }
    for k, t in notes.items():
        x0, y0, x1, y1 = BLOCKS[k]
        sh.text(t, x0 + 2, y1 - 3, size=1.5)
    for p in D.PARTS:
        x, y = POS[p.ref]
        sh.place(p, x, y)
    sch = OUT / "vein_finder.kicad_sch"
    sh.write(sch)
    # netlist round trip
    net = export_netlist(sch, OUT / "vein_finder.net")
    got = nets_from_netlist(net)
    want = {}
    for p in D.PARTS:
        if not p.on_board:          # the cell and the button are wired, not on the board netlist
            continue
        for pin, n in p.pins.items():
            want.setdefault(n, []).append((p.ref, pin))
    want = {k: sorted(v) for k, v in want.items()}
    bad = []
    for n, nodes in want.items():
        if got.get(n) != nodes:
            bad.append((n, nodes, got.get(n)))
    extra = sorted(set(got) - set(want))
    subprocess.run(["kicad-cli", "sch", "export", "pdf", "--output", str(OUT / "vein_finder_schematic.pdf"), str(sch)],
                   check=True, capture_output=True)
    print(f"schematic: {len(D.PARTS)} parts, {len(want)} nets; netlist mismatches: {len(bad)}; extra nets: {extra}")
    for b in bad[:20]:
        print("  MISMATCH", b)
    return not bad and not [e for e in extra if not e.startswith("unconnected")]


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
