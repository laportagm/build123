"""
Build, route and check the gate-3 PCB, then write the fabrication outputs.

    python make_pcb.py [--passes N]

  1. board outline, plated locating-pin holes and the magnet holes from the CAD layout
     (build/device/layout.json -- the board is the CAD's, not a redraw);
  2. footprints from design.py at the positions proved by placement.py (top and underside);
  3. net classes and design rules (written to the .kicad_pro, which pcbnew loads);
  4. Freerouting (headless) through Specctra DSN/SES;
  5. GND pours on both layers, zone fill, DRC report;
  6. Gerbers, drill, pick-and-place, PDF plots -> docs/03-electronics/fab/.

Personal prototype for bench evaluation - NOT a medical device.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pcbnew

import design as D
import placement
from board import BoardBuilder, X0, Y0, dev, kpt

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / "kicad"
FAB = ROOT / "docs" / "03-electronics" / "fab"
FP_DIRS = [ROOT / "build" / "kicadlib" / "fp", HERE / "lib"]
JAR = ROOT / "build" / "kicadlib" / "tools" / "freerouting-2.0.1.jar"
LAYOUT = json.loads((ROOT / "build" / "device" / "layout.json").read_text())

POWER = ["GND", "VBAT", "VBUS", "SW", "VOUT"]
LEDNETS = ["STR_A", "STR_B", "FB"] + [f"A{i}" for i in range(1, 6)] + [f"B{i}" for i in range(1, 6)]
RULES = dict(min_clearance=0.2, min_track_width=0.2, min_via_diameter=0.5, min_via_annular_width=0.1,
             min_through_hole_diameter=0.3, min_copper_edge_clearance=0.3, min_hole_to_hole=0.25,
             min_hole_clearance=0.25, min_silk_clearance=0.0)


def project_file(path: Path):
    """Minimal KiCad 7 project: net classes, their patterns and the board rules."""
    def cls(name, track, via, drill, clearance=0.2):
        return {"name": name, "clearance": clearance, "track_width": track, "via_diameter": via, "via_drill": drill,
                "microvia_diameter": 0.3, "microvia_drill": 0.1, "diff_pair_gap": 0.25, "diff_pair_via_gap": 0.25,
                "diff_pair_width": 0.2, "line_style": 0, "bus_width": 12, "wire_width": 6,
                "pcb_color": "rgba(0, 0, 0, 0.000)", "schematic_color": "rgba(0, 0, 0, 0.000)"}
    pro = {
        "board": {"design_settings": {"defaults": {"board_outline_line_width": 0.1, "copper_line_width": 0.2},
                                      "rules": dict(RULES, allow_blind_buried_vias=False, allow_microvias=False,
                                                    min_microvia_diameter=0.2, min_microvia_drill=0.1,
                                                    min_text_height=0.8, min_text_thickness=0.08),
                                      "track_widths": [0.0, 0.25, 0.3, 0.45], "via_dimensions": [{"diameter": 0.0, "drill": 0.0}]}},
        "meta": {"filename": path.name, "version": 1},
        "net_settings": {
            "classes": [cls("Default", 0.25, 0.6, 0.3), cls("Power", 0.45, 0.7, 0.35), cls("LED", 0.3, 0.6, 0.3)],
            "meta": {"version": 3}, "net_colors": None, "netclass_assignments": None,
            "netclass_patterns": [{"netclass": "Power", "pattern": n} for n in POWER] +
                                 [{"netclass": "LED", "pattern": n} for n in LEDNETS]},
    }
    path.write_text(json.dumps(pro, indent=2))


def build(passes=60):
    OUT.mkdir(parents=True, exist_ok=True)
    P, polys, probs = placement.place(verbose=False)
    if probs:
        raise RuntimeError(f"placement problems: {probs}")
    bb = BoardBuilder(FP_DIRS, thickness=1.0)
    for p in D.PARTS:
        for n in p.pins.values():
            bb.net(n)
    # outline (the CAD's board, with the magnet holes and the USB-C cut-out)
    bb.outline(LAYOUT["board_outline"])
    # footprints
    for p in D.PARTS:
        if not p.on_board:
            continue
        x, y, a, side = P[p.ref]
        p.place, p.side = (x, y, a), side
        bb.footprint(p)
    pcb = OUT / "vein_finder.kicad_pcb"
    bb.b.Save(str(pcb))
    project_file(OUT / "vein_finder.kicad_pro")      # after the save: Save() rewrites the project
    # route in a fresh process: pcbnew keeps the project it saved cached in this one, and
    # only a fresh load picks up the net classes written above
    r = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--stage", "route", "--passes", str(passes)],
                       capture_output=True, text=True)
    print(r.stdout[-3000:], r.stderr[-3000:])
    if r.returncode:
        raise RuntimeError("routing stage failed")
    return P, (OUT / "drc.rpt").read_text()


def route_stage(passes):
    pcb = OUT / "vein_finder.kicad_pcb"
    b = pcbnew.LoadBoard(str(pcb))
    nc = {n: b.FindNet(n).GetNetClassName() for n in ("VBAT", "GND", "SW", "A1", "UPDI")}
    if nc["VBAT"] != "Power" or nc["A1"] != "LED":
        raise RuntimeError(f"net classes not applied: {nc}")
    bb = BoardBuilder(FP_DIRS, thickness=1.0)
    bb.b = b
    names = {n for p in D.PARTS if p.on_board for n in p.pins.values()}
    bb.nets = {n: b.FindNet(n) for n in names}            # reuse the board's nets (no duplicates)
    bb.route(OUT / "route", JAR, passes=passes, threads=4)
    # pours after routing (Freerouting routes GND as ordinary traces): GND on both layers;
    # the underside pour also spreads the LEDs' heat toward the NTC
    bb.gnd_pour()
    rep = bb.finish(pcb, OUT / "drc.rpt")
    print("routed; DRC:", drc_summary(rep))


def fab_outputs():
    FAB.mkdir(parents=True, exist_ok=True)
    pcb = OUT / "vein_finder.kicad_pcb"
    g = FAB / "gerbers"
    if g.exists():
        shutil.rmtree(g)
    g.mkdir()
    layers = "F.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts"
    run = lambda *a: subprocess.run(["kicad-cli", "pcb", "export", *a], check=True, capture_output=True, text=True)
    run("gerbers", "--output", str(g) + "/", "--layers", layers, "--subtract-soldermask", str(pcb))
    run("drill", "--output", str(g) + "/", "--format", "excellon", "--excellon-separate-th", "--generate-map",
        "--map-format", "pdf", str(pcb))
    run("pos", "--output", str(FAB / "vein_finder-pos.csv"), "--format", "csv", "--units", "mm", "--side", "both", str(pcb))
    run("pdf", "--output", str(FAB / "vein_finder-top.pdf"), "--layers", "F.Cu,F.SilkS,F.Mask,Edge.Cuts", str(pcb))
    run("pdf", "--output", str(FAB / "vein_finder-bottom.pdf"), "--layers", "B.Cu,B.SilkS,B.Mask,Edge.Cuts", "--mirror", str(pcb))
    zf = FAB / "vein_finder-gerbers.zip"
    if zf.exists():
        zf.unlink()
    shutil.make_archive(str(zf.with_suffix("")), "zip", g)
    return sorted(p.name for p in g.iterdir())


def drc_summary(text):
    import re
    out = {}
    for key in ("violations", "unconnected pads", "footprint errors"):
        m = re.search(rf"\*\* Found (\d+) (?:DRC )?{key}", text)
        out[key] = int(m.group(1)) if m else None
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--passes", type=int, default=60)
    ap.add_argument("--no-fab", action="store_true")
    ap.add_argument("--stage", default="all")
    a = ap.parse_args()
    if a.stage == "route":
        route_stage(a.passes)
        sys.exit(0)
    P, rep = build(a.passes)
    print("DRC:", drc_summary(rep))
    if not a.no_fab:
        print("fab:", fab_outputs())
