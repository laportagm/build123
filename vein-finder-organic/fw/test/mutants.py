#!/usr/bin/env python3
"""Mutation check of the safety logic:  make -C fw mutants

Each mutant plants one small, plausible bug in src/logic.c (a wrong comparison, a missing
line), builds the host tests against it and runs them.  Every mutant must make the tests
fail; one that survives marks a safety rule the tests do not really check.  If logic.c
changes and a pattern below no longer matches exactly once, this script stops: update the
pattern, do not delete the mutant.

Host-side only: this measures the tests, not the hardware.
Personal prototype for bench evaluation - NOT a medical device.
"""
import pathlib
import subprocess
import sys
import tempfile

MUTANTS = [
    # thermal latch and derating
    ("cut-off at > 41.0 C instead of >=", "if (s->t_dc >= T_CUTOFF_DC)", "if (s->t_dc > T_CUTOFF_DC)"),
    ("release below 38.0 C instead of at",
     "else if (s->t_dc <= T_DERATE_DC)\n            s->hot_lock = false;",
     "else if (s->t_dc < T_DERATE_DC)\n            s->hot_lock = false;"),
    ("release at 39 C",
     "else if (s->t_dc <= T_DERATE_DC)\n            s->hot_lock = false;",
     "else if (s->t_dc <= T_DERATE_DC + 10)\n            s->hot_lock = false;"),
    ("derating floor = full current", "        return DERATE_FLOOR_PERMILLE;", "        return 1000u;"),
    ("derating not applied", "        d = d * derate_permille(s->t_dc) / 1000u;\n", ""),
    # sensor faults
    ("open NTC at > NTC_ADC_OPEN only", "if (adc >= NTC_ADC_OPEN)", "if (adc > NTC_ADC_OPEN)"),
    ("shorted NTC reads 0 C", "    return 700;\n}", "    return 0;\n}"),
    ("light before the first reading (N02)", " && s->t_dc != INT16_MIN) {", ") {"),
    # use and auto-off
    ("held button resets the auto-off (N01)", "if (tap || hold)\n", "if (tap || hold || s->btn_stable)\n"),
    ("no auto-off", "    if (s->on && s->idle_ticks >= AUTO_OFF_TICKS)\n        s->on = false;\n", ""),
    # outputs
    ("no make-before-break overlap", "            a = b = true;\n", ""),
    ("gates left on when off", "        s->gate_a = s->gate_b = false;\n        s->mbb_ticks = 0;", "        s->mbb_ticks = 0;"),
    ("bank A uses bank B's cap", "(s->bank == BANK_A) ? CAP_A_PERMILLE : CAP_B_PERMILLE", "CAP_B_PERMILLE"),
    # power and sleep
    ("USB power does not turn the LEDs off",
     "        s->on = false;                     /* no light while the cell charges */", "        ;"),
    ("battery lock ignored", "    if (s->on && s->batt_lock)\n        s->on = false;\n", ""),
    ("may sleep while on", "s->want_sleep = !s->on && ", "s->want_sleep = "),
]


def main():
    fw = pathlib.Path(__file__).resolve().parent.parent
    src = (fw / "src" / "logic.c").read_text()
    survived = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        for name, a, b in MUTANTS:
            n = src.count(a)
            if n != 1:
                sys.exit(f"pattern for '{name}' matches {n} times in src/logic.c: update mutants.py")
            (tmp / "logic.c").write_text(src.replace(a, b))
            subprocess.run(["gcc", "-std=c11", "-O1", "-w", f"-I{fw / 'src'}", str(fw / "test" / "test_logic.c"),
                            str(tmp / "logic.c"), "-lm", "-o", str(tmp / "t")], check=True)
            r = subprocess.run([str(tmp / "t")], capture_output=True, text=True)
            fails = sum(1 for line in r.stdout.splitlines() if line.startswith("FAIL"))
            print(f"  {'caught' if r.returncode else 'SURVIVED':8s} ({fails:2d} failing checks)  {name}")
            if r.returncode == 0:
                survived.append(name)
    print(f"{len(MUTANTS) - len(survived)}/{len(MUTANTS)} mutants caught")
    sys.exit(1 if survived else 0)


if __name__ == "__main__":
    main()
