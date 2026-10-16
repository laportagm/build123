#!/usr/bin/env bash
# Fetch the third-party tools and library files the build uses into build/ (gitignored):
#   KiCad 7.0.11 symbol and footprint libraries (only the files used), Freerouting 2.0.1,
#   avr-gcc 14.1.0 (ATtiny1614 support).  KiCad 7 itself: your OS package (apt install kicad).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LIB="$ROOT/build/kicadlib"; mkdir -p "$LIB/sym" "$LIB/fp" "$LIB/tools" "$ROOT/build/tools"
KS=https://gitlab.com/kicad/libraries/kicad-symbols/-/raw/7.0.11
KF=https://gitlab.com/kicad/libraries/kicad-footprints/-/raw/7.0.11
for s in Device power MCU_Microchip_ATtiny Battery_Management Connector Switch Transistor_FET Diode Driver_LED \
         Connector_Generic Regulator_Switching; do
  [ -f "$LIB/sym/$s.kicad_sym" ] || curl -fsSL -o "$LIB/sym/$s.kicad_sym" "$KS/$s.kicad_sym"
done
fp() { mkdir -p "$LIB/fp/$1.pretty"; [ -f "$LIB/fp/$1.pretty/$2.kicad_mod" ] || curl -fsSL -o "$LIB/fp/$1.pretty/$2.kicad_mod" "$KF/$1.pretty/$2.kicad_mod"; }
fp Resistor_SMD R_0603_1608Metric_Pad0.98x0.95mm_HandSolder
fp Capacitor_SMD C_0603_1608Metric_Pad1.08x0.95mm_HandSolder
fp Capacitor_SMD C_0805_2012Metric_Pad1.18x1.45mm_HandSolder
fp Capacitor_SMD C_1206_3216Metric_Pad1.33x1.80mm_HandSolder
fp LED_SMD LED_1206_3216Metric_Pad1.42x1.75mm_HandSolder
fp LED_SMD LED_0603_1608Metric
fp Diode_SMD D_SOD-123
fp Package_SO SOIC-14_3.9x8.7mm_P1.27mm
fp Package_TO_SOT_SMD SOT-23
fp Package_TO_SOT_SMD SOT-23-6
fp Inductor_SMD L_Sunlord_SWPA4018S
fp TestPoint TestPoint_Pad_1.5x1.5mm
JAR="$LIB/tools/freerouting-2.0.1.jar"
[ -f "$JAR" ] || curl -fsSL -o "$JAR" https://github.com/freerouting/freerouting/releases/download/v2.0.1/freerouting-2.0.1.jar
AVR="$ROOT/build/tools/avr-gcc-14.1.0-x64-linux"
if [ ! -d "$AVR" ]; then
  curl -fsSL https://github.com/ZakKemble/avr-gcc-build/releases/download/v14.1.0-1/avr-gcc-14.1.0-x64-linux.tar.bz2 \
    | tar -xj -C "$ROOT/build/tools"
fi
echo "tools ready in $ROOT/build"
