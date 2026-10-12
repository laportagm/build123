"""
KiCad 7 PCB builder (pcbnew Python API) driven by design.py and the gate-2 layout.

Coordinates: device frame (mm, +x tail, +y left, window centre at the origin) mapped to
the KiCad page with y flipped:  X = X0 + x,  Y = Y0 - y.  Footprint angles: a device-frame
CCW angle a becomes KiCad -a.  Back-side parts are flipped after placement and their pad
positions are checked numerically (`check_pads`).
"""
from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path

import pcbnew

X0, Y0 = 110.0, 100.0
MM = pcbnew.FromMM


def kpt(x, y):
    return pcbnew.VECTOR2I(MM(X0 + x), MM(Y0 - y))


def dev(p):
    return (pcbnew.ToMM(p.x) - X0, Y0 - pcbnew.ToMM(p.y))


class BoardBuilder:
    def __init__(self, fp_dirs, thickness=1.0):
        self.b = pcbnew.BOARD()
        self.fp_dirs = [Path(d) for d in (fp_dirs if isinstance(fp_dirs, (list, tuple)) else [fp_dirs])]
        self.nets = {}
        ds = self.b.GetDesignSettings()
        ds.SetBoardThickness(MM(thickness))
        self.b.SetCopperLayerCount(2)

    # ---------------------------------------------------------------- nets
    def net(self, name):
        if name not in self.nets:
            ni = pcbnew.NETINFO_ITEM(self.b, name)
            self.b.Add(ni)
            self.nets[name] = ni
        return self.nets[name]

    def netclasses(self, classes):
        """classes: {name: dict(track=mm, clearance=mm, via=mm, drill=mm, nets=[...])}"""
        ns = self.b.GetDesignSettings().m_NetSettings
        for name, c in classes.items():
            nc = pcbnew.NETCLASS(name)
            nc.SetTrackWidth(MM(c["track"]))
            nc.SetClearance(MM(c["clearance"]))
            nc.SetViaDiameter(MM(c["via"]))
            nc.SetViaDrill(MM(c["drill"]))
            if name == "Default":
                ns.m_DefaultNetClass = nc
            else:
                ns.m_NetClasses[name] = nc
                for n in c.get("nets", []):
                    ns.m_NetClassPatternAssignments.append(
                        pcbnew.NETCLASS_PATTERN_ASSIGNMENT(pcbnew.EDA_COMBINED_MATCHER(n, pcbnew.CTX_NETCLASS), name)) \
                        if hasattr(pcbnew, "NETCLASS_PATTERN_ASSIGNMENT") else None
                    self.net(n).SetNetClass(nc) if hasattr(self.net(n), "SetNetClass") else None

    # ---------------------------------------------------------------- outline / holes
    def outline(self, rings_polys, width=0.1):
        for poly in rings_polys:
            for ring in poly:
                pts = ring[:-1] if ring[0] == ring[-1] else ring
                for i in range(len(pts)):
                    a, b = pts[i], pts[(i + 1) % len(pts)]
                    s = pcbnew.PCB_SHAPE(self.b)
                    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
                    s.SetLayer(pcbnew.Edge_Cuts)
                    s.SetWidth(MM(width))
                    s.SetStart(kpt(*a))
                    s.SetEnd(kpt(*b))
                    self.b.Add(s)

    def npth(self, ref, x, y, d):
        fp = pcbnew.FOOTPRINT(self.b)
        fp.SetReference(ref)
        fp.Reference().SetVisible(False)
        fp.SetValue(f"NPTH {d:.2f}")
        fp.Value().SetVisible(False)
        pad = pcbnew.PAD(fp)
        pad.SetAttribute(pcbnew.PAD_ATTRIB_NPTH)
        pad.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
        pad.SetDrillShape(pcbnew.PAD_DRILL_SHAPE_CIRCLE)
        pad.SetSize(pcbnew.VECTOR2I(MM(d), MM(d)))
        pad.SetDrillSize(pcbnew.VECTOR2I(MM(d), MM(d)))
        pad.SetLayerSet(pad.UnplatedHoleMask())
        fp.Add(pad)
        fp.SetPosition(kpt(x, y))
        fp.SetAttributes(pcbnew.FP_EXCLUDE_FROM_POS_FILES | pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_BOARD_ONLY)
        self.b.Add(fp)
        return fp

    def keepout(self, ring, layers=("F.Cu",), footprints=True, tracks=False, vias=False, pads=False, name=""):
        z = pcbnew.ZONE(self.b)
        z.SetIsRuleArea(True)
        z.SetDoNotAllowFootprints(footprints)
        z.SetDoNotAllowTracks(tracks)
        z.SetDoNotAllowVias(vias)
        z.SetDoNotAllowPads(pads)
        z.SetDoNotAllowCopperPour(False)
        ls = pcbnew.LSET()
        for l in layers:
            ls.AddLayer(self.b.GetLayerID(l))
        z.SetLayerSet(ls)
        z.SetZoneName(name)
        ol = z.Outline()
        ol.NewOutline()
        pts = ring[:-1] if ring[0] == ring[-1] else ring
        for (x, y) in pts:
            ol.Append(MM(X0 + x), MM(Y0 - y))
        self.b.Add(z)
        return z

    def gnd_pour(self, net="GND", clearance=0.25, min_width=0.2):
        bb = self.b.GetBoardEdgesBoundingBox()
        for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
            z = pcbnew.ZONE(self.b)
            z.SetLayer(layer)
            z.SetNet(self.net(net))
            z.SetLocalClearance(MM(clearance))
            z.SetMinThickness(MM(min_width))
            z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
            z.SetThermalReliefGap(MM(0.3))
            z.SetThermalReliefSpokeWidth(MM(0.35))
            z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
            ol = z.Outline()
            ol.NewOutline()
            m = MM(2)
            for (x, y) in ((bb.GetLeft() - m, bb.GetTop() - m), (bb.GetRight() + m, bb.GetTop() - m),
                           (bb.GetRight() + m, bb.GetBottom() + m), (bb.GetLeft() - m, bb.GetBottom() + m)):
                ol.Append(x, y)
            self.b.Add(z)

    # ---------------------------------------------------------------- footprints
    def footprint(self, part):
        lib, name = part.footprint.split(":")
        fp = None
        for d in self.fp_dirs:
            if (d / f"{lib}.pretty" / f"{name}.kicad_mod").exists():
                fp = pcbnew.FootprintLoad(str(d / f"{lib}.pretty"), name)
                break
        if fp is None:
            raise FileNotFoundError(part.footprint)
        fp.SetFPID(pcbnew.LIB_ID(lib, name))
        fp.SetReference(part.ref)
        fp.SetValue(part.value)
        x, y, rot = part.place
        fp.SetPosition(kpt(x, y))
        self.b.Add(fp)
        if part.side == "B":
            # flip first (KiCad mirrors about the x axis), then set the board orientation
            fp.Flip(fp.GetPosition(), False)
        # top: device CCW angle -> KiCad -angle (y flipped); a flipped footprint's local x
        # axis is mirrored as well, so there the device angle is the KiCad angle
        fp.SetOrientationDegrees(rot if part.side == "B" else -rot)
        for pad in fp.Pads():
            num = pad.GetNumber()
            net = part.pins.get(num)
            if net:
                pad.SetNet(self.net(net))
        if part.mpn:
            fp.SetField("MPN", part.mpn) if hasattr(fp, "SetField") else None
        return fp

    def check_pads(self, ref):
        fp = self.b.FindFootprintByReference(ref)
        return {p.GetNumber(): dev(p.GetPosition()) for p in fp.Pads()}

    # ---------------------------------------------------------------- routing
    def route(self, work: Path, jar: Path, passes=40, threads=4):
        work.mkdir(parents=True, exist_ok=True)
        dsn, ses = work / "board.dsn", work / "board.ses"
        if not pcbnew.ExportSpecctraDSN(self.b, str(dsn)):
            raise RuntimeError("DSN export failed")
        cmd = ["java", "-Djava.awt.headless=true", "-jar", str(jar), "--gui.enabled=false",
               "-de", str(dsn), "-do", str(ses), "-mp", str(passes), "-mt", str(threads), "-oit", "1.0"]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
        (work / "freerouting.log").write_text(r.stdout + "\n" + r.stderr)
        if not ses.exists():
            raise RuntimeError("Freerouting produced no session file; see freerouting.log")
        self.import_ses(ses)
        return ses

    def import_ses(self, ses: Path):
        """Add Freerouting's wires and vias to the board.  (KiCad 7's ImportSpecctraSES only
        works on the board open in the GUI.)  SES coordinates are in 1/res um with y negated."""
        import re
        from sexp import find, first, parse
        root = parse(Path(ses).read_text())[0]
        routes = first(root, "routes")
        res = first(routes, "resolution")
        unit_nm = 1000.0 / float(res[2]) if res[1] == "um" else 25400.0 / float(res[2])
        n_tr = n_via = 0
        for net in find(first(routes, "network_out"), "net"):
            ni = self.net(str(net[1]))
            for w in find(net, "wire"):
                path = first(w, "path")
                layer = self.b.GetLayerID(str(path[1]))
                width = int(float(path[2]) * unit_nm)
                c = [float(v) for v in path[3:]]
                pts = [(int(c[i] * unit_nm), int(-c[i + 1] * unit_nm)) for i in range(0, len(c) - 1, 2)]
                for (x1, y1), (x2, y2) in zip(pts[:-1], pts[1:]):
                    t = pcbnew.PCB_TRACK(self.b)
                    t.SetStart(pcbnew.VECTOR2I(x1, y1))
                    t.SetEnd(pcbnew.VECTOR2I(x2, y2))
                    t.SetWidth(width)
                    t.SetLayer(layer)
                    t.SetNet(ni)
                    self.b.Add(t)
                    n_tr += 1
            for v in find(net, "via"):
                m = re.search(r"_(\d+):(\d+)_um", str(v[1]))
                dia, drill = (int(m.group(1)) * 1000, int(m.group(2)) * 1000) if m else (MM(0.6), MM(0.3))
                via = pcbnew.PCB_VIA(self.b)
                via.SetPosition(pcbnew.VECTOR2I(int(float(v[2]) * unit_nm), int(-float(v[3]) * unit_nm)))
                via.SetWidth(dia)
                via.SetDrill(drill)
                via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
                via.SetNet(ni)
                self.b.Add(via)
                n_via += 1
        return n_tr, n_via

    def finish(self, path: Path, drc_path: Path):
        """Save, reload (the standalone zone filler needs a loaded board's project context),
        fill the pours, run DRC and save again.  Returns the DRC report text."""
        self.b.Save(str(path))
        b = pcbnew.LoadBoard(str(path))
        filler = pcbnew.ZONE_FILLER(b)
        filler.Fill(b.Zones())
        pcbnew.WriteDRCReport(b, str(drc_path), pcbnew.EDA_UNITS_MILLIMETRES, True)
        b.Save(str(path))
        self.b = b
        return Path(drc_path).read_text()

    def fill(self):
        self.b.BuildConnectivity()
        self._filler = pcbnew.ZONE_FILLER(self.b)          # keep a reference (SWIG lifetime)
        zones = self.b.Zones()
        self._filler.Fill(zones)
        self.b.BuildConnectivity()

    def drc(self, path: Path):
        pcbnew.WriteDRCReport(self.b, str(path), pcbnew.EDA_UNITS_MILLIMETRES, True)
        return Path(path).read_text()

    def save(self, path: Path):
        self.b.Save(str(path))
