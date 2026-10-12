"""
Silkscreen tidy-up before the fab outputs:

  * every reference designator at 0.8 mm, put at the nearest spot around its part that is
    clear of pad openings, of all other silk and of the board edge; hidden if there is none
    (the assembly figures in the docs label every part anyway);
  * the board labels (name, revision, "personal prototype") on a free stretch of the
    underside.

    from silk import tidy;  tidy(board)        (make_pcb.py --stage finish calls it)

Personal prototype for bench evaluation - NOT a medical device.
"""
from __future__ import annotations

import math

import pcbnew
import shapely
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

from board import MM, dev, kpt

TEXT, THICK = 0.8, 0.12          # reference height and stroke, mm
GAP = 0.15                       # to pad openings and other silk, mm
EDGE = 0.25                      # to the board edge, mm
MASK = 0.05                      # solder-mask opening around a pad (KiCad's default 0 + fab margin)
LAYERS = {"F": (pcbnew.F_Cu, pcbnew.F_SilkS, pcbnew.F_CrtYd), "B": (pcbnew.B_Cu, pcbnew.B_SilkS, pcbnew.B_CrtYd)}


def bbox_poly(bb):
    x0, y0 = dev(pcbnew.VECTOR2I(bb.GetLeft(), bb.GetTop()))
    x1, y1 = dev(pcbnew.VECTOR2I(bb.GetRight(), bb.GetBottom()))
    return box(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))


def shape_geom(g):
    """Ink of a silk graphic as shapely geometry."""
    w = max(pcbnew.ToMM(g.GetWidth()), 0.05)
    t = g.GetShape()
    if t == pcbnew.SHAPE_T_SEGMENT:
        a, b = dev(g.GetStart()), dev(g.GetEnd())
        return (LineString([a, b]) if a != b else Point(a)).buffer(w / 2)
    if t == pcbnew.SHAPE_T_CIRCLE:
        c = Point(dev(g.GetCenter()))
        r = pcbnew.ToMM(g.GetRadius())
        if g.IsFilled():
            return c.buffer(r + w / 2)
        return c.buffer(r + w / 2).difference(c.buffer(max(r - w / 2, 0.0)))
    if t == pcbnew.SHAPE_T_ARC:
        pts = [dev(g.GetStart()), dev(g.GetArcMid()), dev(g.GetEnd())]
        return LineString(pts).buffer(w / 2)
    outline = bbox_poly(g.GetBoundingBox())          # rectangles, polygons
    return outline if g.IsFilled() else outline.exterior.buffer(w / 2)


def board_polygon(board):
    ps = pcbnew.SHAPE_POLY_SET()
    board.GetBoardPolygonOutlines(ps)
    polys = []
    for i in range(ps.OutlineCount()):
        ol = ps.Outline(i)
        holes = [[dev(ps.Hole(i, h).CPoint(k)) for k in range(ps.Hole(i, h).PointCount())] for h in range(ps.HoleCount(i))]
        polys.append(Polygon([dev(ol.CPoint(k)) for k in range(ol.PointCount())], holes))
    return unary_union(polys)


def pad_openings(board, layer):
    out = []
    for fp in board.GetFootprints():
        for p in fp.Pads():
            if p.IsOnLayer(layer):
                ps = pcbnew.SHAPE_POLY_SET()
                p.TransformShapeToPolygon(ps, layer, 0, 5000)
                for i in range(ps.OutlineCount()):
                    ol = ps.Outline(i)
                    out.append(Polygon([dev(ol.CPoint(k)) for k in range(ol.PointCount())]))
    return unary_union(out).buffer(MASK)


class Side:
    """What a text on one side must keep clear of."""

    def __init__(self, board, side, inner):
        cu, silk, _ = LAYERS[side]
        self.inner = inner
        self.openings = pad_openings(board, cu).buffer(GAP)
        shapely.prepare(self.openings)
        ink = [shape_geom(g) for fp in board.GetFootprints() for g in fp.GraphicalItems()
               if g.GetLayer() == silk and g.GetClass() != "FP_TEXT"]
        ink += [shape_geom(d) for d in board.GetDrawings() if d.GetLayer() == silk and d.GetClass() == "PCB_SHAPE"]
        self.ink = shapely.STRtree(ink) if ink else None
        self.texts = []                                   # text boxes placed so far

    def free(self, poly):
        if not self.inner.contains(poly) or self.openings.intersects(poly):
            return False
        if self.ink is not None and len(self.ink.query(poly, predicate="dwithin", distance=GAP)):
            return False
        return not any(poly.distance(q) < GAP for q in self.texts)


def _place(text, side, cx, cy, spots, angles=(0.0, 90.0)):
    """Try the spots (device frame offsets from the courtyard box, sized for each angle) and
    keep the first free one.  spots(w, h) -> [(x, y)]."""
    for ang in angles:
        text.SetTextAngleDegrees(ang)
        text.SetPosition(kpt(cx, cy))
        b = bbox_poly(text.GetBoundingBox())
        w, h = b.bounds[2] - b.bounds[0], b.bounds[3] - b.bounds[1]
        for x, y in spots(w, h):
            text.SetPosition(kpt(x, y))
            poly = bbox_poly(text.GetBoundingBox())
            if side.free(poly):
                side.texts.append(poly)
                return True
    return False


_KEEP = []


def clip_silk(board, inner):
    """Footprint silk lines that run off the board (the ring LEDs' outlines at the window and
    the horn slot) are cut back to EDGE inside it; the rest of each outline, cathode marks
    included, stays."""
    n = 0
    for fp in board.GetFootprints():
        for g in list(fp.GraphicalItems()):
            if g.GetLayer() not in (pcbnew.F_SilkS, pcbnew.B_SilkS) or g.GetClass() != "MGRAPHIC":
                continue
            g = g.Cast()
            if g.GetShape() != pcbnew.SHAPE_T_SEGMENT:
                continue
            w = pcbnew.ToMM(g.GetWidth())
            line = LineString([dev(g.GetStart()), dev(g.GetEnd())])
            room = inner.buffer(-w / 2)
            if room.contains(line):
                continue
            keep = line.intersection(room)
            pieces = [q for q in getattr(keep, "geoms", [keep]) if q.geom_type == "LineString" and not q.is_empty]
            n += 1
            if not pieces or max(q.length for q in pieces) < 0.2:
                fp.Remove(g)
                _KEEP.append(g)
                continue
            q = max(pieces, key=lambda q: q.length)
            g.SetStart(kpt(*q.coords[0]))
            g.SetEnd(kpt(*q.coords[-1]))
            g.SetLocalCoord()
    return n


def tidy(board, log=print):
    inner = board_polygon(board).buffer(-EDGE)
    shapely.prepare(inner)
    log(f"  silk lines cut back from the edge: {clip_silk(board, inner)}")
    sides = {s: Side(board, s, inner) for s in LAYERS}
    # board texts first: they are big and their place matters
    labels = [d for d in board.GetDrawings() if d.GetClass() == "PCB_TEXT"]
    for d in labels:
        side = sides["B" if d.GetLayer() == pcbnew.B_SilkS else "F"]
        if d.GetLayer() not in (pcbnew.F_SilkS, pcbnew.B_SilkS):
            continue
        x0, y0 = dev(d.GetPosition())
        if side.free(bbox_poly(d.GetBoundingBox())):
            side.texts.append(bbox_poly(d.GetBoundingBox()))
            continue
        # search outward from where it was put, along the board's long axis first
        ok = _place(d, side, x0, y0, lambda w, h: sorted(
            ((x0 + dx * 0.5, y0 + dy * 0.4) for dx in range(-40, 41) for dy in range(-60, 61)),
            key=lambda q: math.hypot(q[0] - x0, (q[1] - y0) * 1.5)), angles=(d.GetTextAngleDegrees(),))
        log(f"  label '{d.GetText()[:24]}...': {'moved' if ok else 'NO FREE SPOT'}")
    hidden = []
    # wire and test pads first (their names are what the build guide refers to), then the
    # rest, biggest first
    fps = sorted(board.GetFootprints(), key=lambda f: (not f.GetReference().startswith("TP"),
                                                       -bbox_poly(f.GetBoundingBox(False, False)).area))
    for fp in fps:
        s = "B" if fp.IsFlipped() else "F"
        ref = fp.Reference()
        if fp.GetReference().startswith("TP"):
            # a test or wire pad is labelled with its function (BAT+, UPDI, BTN...): the
            # value field goes on the silkscreen in place of the reference
            ref.SetVisible(False)
            ref = fp.Value()
            ref.SetLayer(LAYERS[s][1])
        ref.SetTextSize(pcbnew.VECTOR2I(MM(TEXT), MM(TEXT)))
        ref.SetTextThickness(MM(THICK))
        ref.SetVisible(True)
        ref.SetKeepUpright(False)
        cy_poly = fp.GetCourtyard(LAYERS[s][2])
        if cy_poly.OutlineCount():
            ol = cy_poly.Outline(0)
            x0, y0, x1, y1 = Polygon([dev(ol.CPoint(k)) for k in range(ol.PointCount())]).bounds
        else:
            x0, y0, x1, y1 = bbox_poly(fp.GetBoundingBox(False, False)).bounds
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2

        def spots(w, h, x0=x0, y0=y0, x1=x1, y1=y1, cx=cx, cy=cy):
            out = []
            for d in (0.05, 0.3, 0.6, 1.0, 1.5, 2.0, 2.6, 3.2):
                xs = (cx, x0 + w / 2, x1 - w / 2, x0, x1)
                ys = (cy, y0 + h / 2, y1 - h / 2, y0, y1)
                out += [(x, y1 + h / 2 + d) for x in xs] + [(x, y0 - h / 2 - d) for x in xs]
                out += [(x1 + w / 2 + d, y) for y in ys] + [(x0 - w / 2 - d, y) for y in ys]
                out += [(x1 + w / 2 + d, y1 + h / 2 + d), (x0 - w / 2 - d, y1 + h / 2 + d),
                        (x1 + w / 2 + d, y0 - h / 2 - d), (x0 - w / 2 - d, y0 - h / 2 - d)]
            return out
        if not _place(ref, sides[s], cx, cy, spots):
            ref.SetVisible(False)
            hidden.append(fp.GetReference())
    log(f"  references hidden (no free spot): {hidden or 'none'}")
    return hidden
