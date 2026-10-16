#!/usr/bin/env python3
"""Static checks of the compiled firmware that the host unit tests cannot make.

    python3 tools/check_build.py <avr-objdump> build/fw.elf      (run by `make -C fw`)

1. Race-free power-down.  deep_sleep() must read the button and VBUS pins with interrupts
   off and then run SEI immediately followed by SLEEP.  The AVR always executes the
   instruction after SEI before it takes a pending interrupt.  So a press or a USB plug-in
   that arrives after the pin check still wakes the part, instead of being swallowed by the
   pin ISR just before it powers down.  The compiler must not put anything between the two,
   and there must be no call (which could re-enable interrupts) and no other SEI between
   CLI and SEI.
2. The watchdog is set to the 1K-cycle period (about 1 s), through the CCP protected write,
   after waiting for the previous write to synchronise.
3. The watchdog is fed in main's tick path (a WDR in main), and nowhere else.

This reads the instructions the compiler produced.  It is not a test of the chip: sleep,
wake-up and the watchdog still need the bench checks in docs/06-verification.
Personal prototype for bench evaluation - NOT a medical device.
"""
import re
import subprocess
import sys

PORTA_IN = 0x0408          # PORTA.IN (data space)
VPORTA_IN_IO = 0x02        # VPORTA.IN (I/O space)
WDT_CTRLA = 0x0100
WDT_STATUS = 0x0101
CCP_IO = 0x34
CCP_IOREG = 0xD8
WDT_PERIOD_1KCLK = 0x08

INSN = re.compile(r"^\s*([0-9a-f]+):\s+(?:[0-9a-f]{2} )+\s*([a-z]+)\s*([^;]*)")
FUNC = re.compile(r"^[0-9a-f]+ <([A-Za-z_][\w.]*)>:$")


def disassemble(objdump, elf):
    out = subprocess.run([objdump, "-d", elf], capture_output=True, text=True, check=True).stdout
    insns, func = [], None
    for line in out.splitlines():
        m = FUNC.match(line)
        if m and not m.group(1).startswith((".L", "L0")):
            func = m.group(1)
            continue
        m = INSN.match(line)
        if m:
            insns.append((func, int(m.group(1), 16), m.group(2), m.group(3).strip()))
    return insns


def num(s):
    s = s.strip()
    return int(s, 16) if s.lower().startswith("0x") else int(s)


def main():
    objdump, elf = sys.argv[1], sys.argv[2]
    ins = disassemble(objdump, elf)
    fails = []

    # 1. power-down entry
    pairs = [i for i in range(1, len(ins)) if ins[i][2] == "sleep" and ins[i - 1][2] == "sei"]
    sleeps = [i for i in range(len(ins)) if ins[i][2] == "sleep"]
    if len(pairs) != 1:
        fails.append(f"expected one SEI immediately followed by SLEEP, found {len(pairs)}")
    for p in pairs:
        j = p - 2
        while j >= 0 and ins[j][2] != "cli" and ins[j][0] == ins[p][0]:
            j -= 1
        if j < 0 or ins[j][2] != "cli":
            fails.append(f"SEI;SLEEP at {ins[p][1]:#x}: no CLI before it in {ins[p][0]}")
            continue
        body = ins[j + 1:p - 1]
        bad = [b for b in body if b[2] in ("sei", "call", "rcall", "icall", "eicall", "reti")]
        if bad:
            fails.append(f"between CLI {ins[j][1]:#x} and SEI {ins[p - 1][1]:#x}: {[(hex(b[1]), b[2]) for b in bad]}")
        reads_pins = any((b[2] == "lds" and num(b[3].split(",")[1]) == PORTA_IN) or
                         (b[2] == "in" and num(b[3].split(",")[1]) == VPORTA_IN_IO) for b in body)
        if not reads_pins:
            fails.append("the pins are not read between CLI and SEI;SLEEP")
        print(f"  power-down: CLI at {ins[j][1]:#06x}, pins read, SEI;SLEEP at {ins[p - 1][1]:#06x} "
              f"({len(body)} instructions with interrupts off); {len(sleeps)} SLEEP instructions in all")

    # 2. watchdog enable: wait SYNCBUSY, CCP signature, CTRLA = 1KCLK right after the CCP write
    ok = False
    for k in range(len(ins)):
        f, a, op, args = ins[k]
        if op == "out" and num(args.split(",")[0]) == CCP_IO:
            nxt = ins[k + 1]
            if nxt[2] == "sts" and num(nxt[3].split(",")[0]) == WDT_CTRLA:
                src_ccp, src_val = args.split(",")[1].strip(), nxt[3].split(",")[1].strip()
                win = ins[max(0, k - 6):k]
                ccp = [w for w in win if w[2] == "ldi" and w[3].split(",")[0].strip() == src_ccp]
                val = [w for w in win if w[2] == "ldi" and w[3].split(",")[0].strip() == src_val]
                sync = any(w[2] == "lds" and num(w[3].split(",")[1]) == WDT_STATUS for w in win)
                if ccp and num(ccp[-1][3].split(",")[1]) == CCP_IOREG and val and \
                        num(val[-1][3].split(",")[1]) == WDT_PERIOD_1KCLK and sync:
                    ok = True
                    print(f"  watchdog: 1K-cycle period (~1 s) set at {nxt[1]:#06x} in {f}, after a SYNCBUSY wait")
    if not ok:
        fails.append("no protected write of WDT.CTRLA = 1KCLK after a SYNCBUSY wait")

    # 3. watchdog feed
    wdr = [(f, a) for f, a, op, _ in ins if op == "wdr"]
    if not wdr or any(f != "main" for f, _ in wdr):
        fails.append(f"WDR expected in main only, found {wdr}")
    else:
        print(f"  watchdog fed: WDR at {', '.join(hex(a) for _, a in wdr)} in main")

    for f in fails:
        print("FAIL", f)
    if fails:
        sys.exit(1)
    print("build checks passed")


if __name__ == "__main__":
    main()
