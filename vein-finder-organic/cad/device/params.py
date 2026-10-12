"""
Gate-2 layout parameters: the single source of truth for every internal dimension.

All lengths in mm, device coordinates (window centre at the origin, +x toward the tail,
z = 0 at the lowest skin-contact point, waterline z_part ~ 4.18 from the skin build).
Part dimensions marked (datasheet) are nominal values of the part class chosen here;
the exact part numbers and their datasheets are fixed at the electronics gate, which
re-checks every one of them against this file.
"""

# ----------------------------------------------------------------------------- walls
WALL = 1.8              # top shell, normal thickness (brief: >= 1.6)
SEAM_WALL = 0.7         # thin spot 1 (approved): light seam
MEMBRANE_WALL = 0.40    # thin spot 2 (approved): button skin
MASK_GAP = 0.10         # seam-mask fence tops stay this far below the inner surface
BRIDGE_GAP = 0.6        # button bridge keeps this clearance to the inner surface

# ----------------------------------------------------------------------------- PCB
PCB_T = 1.0             # 2-layer FR4, black mask
PCB_CLEAR = 0.3         # board edge to the cavity wall, in plan
PCB_LEVELS = (0.0, 0.35, 0.7, 1.0, 1.3)   # heights above the waterline the outline must clear
PCB_CORNER_R = 1.0

# ----------------------------------------------------------------------------- battery
# Jauch LP503040JH, 600 mAh, protected (Digi-Key: 42.0 x 30.5 x 5.4 incl. PCM).
# Gate 3: the cell sits ON the board, on foam tape.  The gate-2 board had a bay cut-out
# for a cell on 0.4 mm tape on the sole; the only tape sold at the four distributors is
# 1.0-1.6 mm (Adafruit 5019), and the cut-out split the board into halves that could not
# be routed.  The board under the cell is a component keep-out (traces only).
BATT_T, BATT_W, BATT_L = 5.4, 30.5, 42.0
BATT_X0 = 21.0          # front edge; the cell lies across (42 mm along y)
BATT_FOAM = 1.6         # double-sided foam tape on the board (Adafruit 5019: 1.0-1.6 mm)
BATT_CLEAR = 0.4        # component keep-out margin around the cell on the board
BATT_TOP_CLEAR = 0.4    # cell top to anything above it

# ----------------------------------------------------------------------------- LEDs
# 12 LEDs on the PCB underside in two alternating, mirror-symmetric banks of six.
# SunLED 1206 dome-lens LEDs (gate-3 parts): XZM2MR55W-3 (660 nm) and XZM2CRK55W-3
# (625 nm, "620" bank).  Body 3.2 x 1.6 mm +-0.2 (datasheet), dome 1.6 mm; seated height
# 2.10 mm max for the 660 and 1.80 mm max for the 625 (Digi-Key parametrics).  The LEDs lie
# tangentially.  The pocket in the sole is a straight black light channel through to the
# skin face, with a shallow relief over the land pattern for the solder fillets.
LED_PKG = (3.2, 1.6)            # (tangential, radial) body, nominal
LED_TOL = 0.2                   # body tolerance (datasheet)
LED_H = {"660": 2.10, "620": 1.80}
LED_LAND = (4.4, 1.75)          # KiCad LED_1206_3216Metric_Pad1.42x1.75mm_HandSolder
LED_POCKET_CLEAR = 0.3          # per side, radially, around the nominal body (tolerance + placement)
LED_POCKET_LAND = 0.15          # tangentially the pocket runs 0.15 past the land ends (solder fillets),
                                # so the sole needs no shallow reliefs (they would thin it below 1.6)
LED_COUNT = 12
LED_BANK_ORDER = ("620", "660")   # banks at ring positions k = 0, 2, 4 and k = 1, 3, 5 (k = 0 at +-step/2):
                                  # the lower 625 nm parts take +-11.7 deg, where the sole is thinnest (1.81 mm)
LED_EDGE_MARGIN = 0.25          # pad copper to the board edge
# Murata NCP18XH103F03RB, 0603: (length, width, max height); lies radially at theta = 0
NTC_PKG = (1.6, 0.8, 0.95)
NTC_LAND = (2.8, 0.95)          # KiCad R_0603_1608Metric_Pad0.98x0.95mm_HandSolder
NTC_FLOOR = 0.7                 # PETG left between the NTC pocket and the skin face

# ----------------------------------------------------------------------------- seam
SEAM_R = 18.6           # plan radius of the hairline on the bore's back slope
SEAM_HALF_DEG = 44.0    # arc from -44 to +44 deg
SEAM_SLOT_W = 0.5       # plan width of the slot (about 1 mm along the 60 deg slope)
MASK_T = 0.8            # fence thickness
MASK_CHANNEL = 1.3      # channel width between the fences (plan); the 0603 status LEDs' 0.95 mm lands sit inside
MASK_END_DEG = 2.5      # end caps beyond the slot ends
MASK_CAP_W = 2.4        # end caps (tangential)
MASK_EAR = (3.0, 2.4, 3.0)  # ear outside each cap that carries the pin: width, radial length, height
# Locating pins: posts pulled from a 2.54 mm male header (Sullins PRPC040SAAN-RC: 0.64 mm
# square, 0.91 mm across the corners), dropped into plated 1.0 mm holes (pad 1.7) with the
# printed part on top as the squaring jig, soldered from the underside and cut flush there.
PIN_SQ = 0.64
PIN_ABOVE = 1.3
PIN_HOLE_PART = 1.05    # blind hole in the printed part (slip fit on the corners), 1.6 deep
PIN_HOLE_DEPTH = 1.6
PIN_FILLET_RELIEF = (1.9, 0.3)  # counterbore in the part over the top pad's solder meniscus
PIN_HOLE_PCB = 1.0      # plated drill
PIN_PAD_PCB = 1.7
PIN_SOLE_RELIEF = (2.6, 0.8)    # pocket in the sole under the solder joint and cut pin end
SEAM_LED_COUNT = 5      # Lite-On LTST-C190KSKT 0603 amber LEDs on the PCB top, in the channel

# ----------------------------------------------------------------------------- button
BUTTON_AXES = (10.0, 13.0)      # membrane semi-axes (x, y) at its thin face, inside the thumb dish
MEMBRANE_TAPER = 2.0            # smooth (C2) run from the 0.45 mm skin to the full wall
SWITCH_BODY = (6.0, 6.0, 3.5)   # THT tact switch body (datasheet class)
SWITCH_H = 5.0                  # base to actuator top (datasheet class)
SWITCH_GAP = 0.05               # actuator top to membrane underside, nominal (shim to zero)
BRIDGE_X_W = 8.4                # bridge width along x: one constant width so it prints flat on its side
BRIDGE_LEG_Y = 23.6             # leg centre |y|, on the PCB side arms
BRIDGE_LEG = (8.4, 2.8)         # leg footprint (x, y)

# ----------------------------------------------------------------------------- magnets
# N35 discs, 1/4" diameter (gate-3 parts): Radial Magnets 8193 (1/4 x 1/8") and 8195
# (1/4 x 1/16"), Br 1.17-1.21 T.
#  * Horns: a 1/8" sole magnet stands 2.0 above the waterline, through the PCB hole and
#    1.0 mm into a counterbore in the top boss (dowel action: the two horn dowels align
#    the halves); a 1/16" magnet sits in the top boss.  At (-12, +-20.0) this leaves
#    >= 1.6 mm of sole under the pocket and >= 0.8 mm of shell over the top magnet.
#  * Tail: a 1/16" pair.  The sole is only 2.1-2.4 mm thick there, and a proud 1/8"
#    magnet would leave 0.67 mm of PETG under it; the 1/16" sole magnet stands just
#    0.15 mm above the PCB top (it still locates the board) and leaves >= 1.6 mm.
MAG_D = 6.35
MAG_BR = (1.17, 1.21)           # N35 remanence range, T
MAG_POCKET_CLEAR = 0.15         # diametral clearance in the pockets (magnets are glued)
MAG_DOWEL_CLEAR = 0.25          # diametral clearance of the counterbore around a proud magnet
MAG_PCB_HOLE = 6.75
MAG_BOSS_WALL = 1.6
MAG_GAP = 0.15                  # air gap between the two magnet faces
BOSS_PCB_GAP = 0.05             # boss underside above the PCB top (boards are 1.0 +- 0.1)
MAG_COVER_MIN = 0.8             # PETG left above the top magnet pocket
MAGNETS = ([dict(x=-12.0, y=s_ * 20.0, sole_h=3.18, top_h=1.59, proud=2.0, sole_pn="8193", top_pn="8195")
            for s_ in (1, -1)] +
           [dict(x=56.6, y=s_ * 12.0, sole_h=1.59, top_h=1.59, proud=PCB_T + 0.15, sole_pn="8195", top_pn="8195")
            for s_ in (1, -1)])
SOLE_FLOOR_MIN = 1.6            # brief: walls >= 1.6 mm (the sole's floors count)

# ----------------------------------------------------------------------------- USB-C
# GCT USB4515-GF-A: power-only (6-contact) mid-mount receptacle, "1.6 mm offset" (gate-3
# part; GCT 3D model and spec).  Shell 8.94 x 3.17 stadium, 7.13 long, contact tails to
# 7.50; the shell spans -1.606 / +1.566 about the board top, so on this 1.0 mm board it
# hangs 0.61 below the board into a pocket in the sole.  Board cut-out 9.24 wide, 5.70
# deep from the board edge; the face stands 0.85 in front of the board edge.  The tail tip
# is too thin for a flush port, so the port sits in a flat landing (the one deliberate
# flat on the skin) that lets a standard plug overmold (up to 12.4 mm wide) seat fully.
USB_W, USB_H, USB_L = 8.94, 3.17, 7.13
USB_TAILS = 7.50                # contact tails behind the face
USB_FACE_PROUD = 0.85           # face in front of the board edge (GCT footprint)
USB_X_FACE = 61.1               # receptacle face = board edge at the legs (60.24) + 0.85
USB_ZC = PCB_T - 0.02           # receptacle centre above the waterline (shell -1.606 / +1.566)
USB_CLEAR = 0.25                # opening around the receptacle shell, per side
USB_OPEN_DEPTH = 1.5            # the full-clearance opening runs this far in from the face
USB_FLOOR_CLEAR = 0.05          # behind it the shell rests on the sole (pocket floor clearance)
USB_LAND_DX = 0.1               # landing plane in front of the receptacle face
USB_LAND_HW = 6.9               # landing half-width (y)
USB_LAND_R = 1.5                # plan radius at the landing's side corners
USB_PCB_NOTCH = (USB_FACE_PROUD + 5.70, 4.62)   # PCB cut-out: depth from the face, half-width
# shell legs (plated slots) and contact pads, from the face: (behind face, |y|, slot l, pad l)
USB_LEGS = [(2.40, 5.62, 1.6, 2.1), (6.40, 5.62, 1.2, 1.7)]
USB_PADS_X = 7.35               # contact pad row behind the face; pads 0.8 x 1.2 at |y| 0.5, 1.52, 2.75
