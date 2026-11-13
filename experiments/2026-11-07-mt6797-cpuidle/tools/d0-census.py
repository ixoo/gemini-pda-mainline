#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""D0: deep-idle condition census on the running station (read-only).

Stage D0 of experiments/2026-11-07-mt6797-cpuidle/README.md ("Deep idle with
the screen off: the SODI route"). Run as root with python3 -I.

  d0-census.py run CASE     wait for the idle blank, take CPU1-9 offline,
                            record 60 s, restore the CPUs; log to
                            /tmp/d0-CASE.log
  d0-census.py cirq         read the SYS_CIRQ block once; log to
                            /tmp/d0-cirq.log (run last, separately)

Hypothesis: with the screen blanked and CPU0 alone, the station fails the
vendor's deep-idle and SODI conditions on the infra clock gates and the
display power domain, and passes on one CPU, MSDC and the multimedia
domains.
Unique observation: the exact list of blocking gates and domains, and how
often each one blocks, in each case (Wi-Fi joined and idle; music playing).
Decision: the blocking list becomes P3's work list. If Wi-Fi or audio
themselves hold a required gate, deep idle with them active is out and only
plain dark idle remains for those cases.

Every register access is a 32-bit load through a /dev/mem mapping; the
script never stores to a register. The mapping is opened read-write only
because ctypes needs a writable buffer to make a single 32-bit load. Only
always-on blocks are read: INFRACFG_AO, SPM, TOPCKGEN, APMIXED and the GIC
distributor. Nothing in MMSYS, AUDIO, MSDC or any other block that can be
clock-gated or powered off is touched; their state comes from sysfs and
debugfs. The only state change is CPU hotplug: CPU1-9 offline for the
window and back afterwards (CPU8 before CPU9, as the A72 module requires).
"""
import ctypes
import mmap
import os
import re
import sys
import time

ROOT = os.environ.get("D0_ROOT", "")          # test hook: a fake / tree
FAKE_MEM = os.environ.get("D0_FAKE_MEM")      # test hook: a file for /dev/mem
WINDOW_S = int(os.environ.get("D0_WINDOW_S", "60"))
BLANK_TIMEOUT_S = int(os.environ.get("D0_BLANK_TIMEOUT_S", "300"))

# --- always-on registers (physical address, name) ---------------------------
INFRA = 0x10001000
SPM = 0x10006000
TOPCK = 0x10000000
APMIXED = 0x1000C000
GICD = 0x19000000
CIRQ = 0x10204000

# Vendor names (mt_idle_mt6797.h): INFRA0 = 0x94, INFRA1 = 0x90, INFRA2 = 0xb0.
# A set bit in a status word means the clock is gated (off).
CG = {"INFRA0": INFRA + 0x094, "INFRA1": INFRA + 0x090, "INFRA2": INFRA + 0x0B0}
# Vendor condition masks: a bit set here must be gated before entry.
MASKS = {
    "dpidle": {"INFRA0": 0x00460802, "INFRA1": 0x03AFF900, "INFRA2": 0x21FE36FD},
    "sodi":   {"INFRA0": 0x00440802, "INFRA1": 0x03AFF900, "INFRA2": 0x21FE36FD},
}
PWR_STATUS, PWR_STATUS_2ND = SPM + 0x180, SPM + 0x184
CPU_PWR_STATUS, CPU_PWR_STATUS_2ND = SPM + 0x188, SPM + 0x18C
DOMAINS = {"DIS": 3, "ISP": 5, "VDE": 7, "MFG": 12, "MJC": 20, "VEN": 21, "AUDIO": 24}
DPIDLE_OFF = ("DIS", "ISP", "VDE", "MFG", "MJC", "VEN")
SODI_OFF = ("ISP", "VDE", "MFG", "MJC", "VEN")
# APMIXED PLL CON0 (bit 0 enable), offsets from mainline clk-mt6797.c.
PLLS = {"MAINPLL": 0x220, "UNIVPLL": 0x230, "MFGPLL": 0x240, "MSDCPLL": 0x250,
        "IMGPLL": 0x260, "TVDPLL": 0x270, "CODECPLL": 0x290, "APLL1": 0x2A0,
        "APLL2": 0x2B4, "VDECPLL": 0x2E4}
SNAPSHOT = (
    [("INFRA_CG_STA_0x090", INFRA + 0x090), ("INFRA_CG_STA_0x094", INFRA + 0x094),
     ("INFRA_CG_STA_0x0b0", INFRA + 0x0B0),
     ("PWR_STATUS", PWR_STATUS), ("PWR_STATUS_2ND", PWR_STATUS_2ND),
     ("CPU_PWR_STATUS", CPU_PWR_STATUS), ("CPU_PWR_STATUS_2ND", CPU_PWR_STATUS_2ND),
     ("SPM_PCM_CON0", SPM + 0x018), ("SPM_PCM_FSM_STA", SPM + 0x17C),
     ("SPM_CPU_IDLE_STA", SPM + 0x174)]
    + [("CLK_CFG_%d" % i, TOPCK + 0x40 + 0x10 * i) for i in range(8)]
    + [("%s_CON0" % n, APMIXED + o) for n, o in PLLS.items()]
)


class Mem:
    """32-bit loads from physical addresses, one page mapping per page."""

    def __init__(self):
        path = FAKE_MEM or "/dev/mem"
        flags = os.O_RDWR | (0 if FAKE_MEM else os.O_SYNC)
        self.fd = os.open(path, flags)
        self.pages = {}

    def rd(self, addr):
        if addr & 3:
            raise ValueError("unaligned 0x%x" % addr)
        page, off = addr & ~0xFFF, addr & 0xFFF
        if page not in self.pages:
            self.pages[page] = mmap.mmap(self.fd, 0x1000, mmap.MAP_SHARED,
                                         mmap.PROT_READ | mmap.PROT_WRITE,
                                         offset=page if not FAKE_MEM else 0)
        return ctypes.c_uint32.from_buffer(self.pages[page], off).value


def path(p):
    return ROOT + p


def rtext(p, default=""):
    try:
        with open(path(p)) as f:
            return f.read()
    except OSError as e:
        return default or "<%s>" % e.strerror


def wtext(p, s):
    with open(path(p), "w") as f:
        f.write(s)


def online():
    return rtext("/sys/devices/system/cpu/online").strip()


def cpu_online(cpu):
    return rtext("/sys/devices/system/cpu/cpu%d/online" % cpu, "0").strip() == "1"


class Log:
    def __init__(self, name):
        self.f = open("/tmp/d0-%s.log" % name, "w")

    def __call__(self, *a):
        line = " ".join(str(x) for x in a)
        print(line)
        self.f.write(line + "\n")

    def block(self, title, text):
        self(title)
        print(text)
        self.f.write(text if text.endswith("\n") else text + "\n")

    def sync(self):
        self.f.flush()
        os.fsync(self.f.fileno())


def blanked():
    """True when every backlight is powered down and no DRM connector is On."""
    bls = [d for d in os.listdir(path("/sys/class/backlight"))] \
        if os.path.isdir(path("/sys/class/backlight")) else []
    if not bls:
        return False
    for d in bls:
        if rtext("/sys/class/backlight/%s/bl_power" % d).strip() != "4":
            return False
    drm = path("/sys/class/drm")
    for d in (os.listdir(drm) if os.path.isdir(drm) else []):
        if rtext("/sys/class/drm/%s/dpms" % d, "Off").strip() == "On":
            return False
    return True


def display_state():
    out = []
    for d in sorted(os.listdir(path("/sys/class/backlight"))) \
            if os.path.isdir(path("/sys/class/backlight")) else []:
        out.append("backlight %s bl_power=%s brightness=%s" % (
            d, rtext("/sys/class/backlight/%s/bl_power" % d).strip(),
            rtext("/sys/class/backlight/%s/brightness" % d).strip()))
    drm = path("/sys/class/drm")
    for d in sorted(os.listdir(drm)) if os.path.isdir(drm) else []:
        if os.path.exists(path("/sys/class/drm/%s/dpms" % d)):
            out.append("drm %s status=%s dpms=%s enabled=%s" % (
                d, rtext("/sys/class/drm/%s/status" % d).strip(),
                rtext("/sys/class/drm/%s/dpms" % d).strip(),
                rtext("/sys/class/drm/%s/enabled" % d).strip()))
    return "\n".join(out)


def interrupts():
    """{irq label: (cpu0 count, total over the online columns)}."""
    lines = rtext("/proc/interrupts").splitlines()
    if not lines:
        return {}
    cpus = lines[0].split()
    res = {}
    for ln in lines[1:]:
        parts = ln.split()
        if not parts:
            continue
        key = parts[0].rstrip(":")
        nums = []
        for p in parts[1:1 + len(cpus)]:
            if not p.isdigit():
                break
            nums.append(int(p))
        name = " ".join(parts[1 + len(nums):])
        cpu0 = nums[0] if cpus and cpus[0] == "CPU0" and nums else 0
        res["%s %s" % (key, name)] = (cpu0, sum(nums))
    return res


def decode(m, log, tag):
    log("== registers (%s)" % tag)
    vals = {}
    for name, addr in SNAPSHOT:
        v = m.rd(addr)
        vals[name] = v
        log("%-22s 0x%08x = 0x%08x" % (name, addr, v))
    for st in ("dpidle", "sodi"):
        for g, a in CG.items():
            blocked = MASKS[st][g] & ~m.rd(a) & 0xFFFFFFFF
            log("%s %s blocking bits 0x%08x %s" % (
                st, g, blocked, bits(blocked)))
    p1, p2 = vals["PWR_STATUS"], vals["PWR_STATUS_2ND"]
    on = [n for n, b in DOMAINS.items() if (p1 >> b) & (p2 >> b) & 1]
    log("domains on:", " ".join(on) or "none")
    log("dpidle domain blockers:", " ".join(d for d in DPIDLE_OFF if d in on) or "none")
    log("sodi domain blockers:", " ".join(d for d in SODI_OFF if d in on) or "none")
    log("PLLs enabled:", " ".join(n for n in PLLS if vals["%s_CON0" % n] & 1))
    return vals


def bits(v):
    return "[" + ",".join(str(i) for i in range(32) if v >> i & 1) + "]"


def gic(m, log):
    typer = m.rd(GICD + 0x004)
    n = min((typer & 0x1F) + 1, 32)
    log("GICD_TYPER 0x%08x, %d enable words" % (typer, n))
    for i in range(1, n):
        log("GICD_ISENABLER%-2d 0x%08x = 0x%08x" % (
            i, GICD + 0x100 + 4 * i, m.rd(GICD + 0x100 + 4 * i)))


def msdc_rpm():
    out = []
    base = path("/sys/bus/platform/devices")
    for d in sorted(os.listdir(base)) if os.path.isdir(base) else []:
        if re.search(r"mmc|msdc", d):
            out.append("%s runtime_status=%s" % (
                d, rtext("/sys/bus/platform/devices/%s/power/runtime_status" % d).strip()))
    return "\n".join(out)


def enabled_clocks():
    txt = rtext("/sys/kernel/debug/clk/clk_summary")
    keep = [ln for ln in txt.splitlines()[:3]]
    for ln in txt.splitlines()[3:]:
        f = ln.split()
        # name, enable count, prepare count, protect count, rate, ...
        if len(f) > 2 and f[1].isdigit() and int(f[1]) > 0:
            keep.append(ln)
    return "\n".join(keep)


def hotplug_down(log):
    taken = []
    for cpu in range(9, 0, -1):
        if cpu_online(cpu):
            wtext("/sys/devices/system/cpu/cpu%d/online" % cpu, "0")
            taken.append(cpu)
    log("took offline:", " ".join(map(str, sorted(taken))) or "none",
        "-> online", online())
    return taken


def hotplug_up(log, taken):
    for cpu in sorted(taken):
        try:
            wtext("/sys/devices/system/cpu/cpu%d/online" % cpu, "1")
        except OSError as e:
            log("cpu%d did not come back: %s" % (cpu, e))
    log("restored -> online", online())


def run(case):
    if os.geteuid() != 0 and not ROOT:
        sys.exit("run as root")
    log = Log(case)
    log("D0 census, case %s, %s" % (case, time.strftime("%Y-%m-%d %H:%M:%S %z")))
    log("Hypothesis: " + __doc__.split("Hypothesis:")[1].split("Every register")[0].strip())
    log("kernel", rtext("/proc/sys/kernel/osrelease").strip(),
        "boot_id", rtext("/proc/sys/kernel/random/boot_id").strip())
    log("online at start", online())
    log("A72 module loaded:", os.path.isdir(path("/sys/module/mt6797_a72")))
    m = Mem()

    log("waiting up to %d s for the idle blank; do not touch any input" % BLANK_TIMEOUT_S)
    t0 = time.time()
    before = online()
    while not blanked():
        if time.time() - t0 > BLANK_TIMEOUT_S:
            log("STOP: no blank within %d s" % BLANK_TIMEOUT_S)
            log.block("display:", display_state())
            log.sync()
            sys.exit(1)
        time.sleep(1)
    log("blanked after %.0f s; online before %s, after the blank %s%s" % (
        time.time() - t0, before, online(),
        "" if before == online() else " (something hotplugged on the blank)"))
    log.block("display:", display_state())

    taken = hotplug_down(log)
    try:
        time.sleep(5)
        decode(m, log, "start")
        gic(m, log)
        log.block("MSDC runtime PM:", msdc_rpm())
        log.block("pm_genpd_summary:", rtext("/sys/kernel/debug/pm_genpd/pm_genpd_summary"))
        log.block("clk_summary, enable count > 0:", enabled_clocks())
        log.sync()

        irq0 = interrupts()
        counts = {st: {g: [0] * 32 for g in CG} for st in MASKS}
        dom_counts = {d: 0 for d in DOMAINS}
        unblanked = 0
        for _ in range(WINDOW_S):
            time.sleep(1)
            if not blanked():
                unblanked += 1
            for g, a in CG.items():
                on_bits = ~m.rd(a) & 0xFFFFFFFF
                for st in MASKS:
                    b = MASKS[st][g] & on_bits
                    for i in range(32):
                        if b >> i & 1:
                            counts[st][g][i] += 1
            p = m.rd(PWR_STATUS) & m.rd(PWR_STATUS_2ND)
            for d, b in DOMAINS.items():
                if p >> b & 1:
                    dom_counts[d] += 1
        irq1 = interrupts()

        log("== %d s window, 1 Hz samples" % WINDOW_S)
        log("samples not blanked:", unblanked)
        log("online during the window:", online())
        for st in MASKS:
            for g in CG:
                hits = ["bit%d:%d" % (i, c) for i, c in enumerate(counts[st][g]) if c]
                log("%s %s blocking (bit:samples) %s" % (st, g, " ".join(hits) or "none"))
        log("domain on (samples):", " ".join("%s:%d" % kv for kv in dom_counts.items()))
        log("interrupts during the window (CPU0 delta / all delta):")
        for k in sorted(irq1, key=lambda k: -(irq1[k][1] - irq0.get(k, (0, 0))[1])):
            d0 = irq1[k][0] - irq0.get(k, (0, 0))[0]
            dt = irq1[k][1] - irq0.get(k, (0, 0))[1]
            if dt:
                log("  %8d %8d  %s" % (d0, dt, k))
        decode(m, log, "end")
        log.block("MSDC runtime PM (end):", msdc_rpm())
        log.block("clk_summary, enable count > 0 (end):", enabled_clocks())
    finally:
        hotplug_up(log, taken)
        log.sync()
    log("done: /tmp/d0-%s.log" % case)


def cirq():
    """SYS_CIRQ v1 read-only registers: status, mask, sensitivity, polarity."""
    log = Log("cirq")
    m = Mem()
    for name, off in (("STA", 0x000), ("MASK", 0x080), ("SENS", 0x140), ("POL", 0x200)):
        for i in range(7):
            a = CIRQ + off + 4 * i
            log("CIRQ_%s%d 0x%08x = 0x%08x" % (name, i, a, m.rd(a)))
    log("CIRQ_CONTROL 0x%08x = 0x%08x" % (CIRQ + 0x300, m.rd(CIRQ + 0x300)))
    log.sync()


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "run" and re.fullmatch(r"[a-z0-9-]+", sys.argv[2]):
        run(sys.argv[2])
    elif len(sys.argv) == 2 and sys.argv[1] == "cirq":
        cirq()
    else:
        sys.exit(__doc__)
