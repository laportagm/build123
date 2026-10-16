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

POWER = ["VBAT", "VBUS", "SW", "VOUT"]
LEDNETS = ["STR_A", "STR_B", "FB"] + [f"A{i}" for i in range(1, 6)] + [f"B{i}" for i in range(1, 6)]
RULES = dict(min_clearance=0.2, min_track_width=0.2, min_via_diameter=0.5, min_via_annular_width=0.1,
             min_through_hole_diameter=0.3, min_copper_edge_clearance=0.3, min_hole_to_hole=0.25,
             min_hole_clearance=0.25, min_silk_clearance=0.0)


FP_LIBS = ["Capacitor_SMD", "Diode_SMD", "Inductor_SMD", "LED_SMD", "Package_SO", "Package_TO_SOT_SMD",
           "Resistor_SMD", "TestPoint"]


def lib_tables(kicad_dir: Path):
    """Project library tables: KiCad's own libraries as tools/fetch.sh puts them in
    build/kicadlib, and this project's vf library."""
    fp = ['(fp_lib_table', '  (version 7)',
          '  (lib (name "vf")(type "KiCad")(uri "${KIPRJMOD}/../lib/vf.pretty")(options "")(descr "vein finder"))']
    fp += [f'  (lib (name "{n}")(type "KiCad")(uri "${{KIPRJMOD}}/../../build/kicadlib/fp/{n}.pretty")(options "")(descr ""))'
           for n in FP_LIBS]
    (kicad_dir / "fp-lib-table").write_text("\n".join(fp + [")"]) + "\n")


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
            "classes": [cls("Default", 0.25, 0.6, 0.3), cls("Power", 0.45, 0.7, 0.35), cls("LED", 0.25, 0.6, 0.3),
                        cls("Gnd", 0.3, 0.6, 0.3)],
            "meta": {"version": 3}, "net_colors": None, "netclass_assignments": None,
            "netclass_patterns": [{"netclass": "Gnd", "pattern": "GND"}] +
                                 [{"netclass": "Power", "pattern": n} for n in POWER] +
                                 [{"netclass": "LED", "pattern": n} for n in LEDNETS]},
    }
    path.write_text(json.dumps(pro, indent=2))
    lib_tables(path.parent)
    # custom rule: the USB-C receptacle's land pattern (GCT USB4515 datasheet) puts its
    # pads 0.2 mm from the board notch it hangs in; everything else keeps the 0.3 mm rule
    # (the outer ring LEDs are pulled in to clear it: cad/device/layout.py, LED_END_MARGIN)
    path.with_suffix(".kicad_dru").write_text(
        '(version 1)\n'
        '(rule "USB-C land pattern at the notch (USB4515 datasheet layout)"\n'
        '  (constraint edge_clearance (min 0.15mm))\n'
        '  (condition "A.Type == \'Pad\' && A.intersectsCourtyard(\'J1\')"))\n')


# the label the brief asks for on everything: underside silkscreen, on the free tail.
# 1.0 mm text with a 0.16 mm stroke: JLCPCB's published minimums are 1.0 mm and 0.153 mm.
LABELS = [("VEIN FINDER (ORGANIC) REV A 2026-10", 40.0, 1.25),
          ("PERSONAL PROTOTYPE - NOT A MEDICAL DEVICE", 40.0, -1.0)]
LABEL_SIZE, LABEL_STROKE = 1.0, 0.16


def label_style(t):
    t.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(LABEL_SIZE), pcbnew.FromMM(LABEL_SIZE)))
    t.SetTextThickness(pcbnew.FromMM(LABEL_STROKE))
    return t


def solid_pads(board):
    for ref in ["RT1"] + [f"H{i}" for i in range(1, 7)]:
        board.FindFootprintByReference(ref).SetZoneConnection(pcbnew.ZONE_CONNECTION_FULL)


def build(passes=60):
    OUT.mkdir(parents=True, exist_ok=True)
    P, polys, probs = placement.place(verbose=False)
    if probs:
        raise RuntimeError(f"placement problems: {probs}")
    bb = BoardBuilder(FP_DIRS, thickness=1.0)
    for p in D.PARTS:
        for n in p.pins.values():
            bb.net(n)
    # outline (the CAD's board, with the magnet holes and the USB-C cut-out), simplified to
    # 0.02 mm: the CAD ring has ~1800 vertices, which stalls Freerouting; 0.02 mm is far
    # inside the 0.3 mm board-to-cavity clearance
    from shapely.geometry import Polygon
    rings = []
    for poly in LAYOUT["board_outline"]:
        q = Polygon(poly[0], poly[1:]).simplify(0.02, preserve_topology=True)
        rings.append([list(q.exterior.coords)] + [list(i.coords) for i in q.interiors])
    bb.outline(rings)
    # footprints
    for p in D.PARTS:
        if not p.on_board:
            continue
        x, y, a, side = P[p.ref]
        p.place, p.side = (x, y, a), side
        bb.footprint(p)
        err = bb.check_transform(p)
        if err > 1e-3:
            raise RuntimeError(f"{p.ref}: pads {err:.3f} mm off the intended placement")
    # the NTC's GND pad joins the underside plane solidly: a thermal relief there gets one
    # spoke between the ring LEDs, and solid copper couples the sensor to the board.  The
    # locating pins (GND only so that no copper floats) are solid too: their pads sit among
    # tracks, where a relief may get a single spoke, and a header post solders fine either way.
    solid_pads(bb.b)
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
    bb = BoardBuilder(FP_DIRS, board=b)
    names = {n for p in D.PARTS if p.on_board for n in p.pins.values()}
    bb.nets = {n: b.FindNet(n) for n in names}            # reuse the board's nets (no duplicates)
    # GND is routed like any other net (0.3 mm), so every GND pad gets a real connection.  A
    # pour present during routing would export as a Specctra plane: the router then assumes
    # it is whole, while its own traces cut it into islands.  The pours come after routing,
    # on both layers; finish_route.py stitches them.  The underside pour also spreads the
    # LEDs' heat toward the NTC.
    bb.route(OUT / "route", JAR, passes=passes, threads=4)
    bb.gnd_pour(layers=(pcbnew.F_Cu, pcbnew.B_Cu))
    # the label the brief asks for on everything (underside silkscreen, along the -y arm)
    for txt, x, y in LABELS:
        label_style(bb.text(txt, x, y))
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
        m = re.search(rf"\*\* Found (\d+) (?:DRC )?{key}", text, re.IGNORECASE)   # "Footprint errors"
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
    if a.stage == "finish":                 # re-label, re-fill and re-check a routed board
        pcb = OUT / "vein_finder.kicad_pcb"
        project_file(OUT / "vein_finder.kicad_pro")      # before the load: rules and net classes
        b = pcbnew.LoadBoard(str(pcb))
        bb = BoardBuilder(FP_DIRS, board=b)
        solid_pads(b)
        have = {d.GetText(): d for d in b.GetDrawings() if d.GetClass() == "PCB_TEXT"}
        for txt, x, y in LABELS:
            if txt in have:
                have[txt].SetPosition(kpt(x, y))
                label_style(have[txt])
            else:
                label_style(bb.text(txt, x, y))
        if "CELL ON FOAM TAPE - NO PARTS" not in have:
            bt = LAYOUT["battery"]
            bb.rect(bt["x0"], -bt["y"], bt["x1"], bt["y"])                     # where the cell goes
            bb.text("CELL ON FOAM TAPE - NO PARTS", (bt["x0"] + bt["x1"]) / 2, 0.0, layer="F.SilkS", size=1.2, angle=90)
        import silk
        silk.tidy(b)
        print("DRC:", drc_summary(bb.finish(pcb, OUT / "drc.rpt")))
        if not a.no_fab:
            print("fab:", fab_outputs())
        sys.exit(0)
    P, rep = build(a.passes)
    print("DRC:", drc_summary(rep))
    if not a.no_fab:
        print("fab:", fab_outputs())
