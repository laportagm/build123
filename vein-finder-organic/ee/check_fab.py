#!/usr/bin/env python3
"""
Read-only integrity checks of the board and its fabrication outputs (readiness N08).

    cd ee && python3 check_fab.py           (KiCad 7.0 pcbnew Python + kicad-cli)

Nothing in the repository is written.  Regenerated copies go to a temporary folder and
are compared with the committed files.  The one exception: if build/device/layout.json is
missing (it is generated), it is restored from the committed docs/02-cad/pcb copy so that
design.py can load.

 1  DRC of the board as saved: 0 errors, 0 unconnected, 0 footprint errors; warnings only
    of the documented kind (lib_footprint_mismatch on the ring LEDs); the committed report
    lists the same items
 2  copper pours are current: refilling them (in memory only) changes no filled area
 3  connectivity: every pad's net on the PCB = design.py; the schematic's netlist, exported
    now, = design.py = the committed .net; no single-pad nets, no unassigned IC pins
    (KiCad 7's command line has no ERC: this is the netlist-level substitute)
 4  BOM and order pack: regenerated from design.py = the committed files
 5  placement file: regenerated from the board = the committed pos.csv
 6  Gerbers and drill files: regenerated from the board = the committed files, apart from
    creation dates; the zip holds exactly those files
 7  board facts quoted in the order pack = the board
 8  copper to board edge: >= 0.3 mm, except the USB-C (J1) pads >= 0.20 mm (independent of
    KiCad's DRC: shapely distances from every pad, track, via and pour to the outline)
 9  outline: the board's Edge.Cuts = layout.json = the committed DXF
10  silkscreen against JLCPCB's published minimums (line 0.153 mm, text height 1.0 mm):
    reported, not failed (it does not change the copper)

Personal prototype for bench evaluation - NOT a medical device.
"""
from __future__ import annotations

import csv
import json
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
KI = HERE / "kicad"
PCB = KI / "vein_finder.kicad_pcb"
SCH = KI / "vein_finder.kicad_sch"
NET = KI / "vein_finder.net"
FAB = ROOT / "docs" / "03-electronics" / "fab"
LAYOUT_DOCS = ROOT / "docs" / "02-cad" / "pcb" / "layout.json"
LAYOUT_BUILD = ROOT / "build" / "device" / "layout.json"
DXF = ROOT / "docs" / "02-cad" / "pcb" / "pcb_edge_cuts.dxf"
GERBER_LAYERS = "F.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts"   # as make_pcb.fab_outputs

EDGE_MIN = 0.30            # project rule: copper to edge
EDGE_MIN_J1 = 0.20         # the documented USB-C exception (.kicad_dru)
SILK_LINE_MIN = 0.153      # JLCPCB: minimum silkscreen line width (6 mil)
SILK_TEXT_MIN = 1.0        # JLCPCB: minimum text height
TOL = 0.001
SIMPLIFY = 0.02            # make_pcb.py draws Edge.Cuts from layout.json simplified at 0.02 mm

NOTES = []
if not LAYOUT_BUILD.exists():
    LAYOUT_BUILD.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(LAYOUT_DOCS, LAYOUT_BUILD)
    NOTES.append("build/device/layout.json was missing: restored from docs/02-cad/pcb/layout.json")

import pcbnew                                           # noqa: E402
import shapely                                          # noqa: E402
from shapely.geometry import LineString, Polygon        # noqa: E402
from shapely.ops import unary_union                     # noqa: E402

import design as D                                      # noqa: E402

RESULTS = []


def result(n, name, ok, summary, details=()):
    status = {True: "PASS", False: "FAIL"}.get(ok, ok)
    RESULTS.append((n, name, status, summary, list(details)))


def mm(v):
    return pcbnew.ToMM(v)


def poly_set_to_shapely(ps):
    polys = []
    for i in range(ps.OutlineCount()):
        ol = ps.Outline(i)
        holes = [[(mm(ps.Hole(i, h).CPoint(k).x), mm(ps.Hole(i, h).CPoint(k).y))
                  for k in range(ps.Hole(i, h).PointCount())] for h in range(ps.HoleCount(i))]
        polys.append(Polygon([(mm(ol.CPoint(k).x), mm(ol.CPoint(k).y)) for k in range(ol.PointCount())], holes))
    return unary_union(polys) if polys else Polygon()


def pad_poly(pad, layer):
    """KiCad's own polygon of the pad, within 0.2 um of the true shape."""
    ps = pcbnew.SHAPE_POLY_SET()
    pad.TransformShapeToPolygon(ps, layer, 0, 200)
    return poly_set_to_shapely(ps)


def track_poly(t):
    """Exact copper of a track (round ends), arc or via, built here: this KiCad's Python
    binding cannot pass the error-side argument that TransformShapeToPolygon needs."""
    pt = lambda v: (mm(v.x), mm(v.y))
    w = mm(t.GetWidth())
    if t.GetClass() == "PCB_VIA":
        return shapely.Point(pt(t.GetPosition())).buffer(w / 2, quad_segs=64)
    if t.GetClass() == "PCB_ARC":
        import numpy as np
        (ax, ay), (bx, by), (cx, cy) = pt(t.GetStart()), pt(t.GetMid()), pt(t.GetEnd())
        d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
        ux = ((ax**2 + ay**2) * (by - cy) + (bx**2 + by**2) * (cy - ay) + (cx**2 + cy**2) * (ay - by)) / d
        uy = ((ax**2 + ay**2) * (cx - bx) + (bx**2 + by**2) * (ax - cx) + (cx**2 + cy**2) * (bx - ax)) / d
        r = np.hypot(ax - ux, ay - uy)
        a0, am, a1 = (np.arctan2(y - uy, x - ux) for x, y in ((ax, ay), (bx, by), (cx, cy)))
        span = (a1 - a0) % (2 * np.pi)
        if (am - a0) % (2 * np.pi) > span:             # the arc runs the other way round
            span -= 2 * np.pi
        ang = a0 + np.linspace(0, span, 64)
        return LineString(np.c_[ux + r * np.cos(ang), uy + r * np.sin(ang)]).buffer(w / 2, quad_segs=32)
    return LineString([pt(t.GetStart()), pt(t.GetEnd())]).buffer(w / 2, quad_segs=32)


def board_outline(b):
    ps = pcbnew.SHAPE_POLY_SET()
    b.GetBoardPolygonOutlines(ps)
    return poly_set_to_shapely(ps)


def to_device(geom):
    """KiCad page mm -> device frame (board.py: X = X0 + x, Y = Y0 - y)."""
    from board import X0, Y0
    return shapely.transform(geom, lambda a: a * [1, -1] + [-X0, Y0])


def kicad(*args, check=True):
    return subprocess.run(["kicad-cli", *args], check=check, capture_output=True, text=True)


# ----------------------------------------------------------------------------- 1 DRC
DRC_ITEM = re.compile(r"^\[(\w+)\]: (.*)\n\s+(.*?); Severity: (\w+)\n\s+@\(.*?\): (.*)$", re.M)


def parse_drc(text):
    items = [(m[0], m[3], m[4].strip()) for m in DRC_ITEM.findall(text)]
    count = lambda key: int(re.search(rf"\*\* Found (\d+) {key}", text, re.I).group(1))
    return items, count("unconnected pads"), count("Footprint errors")


def check_drc(tmp):
    b = pcbnew.LoadBoard(str(PCB))
    rpt = tmp / "drc.rpt"
    pcbnew.WriteDRCReport(b, str(rpt), pcbnew.EDA_UNITS_MILLIMETRES, True)
    items, unconnected, fp_err = parse_drc(rpt.read_text())
    old_items, old_unc, old_fp = parse_drc((KI / "drc.rpt").read_text())
    errors = [i for i in items if i[1] != "warning"]
    kinds = Counter(i[0] for i in items)
    leds = {f"D{k}" for k in range(2, 14)}
    unexpected = [i for i in items if i[1] == "warning" and
                  not (i[0] == "lib_footprint_mismatch" and i[2].split()[-1] in leds)]
    same = sorted(items) == sorted(old_items) and (unconnected, fp_err) == (old_unc, old_fp)
    ok = not errors and unconnected == 0 and fp_err == 0 and not unexpected and same
    result(1, "DRC (board as saved)", ok,
           f"{len(errors)} errors, {unconnected} unconnected, {fp_err} footprint errors; "
           f"warnings {dict(kinds)}; same items as the committed drc.rpt: {same}",
           [f"error {e}" for e in errors] + [f"unexpected warning {u}" for u in unexpected])
    return items


# ----------------------------------------------------------------------------- 2 pours
def check_fills():
    b = pcbnew.LoadBoard(str(PCB))

    def fills():
        out = {}
        for k, z in enumerate(b.Zones()):
            for L in (pcbnew.F_Cu, pcbnew.B_Cu):
                if z.IsOnLayer(L):
                    out[(k, z.GetNetname(), b.GetLayerName(L))] = poly_set_to_shapely(z.GetFilledPolysList(L))
        return out

    before = fills()
    filler = pcbnew.ZONE_FILLER(b)                      # keep the reference (SWIG lifetime)
    filler.Fill(b.Zones())
    after = fills()
    diffs = {k: before[k].symmetric_difference(after[k]).area for k in before}
    worst = max(diffs.values()) if diffs else 0.0
    area = sum(g.area for g in before.values())
    ok = set(before) == set(after) and worst < 0.01
    result(2, "Copper pours current", ok,
           f"{len(before)} fills, {area:.0f} mm² in all; largest change on refill {worst:.4f} mm²",
           [f"{k}: {v:.4f} mm² differs" for k, v in diffs.items() if v >= 0.01])


# ----------------------------------------------------------------------------- 3 connectivity
def design_nets():
    want = {}
    for p in D.PARTS:
        if p.on_board:
            for pin, n in p.pins.items():
                want.setdefault(n, []).append((p.ref, pin))
    return {k: sorted(v) for k, v in want.items()}


def check_nets(tmp):
    import schematic
    b = pcbnew.LoadBoard(str(PCB))
    parts = {p.ref: p for p in D.PARTS if p.on_board}
    fps = {fp.GetReference(): fp for fp in b.GetFootprints()}
    det = []
    missing, extra = sorted(set(parts) - set(fps)), sorted(set(fps) - set(parts))
    det += [f"in design.py, not on the PCB: {r}" for r in missing] + [f"on the PCB, not in design.py: {r}" for r in extra]
    pads = 0
    for ref, fp in fps.items():
        p = parts.get(ref)
        if p is None:
            continue
        numbered = {pad.GetNumber() for pad in fp.Pads() if pad.GetNumber()}
        for pin in sorted(set(p.pins) - numbered):
            det.append(f"{ref} pin {pin} ({p.pins[pin]}) has no pad on the footprint")
        for pad in fp.Pads():
            pads += 1
            want = p.pins.get(pad.GetNumber(), "")
            if pad.GetNetname() != want:
                det.append(f"{ref} pad {pad.GetNumber() or '(unnumbered)'}: PCB net '{pad.GetNetname()}', design '{want}'")
            if pad.GetAttribute() == pcbnew.PAD_ATTRIB_SMD or pad.GetAttribute() == pcbnew.PAD_ATTRIB_PTH:
                if pad.GetNumber() and not want and ref.startswith("U"):
                    det.append(f"{ref} pin {pad.GetNumber()} is not assigned in design.py")
    want = design_nets()
    single = [n for n, nodes in want.items() if len(nodes) < 2]
    det += [f"net {n} has a single pad: {want[n]}" for n in single]
    root = schematic.export_netlist(SCH, tmp / "fresh.net")
    got = schematic.nets_from_netlist(root)
    committed = schematic.nets_from_netlist(schematic.parse(NET.read_text())[0])
    sch_bad = [n for n in want if got.get(n) != want[n]]
    sch_extra = [n for n in got if n not in want and not n.startswith("unconnected")]
    det += [f"schematic net {n}: {got.get(n)} != design {want[n]}" for n in sch_bad]
    det += [f"schematic has an extra net {n}" for n in sch_extra]
    if got != committed:
        det.append("the committed vein_finder.net differs from a fresh export of the schematic")
    pcb_nets = {n for n in b.GetNetsByName().keys() if str(n)}
    det += [f"PCB net {n} is not in design.py" for n in sorted(map(str, pcb_nets)) if n not in want]
    result(3, "Connectivity: design = PCB = schematic", not det,
           f"{len(fps)} footprints, {pads} pads, {len(want)} nets; schematic netlist {len(got)} nets "
           f"({len(got) - len(want)} unconnected-pin nets); single-pad nets: {len(single)}", det)


# ----------------------------------------------------------------------------- 4 BOM / order
def regenerate(module, outdir, tmp):
    orig = module.OUT
    module.OUT = tmp
    try:
        module.main()
    finally:
        module.OUT = orig
    det = []
    made = sorted(p.name for p in tmp.iterdir() if p.is_file())
    for name in made:
        a, b = (tmp / name).read_bytes(), (outdir / name).read_bytes() if (outdir / name).exists() else None
        if b is None:
            det.append(f"{name}: not committed")
        elif a != b:
            det.append(f"{name}: differs from the committed file")
    return made, det


def check_bom(tmp):
    import contextlib
    import io
    import make_bom
    import make_order
    with contextlib.redirect_stdout(io.StringIO()):
        bom_files, det = regenerate(make_bom, ROOT / "docs" / "03-electronics", tmp / "bom")
        order_files, det2 = regenerate(make_order, ROOT / "docs" / "07-order", tmp / "order")
    det += det2
    refs_bom = set()
    with open(ROOT / "docs" / "03-electronics" / "bom.csv") as fh:
        for r in csv.DictReader(fh):
            refs_bom |= set(r["refs"].split()) - {"(off-board)"}
    with_mpn = {p.ref for p in D.PARTS if p.mpn}
    det += [f"{r} has an MPN but is not in bom.csv" for r in sorted(with_mpn - refs_bom)]
    det += [f"bom.csv lists {r}, which design.py does not have" for r in sorted(refs_bom - {p.ref for p in D.PARTS})]
    result(4, "BOM and order pack regenerate identically", not det,
           f"{', '.join(bom_files + order_files)} = committed; {len(refs_bom)} refs in the BOM", det)


# ----------------------------------------------------------------------------- 5 / 6 fab files
DATE = re.compile(rb"(CreationDate[^\n]*|[)}] date [^\n]*|/CreationDate \([^)]*\)|/ModDate \([^)]*\))")


def same_but_dates(a: bytes, b: bytes):
    return DATE.sub(b"<date>", a) == DATE.sub(b"<date>", b)


def check_pos(tmp):
    out = tmp / "pos.csv"
    kicad("pcb", "export", "pos", "--output", str(out), "--format", "csv", "--units", "mm", "--side", "both", str(PCB))
    a, b = out.read_bytes(), (FAB / "vein_finder-pos.csv").read_bytes()
    rows = list(csv.DictReader(open(FAB / "vein_finder-pos.csv")))
    sides = Counter(r["Side"] for r in rows)
    result(5, "Placement file = board", a == b, f"{len(rows)} parts ({dict(sides)}); regenerated file identical: {a == b}")


def check_gerbers(tmp):
    g = tmp / "gerbers"
    g.mkdir()
    kicad("pcb", "export", "gerbers", "--output", str(g) + "/", "--layers", GERBER_LAYERS, "--subtract-soldermask", str(PCB))
    kicad("pcb", "export", "drill", "--output", str(g) + "/", "--format", "excellon", "--excellon-separate-th",
          "--generate-map", "--map-format", "pdf", str(PCB))
    det = []
    made = sorted(p.name for p in g.iterdir())
    have = sorted(p.name for p in (FAB / "gerbers").iterdir())
    if made != have:
        det.append(f"file sets differ: only regenerated {sorted(set(made) - set(have))}, only committed {sorted(set(have) - set(made))}")
    identical = dated = 0
    for name in sorted(set(made) & set(have)):
        a, b = (g / name).read_bytes(), (FAB / "gerbers" / name).read_bytes()
        if a == b:
            identical += 1
        elif same_but_dates(a, b):
            dated += 1
        elif name.endswith(".pdf"):
            det.append(f"{name}: differs (a drill-map drawing, not a fab input)")
        else:
            det.append(f"{name}: differs beyond the creation date")
    with zipfile.ZipFile(FAB / "vein_finder-gerbers.zip") as z:
        names = sorted(z.namelist())
        zip_ok = names == have and all(z.read(n) == (FAB / "gerbers" / n).read_bytes() for n in names)
    if not zip_ok:
        det.append("the zip does not hold exactly the files in fab/gerbers")
    fab_inputs = [n for n in det if not n.split(":")[0].endswith(".pdf")]
    ok = not fab_inputs
    result(6, "Gerbers and drill = board", ok if not det else (ok and "PASS*"),
           f"{len(have)} files: {identical} identical, {dated} identical apart from the creation date; "
           f"zip = folder: {zip_ok}", det)


# ----------------------------------------------------------------------------- 7 order facts
def check_facts(b, outline):
    import make_order
    F = make_order.BOARD
    det, got = [], {}
    x0, y0, x1, y1 = outline.bounds
    got["size"] = f"{x1 - x0:.1f} × {y1 - y0:.1f} mm"
    got["layers"] = b.GetCopperLayerCount()
    got["thickness"] = f"{mm(b.GetDesignSettings().GetBoardThickness()):.1f} mm"
    text = PCB.read_text()
    cu = re.findall(r'\(layer "[FB]\.Cu" \(type "copper"\) \(thickness ([\d.]+)\)', text)
    got["copper"] = f"{', '.join(sorted(set(cu)))} mm" if cu else "no stackup in the file (fab default)"
    tracks = [t for t in b.GetTracks() if t.GetClass() in ("PCB_TRACK", "PCB_ARC")]
    vias = [t for t in b.GetTracks() if t.GetClass() == "PCB_VIA"]
    got["min track"] = f"{min(mm(t.GetWidth()) for t in tracks):.2f} mm"
    got["vias"] = sorted({(round(mm(v.GetWidth()), 3), round(mm(v.GetDrillValue()), 3)) for v in vias})
    pro = json.loads((KI / "vein_finder.kicad_pro").read_text())
    clear = sorted({c["clearance"] for c in pro["net_settings"]["classes"]})
    holes = Counter()
    for fp in b.GetFootprints():
        for p in fp.Pads():
            if p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH):
                dx, dy = mm(p.GetDrillSize().x), mm(p.GetDrillSize().y)
                kind = "plated" if p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH else "unplated"
                shape = f"{dx:.2f} mm" if abs(dx - dy) < 1e-6 else f"{min(dx, dy):.2f} × {max(dx, dy):.2f} mm slot"
                holes[(kind, shape, fp.GetReference()[0] if fp.GetReference().startswith("H") else fp.GetReference())] += 1
    got["holes"] = dict(holes)
    if not F["size"].startswith(got["size"]):
        det.append(f"size: order pack {F['size']}, board outline {got['size']}")
    if got["layers"] != F["layers"]:
        det.append(f"layers: order pack {F['layers']}, board {got['layers']}")
    if got["thickness"] != F["thickness"]:
        det.append(f"thickness: order pack {F['thickness']}, board {got['thickness']}")
    if cu and set(cu) != {"0.035"}:
        det.append(f"copper: order pack {F['copper']}, stackup {got['copper']}")
    if got["min track"] != "0.25 mm" or "0.25 mm" not in F["track"]:
        det.append(f"track: order pack {F['track']}, board minimum {got['min track']}")
    if clear != [0.2] or "0.2 mm minimum gap" not in F["track"]:
        det.append(f"clearance: order pack {F['track']}, net classes {clear}")
    for pad, drill in got["vias"]:
        if f"{pad:g} mm" not in F["via"] or f"{drill:g} mm" not in F["via"]:
            det.append(f"via {pad:g} / {drill:g} mm on the board, not in the order pack ('{F['via']}')")
    pins = holes.get(("plated", "1.00 mm", "H"), 0)
    slots = sorted(k[1] for k in holes if k[0] == "plated" and "slot" in k[1])
    if pins != 6 or "1.0 mm plated (6 locating pins)" not in F["holes"]:
        det.append(f"pin holes: order pack '{F['holes']}', board {pins} × 1.00 mm plated")
    if slots != ["0.60 × 1.20 mm slot", "0.60 × 1.60 mm slot"] or "0.6 × 1.2 and 0.6 × 1.6 mm" not in F["holes"]:
        det.append(f"slots: order pack '{F['holes']}', board {slots}")
    unplated = {k: v for k, v in holes.items() if k[0] == "unplated"}
    summary = (f"{got['size']}, {got['layers']} layers, {got['thickness']}, copper {got['copper']}, "
               f"min track {got['min track']}, clearance {clear}, vias {got['vias']}, holes {dict(holes)}")
    if unplated:
        det.append(f"unplated holes the order pack does not mention: {unplated}")
    result(7, "Order-pack board facts = board", not det, summary, det)


# ----------------------------------------------------------------------------- 8 edge
def check_edge(b, outline):
    edge = outline.boundary
    shapely.prepare(edge)
    rows = []                                          # (distance, what, layer)
    layers = ((pcbnew.F_Cu, "F.Cu"), (pcbnew.B_Cu, "B.Cu"))
    for fp in b.GetFootprints():
        for p in fp.Pads():
            for L, name in layers:
                if p.IsOnLayer(L):
                    g = pad_poly(p, L)
                    if not g.is_empty:
                        rows.append((edge.distance(g), f"{fp.GetReference()} pad {p.GetNumber() or '-'}", name))
    for t in b.GetTracks():
        for L, name in layers:
            if t.IsOnLayer(L):
                kind = {"PCB_VIA": "via", "PCB_ARC": "arc"}.get(t.GetClass(), "track")
                rows.append((edge.distance(track_poly(t)), f"{kind} {t.GetNetname()}", name))
    for z in b.Zones():
        for L, name in layers:
            if z.IsOnLayer(L):
                g = poly_set_to_shapely(z.GetFilledPolysList(L))
                if not g.is_empty:
                    rows.append((edge.distance(g), f"pour {z.GetNetname()}", name))
    rows.sort()
    bad = [r for r in rows if r[0] < (EDGE_MIN_J1 if r[1].startswith("J1 pad") else EDGE_MIN) - TOL]
    j1 = [r for r in rows if r[1].startswith("J1 pad")]
    rest = [r for r in rows if not r[1].startswith("J1 pad")]
    result(8, "Copper to board edge", not bad,
           f"{len(rows)} copper items; closest outside J1 {rest[0][0]:.3f} mm ({rest[0][1]}, {rest[0][2]}); "
           f"J1 closest {j1[0][0]:.3f} mm ({j1[0][1]})",
           [f"below the rule: {d:.3f} mm {w} {L}" for d, w, L in bad] +
           [f"closest: {d:.3f} mm {w} {L}" for d, w, L in rows[:8]])
    return rows


# ----------------------------------------------------------------------------- 9 outline
def check_outline(outline):
    import ezdxf
    L = json.loads(LAYOUT_DOCS.read_text())
    cad = unary_union([Polygon(rings[0], rings[1:]) for rings in L["board_outline"]])
    pcb = to_device(outline)
    doc = ezdxf.readfile(DXF)
    rings = []
    for e in doc.modelspace():
        if e.dxftype() == "LWPOLYLINE":
            if any(abs(b) > 1e-12 for *_, b in e.get_points("xyb")):
                raise SystemExit("the DXF has arcs (bulges): extend check 9")
            pts = [(p[0], -p[1]) for p in e.get_points("xy")]      # written with y mirrored
            rings.append(Polygon(pts))
    rings.sort(key=lambda p: -p.area)
    dxf = Polygon(rings[0].exterior.coords, [r.exterior.coords for r in rings[1:]]) if rings else Polygon()
    d1 = pcb.symmetric_difference(cad).area
    h1 = pcb.boundary.hausdorff_distance(cad.boundary)
    d2 = dxf.symmetric_difference(cad).area
    h2 = dxf.boundary.hausdorff_distance(cad.boundary)
    n_holes = len(cad.interiors) if cad.geom_type == "Polygon" else None
    mirror = dxf.boundary.hausdorff_distance(shapely.transform(cad, lambda a: a * [1, -1]).boundary)
    ok = h1 <= SIMPLIFY + 1e-4 and h2 < 1e-6
    result(9, "Outline: PCB = layout.json = DXF", ok,
           f"area {cad.area:.1f} mm², {n_holes} inner holes; PCB vs CAD: max gap {h1:.4f} mm, within the "
           f"{SIMPLIFY} mm simplification in make_pcb.py (area diff {d1:.3f} mm²); DXF vs CAD: max gap {h2:.1e} mm; "
           f"the outline is mirror-symmetric to {mirror:.3f} mm, so the DXF reads the same either way up")


# ----------------------------------------------------------------------------- 10 silk
def check_silk(b):
    silk = {pcbnew.F_SilkS: "F.SilkS", pcbnew.B_SilkS: "B.SilkS"}
    lines, texts = [], []
    for fp in b.GetFootprints():
        ref = fp.GetReference()
        for t in (fp.Reference(), fp.Value()):
            if t.GetLayer() in silk and t.IsVisible():
                texts.append((mm(t.GetTextHeight()), mm(t.GetTextThickness()), f"{ref} {t.GetText()}", silk[t.GetLayer()]))
        for g in fp.GraphicalItems():
            if g.GetLayer() not in silk:
                continue
            if g.GetClass() == "FP_TEXT":
                if g.IsVisible():
                    texts.append((mm(g.GetTextHeight()), mm(g.GetTextThickness()), f"{ref} {g.GetText()}", silk[g.GetLayer()]))
            else:
                lines.append((mm(g.GetWidth()), f"{ref} outline", silk[g.GetLayer()]))
    for d in b.GetDrawings():
        if d.GetLayer() not in silk:
            continue
        if d.GetClass() == "PCB_TEXT":
            texts.append((mm(d.GetTextHeight()), mm(d.GetTextThickness()), f"board text '{d.GetText()}'", silk[d.GetLayer()]))
        else:
            lines.append((mm(d.GetWidth()), "board graphic", silk[d.GetLayer()]))
    thin = [l for l in lines if l[0] < SILK_LINE_MIN - TOL]
    small = [t for t in texts if t[0] < SILK_TEXT_MIN - TOL]
    thin_text = [t for t in texts if t[1] < SILK_LINE_MIN - TOL]
    widths = Counter(round(l[0], 3) for l in lines)
    sizes = Counter((round(t[0], 2), round(t[1], 3)) for t in texts)
    det = [f"text {h:.2f} mm high, {w:.3f} mm stroke: {what} ({L})" for h, w, what, L in sorted(texts)]
    ok = True if not (thin or small or thin_text) else "WARN"
    result(10, "Silkscreen vs JLCPCB minimums", ok,
           f"{len(lines)} lines, widths {dict(widths)}; {len(texts)} texts (height, stroke) {dict(sizes)}; "
           f"below the minimum: {len(thin)} lines, {len(small)} text heights, {len(thin_text)} text strokes", det)


def main():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        for d in ("bom", "order"):
            (tmp / d).mkdir()
        check_drc(tmp)
        check_fills()
        check_nets(tmp)
        check_bom(tmp)
        check_pos(tmp)
        check_gerbers(tmp)
        b = pcbnew.LoadBoard(str(PCB))
        outline = board_outline(b)
        check_facts(b, outline)
        check_edge(b, outline)
        check_outline(outline)
        check_silk(b)
    for n in NOTES:
        print("note:", n)
    for n, name, status, summary, det in sorted(RESULTS):
        print(f"{n:2d} {status:5s} {name}: {summary}")
        for d in det[:40]:
            print(f"         {d}")
    fails = [r for r in RESULTS if r[2] == "FAIL"]
    print(f"{len(RESULTS) - len(fails)}/{len(RESULTS)} checks without failures")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
