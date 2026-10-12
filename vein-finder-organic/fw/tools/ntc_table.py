"""NTC lookup table for fw/src/logic.c: Murata NCP18XH103F03RB (10 k, B25/50 = 3380 K) to
GND under a 10 k resistor from NTC_EN; 10-bit ratiometric ADC (full scale 1023)."""
import math

R25, BETA, RFIX = 10e3, 3380.0, 10e3


def counts(t_c):
    r = R25 * math.exp(BETA * (1 / (t_c + 273.15) - 1 / 298.15))
    return round(1023 * r / (r + RFIX))


if __name__ == "__main__":
    print([counts(t) for t in range(0, 71, 5)])
