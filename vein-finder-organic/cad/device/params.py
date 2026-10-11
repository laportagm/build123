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
# Jauch LP503040JH, 600 mAh, protected (datasheet max incl. PCM): 5.4 x 30.5 x 42.0
BATT_T, BATT_W, BATT_L = 5.4, 30.5, 42.0
BATT_X0 = 21.0          # front edge; the cell lies across (42 mm along y)
BATT_FOAM = 0.4         # double-sided foam tape on the sole
BATT_CLEAR = 0.4        # PCB cut-out clearance around the cell
BATT_TOP_CLEAR = 0.4    # cell top to anything above it

# ----------------------------------------------------------------------------- LEDs
# 12 LEDs on the PCB underside in two alternating, mirror-symmetric banks of six.
# Package class 2.0 x 2.0 mm (datasheet); the pocket in the sole is a straight
# black light channel through to the skin face.
LED_PKG = (2.0, 2.0)            # (tangential, radial)
LED_PAD_MARGIN = 0.15           # land pattern beyond the package edge (bottom-terminated)
LED_POCKET_CLEAR = 0.2          # per side, around the package
LED_COUNT = 12
LED_EDGE_MARGIN = 0.25          # pad copper to the board edge
NTC_PKG = (1.0, 0.5, 0.55)      # 0402 NTC: (tangential, radial, height) on the underside
NTC_FLOOR = 0.7                 # PETG left between the NTC pocket and the skin face

# ----------------------------------------------------------------------------- seam
SEAM_R = 18.6           # plan radius of the hairline on the bore's back slope
SEAM_HALF_DEG = 44.0    # arc from -44 to +44 deg
SEAM_SLOT_W = 0.5       # plan width of the slot (about 1 mm along the 60 deg slope)
MASK_T = 0.8            # fence thickness
MASK_CHANNEL = 1.0      # channel width between the fences (plan)
MASK_END_DEG = 2.5      # end caps beyond the slot ends
MASK_CAP_W = 2.4        # end caps (tangential), each carries a pin hole
PIN_D = 1.0             # locating pins: 1.0 mm brass/steel wire, 2.6 mm long
PIN_HOLE_PART = 1.05    # blind hole in the printed part (press fit), 1.6 deep
PIN_HOLE_PCB = 1.15     # plated or plain hole in the PCB
SEAM_LED_COUNT = 5      # 0402-class status LEDs on the PCB top, inside the channel

# ----------------------------------------------------------------------------- button
BUTTON_AXES = (10.0, 13.0)      # membrane semi-axes (x, y) at its thin face, inside the thumb dish
MEMBRANE_TAPER = 2.0            # smooth (C2) run from the 0.45 mm skin to the full wall
SWITCH_BODY = (6.0, 6.0, 3.5)   # THT tact switch body (datasheet class)
SWITCH_H = 5.0                  # base to actuator top (datasheet class)
SWITCH_GAP = 0.05               # actuator top to membrane underside, nominal (shim to zero)
BRIDGE_X_W = 8.4                # bridge width along x: one constant width so it prints flat on its side
BRIDGE_LEG_Y = 23.6             # leg centre |y|, on the PCB side arms
BRIDGE_LEG = (8.4, 2.4)         # leg footprint (x, y)

# ----------------------------------------------------------------------------- magnets
# N42 discs, 1/4" diameter (datasheet class): 1/8" thick in the sole, 1/16" thick in the
# top.  The sole magnet stands MAG_PROUD above the waterline, through a PCB hole and
# 0.5 mm into a counterbore in the top boss (dowel action: aligns the halves).
MAG_D = 6.35
MAG_H_SOLE, MAG_H_TOP = 3.18, 1.59
MAG_PROUD = 1.5                 # sole magnet top above the waterline (PCB is 1.0)
MAG_POCKET_CLEAR = 0.15         # diametral clearance in the pockets (magnets are glued)
MAG_DOWEL_CLEAR = 0.25          # diametral clearance of the counterbore around the proud magnet
MAG_PCB_HOLE = 6.75
MAG_BOSS_WALL = 1.6
MAG_GAP = 0.15                  # air gap between the two magnet faces
BOSS_PCB_GAP = 0.05             # boss underside above the PCB top (boards are 1.0 +- 0.1)
MAG_COVER_MIN = 0.8             # PETG left above the top magnet pocket
MAGNETS = [(-12.0, 20.5), (-12.0, -20.5), (56.6, 12.0), (56.6, -12.0)]

# ----------------------------------------------------------------------------- USB-C
# Mid-mount ("sink") 16-pin USB 2.0 receptacle class: shell 8.94 x 3.26 (stadium),
# 7.35 long (datasheet class).  The tail tip is too thin for a flush port, so the port
# sits in a flat landing (the one deliberate flat on the skin) that lets a standard
# plug overmold (up to 12.4 mm wide) seat fully.
USB_W, USB_H, USB_L = 8.94, 3.26, 7.35
USB_X_FACE = 61.6               # receptacle face (the skin's tail tip is at x = 62.6)
USB_ZC = 1.42                   # receptacle centre above the waterline
USB_CLEAR = 0.25                # opening around the receptacle shell, per side
USB_LAND_DX = 0.1               # landing plane in front of the receptacle face
USB_LAND_HW = 6.9               # landing half-width (y)
USB_LAND_R = 1.5                # plan radius at the landing's side corners
USB_PCB_NOTCH = (6.0, 4.65)     # PCB notch for the sinking body: depth from face, half-width
