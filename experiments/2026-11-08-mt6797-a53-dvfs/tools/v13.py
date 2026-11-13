#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""V13: idle wakeups and current with policy0 capped while blanked.

Tests V13a-c of experiments/2026-11-08-mt6797-a53-dvfs/README.md ("Idle wakeups
while blanked (V13)"). Run as root with python3 -I, detached:

  setsid -f python3 -I v13.py run </dev/null >/tmp/v13.out 2>&1
  python3 -I v13.py summary        afterwards; reads the /tmp/v13-*.dat files

The run waits for external power to go away, then for the desktop's own idle
blank; it never blanks the display. It then takes CPU1-9 offline, which leaves
CPU0 alone, and runs these windows:

  A   policy0 uncapped (1547000)  300 s traced, then 600 s untraced
  B   scaling_max_freq 481000     the same
  C   scaling_max_freq 221000     the same, then 60 s of a quiet test tone
  A2  uncapped again              600 s untraced, to bracket the gauge's drift

The fuel gauge is read at 1 Hz in every window. The tracing uses
trace-cmd start/stop/extract, so no reader runs during a window. The run stops
early, with the cap and the CPUs restored, if external power appears or the
display unblanks.

The writes are policy0/scaling_max_freq (481000, 221000, then 1547000, read
back each time) and CPU hotplug, restored by a finally block. Log:
/tmp/v13.log. Traces: /tmp/v13-{A,B,C}.dat.
"""
import math
import os
import pwd
import re
import signal
import struct
import subprocess
import sys
import time
import wave

TRACE_S = int(os.environ.get("V13_TRACE_S", "300"))
GAUGE_S = int(os.environ.get("V13_GAUGE_S", "600"))
TONE_S = 60
WAIT_S = 900
POLICY0 = "/sys/devices/system/cpu/cpufreq/policy0"
FULL = "1547000"
TONE = "/tmp/v13-tone.wav"
EVENTS = ["-e", "power:cpu_frequency",
          "-e", "sched:sched_wakeup", "-f", 'comm ~ "sugov*"',
          "-e", "regulator:regulator_set_voltage",
          "-e", "timer:hrtimer_expire_entry",
          "-e", "irq:irq_handler_entry",
          "-e", "workqueue:workqueue_execute_start"]


class Stop(Exception):
    pass


def rtext(p, default=""):
    try:
        with open(p) as f:
            return f.read().strip()
    except OSError:
        return default


def wtext(p, s):
    with open(p, "w") as f:
        f.write(s)


class Log:
    def __init__(self):
        self.f = open("/tmp/v13.log", "w")

    def __call__(self, *a):
        line = "%s %s" % (time.strftime("%H:%M:%S"), " ".join(str(x) for x in a))
        print(line, flush=True)
        self.f.write(line + "\n")
        self.f.flush()
        os.fsync(self.f.fileno())


def plugged():
    base = "/sys/class/power_supply"
    for d in os.listdir(base) if os.path.isdir(base) else []:
        if rtext("%s/%s/type" % (base, d)) != "Battery" and \
                rtext("%s/%s/online" % (base, d)) == "1":
            return d
    return None


def blanked():
    """Every backlight powered down and no DRM connector On."""
    bls = os.listdir("/sys/class/backlight") if os.path.isdir("/sys/class/backlight") else []
    if not bls or any(rtext("/sys/class/backlight/%s/bl_power" % d) != "4" for d in bls):
        return False
    drm = "/sys/class/drm"
    return not any(rtext("%s/%s/dpms" % (drm, d), "Off") == "On" for d in os.listdir(drm))


def battery():
    base = "/sys/class/power_supply"
    for d in os.listdir(base):
        if rtext("%s/%s/type" % (base, d)) == "Battery":
            return "%s/%s" % (base, d)
    raise SystemExit("no battery in %s" % base)


def online():
    return rtext("/sys/devices/system/cpu/online")


def set_cap(log, khz):
    wtext(POLICY0 + "/scaling_max_freq", khz)
    got = rtext(POLICY0 + "/scaling_max_freq")
    log("scaling_max_freq <- %s, read back %s" % (khz, got))
    if got != khz:
        raise Stop("scaling_max_freq read back %s, not %s" % (got, khz))


def sugov0_pid():
    for p in os.listdir("/proc"):
        if p.isdigit() and rtext("/proc/%s/comm" % p) == "sugov:0":
            return p
    return None


def snapshot():
    irq = {}
    for ln in rtext("/proc/interrupts").splitlines()[1:]:
        if "1100e000.i2c" in ln or "arch_timer" in ln:
            nums = [int(x) for x in ln.split()[1:] if x.isdigit()]
            irq["i2c6" if "1100e000.i2c" in ln else "arch_timer"] = sum(nums)
    tis = {}
    for ln in rtext(POLICY0 + "/stats/time_in_state").splitlines():
        f, t = ln.split()
        tis[int(f)] = int(t)
    cci = re.search(r"Total transition\s*:\s*(\d+)", rtext("/sys/class/devfreq/cci/trans_stat"))
    pid = sugov0_pid()
    vol = re.search(r"voluntary_ctxt_switches:\s*(\d+)",
                    rtext("/proc/%s/status" % pid)) if pid else None
    return {"t": time.monotonic(), "irq": irq, "tis": tis,
            "trans": int(rtext(POLICY0 + "/stats/total_trans", "0")),
            "cci": int(cci.group(1)) if cci else -1,
            "sugov": int(vol.group(1)) if vol else -1}


def report(log, tag, a, b, cur, volt):
    dt = b["t"] - a["t"]
    log("== %s: %.0f s" % (tag, dt))
    log("policy0 changes/s %.2f; sugov:0 voluntary switches/s %.2f; CCI transitions/s %.2f" % (
        (b["trans"] - a["trans"]) / dt, (b["sugov"] - a["sugov"]) / dt,
        (b["cci"] - a["cci"]) / dt))
    for k in sorted(b["irq"]):
        log("%s IRQ/s %.2f" % (k, (b["irq"][k] - a["irq"].get(k, 0)) / dt))
    log("time_in_state (10 ms units): " + " ".join(
        "%d:%d" % (f // 1000, b["tis"][f] - a["tis"].get(f, 0))
        for f in sorted(b["tis"]) if b["tis"][f] != a["tis"].get(f, 0)))
    gauge(log, cur, volt)


def gauge(log, cur, volt):
    if cur:
        mean = sum(cur) / len(cur)
        sd = math.sqrt(sum((c - mean) ** 2 for c in cur) / len(cur))
        log("current_now uA: n %d mean %.0f sd %.0f min %d max %d; voltage_now mean %.0f uV" % (
            len(cur), mean, sd, min(cur), max(cur), sum(volt) / len(volt)))


def sample(bat, cur, volt):
    p = plugged()
    if p:
        raise Stop("external power on %s" % p)
    if not blanked():
        raise Stop("display unblanked")
    cur.append(int(rtext(bat + "/current_now", "0")))
    volt.append(int(rtext(bat + "/voltage_now", "0")))


def window(log, bat, tag, seconds, trace):
    if trace:
        subprocess.run(["trace-cmd", "reset"], check=True, capture_output=True)
        subprocess.run(["trace-cmd", "start", "-b", "8192"] + EVENTS,
                       check=True, capture_output=True)
    a = snapshot()
    cur, volt = [], []
    try:
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            time.sleep(1)
            sample(bat, cur, volt)
    finally:
        b = snapshot()
        if trace:
            subprocess.run(["trace-cmd", "stop"], capture_output=True)
            r = subprocess.run(["trace-cmd", "extract", "-o", "/tmp/v13-%s.dat" % tag],
                               capture_output=True, text=True)
            log("extract /tmp/v13-%s.dat rc %d %s" % (tag, r.returncode,
                                                     (r.stdout + r.stderr).strip()[-300:]))
            subprocess.run(["trace-cmd", "reset"], capture_output=True)
        report(log, "%s %s" % (tag, "traced" if trace else "untraced"), a, b, cur, volt)


def make_tone():
    """60 s of 440 Hz at -26 dBFS, 48 kHz stereo S16."""
    rate, amp = 48000, 0.05 * 32767
    # 440 whole cycles a second, so one-second blocks join without a click.
    one = b"".join(struct.pack("<hh", v, v) for v in
                   (int(amp * math.sin(2 * math.pi * 440 * i / rate)) for i in range(rate)))
    with wave.open(TONE, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(rate)
        for _ in range(TONE_S):
            w.writeframes(one)


def substreams():
    out = {}
    for card in sorted(os.listdir("/proc/asound")):
        if not re.fullmatch(r"card\d+", card):
            continue
        for pcm in os.listdir("/proc/asound/" + card):
            if pcm.startswith("pcm") and pcm.endswith("p"):
                for sub in os.listdir("/proc/asound/%s/%s" % (card, pcm)):
                    if sub.startswith("sub"):
                        out["%s/%s/%s" % (card, pcm, sub)] = "/proc/asound/%s/%s/%s" % (card, pcm, sub)
    return out


def tone(log, bat):
    user = pwd.getpwuid(1000).pw_name
    t0wall = time.time()
    kmsg0 = len(subprocess.run(["dmesg"], capture_output=True, text=True).stdout.splitlines())
    cur, volt, ptr, top = [], [], {}, False
    p = subprocess.Popen(["runuser", "-u", user, "--", "env", "XDG_RUNTIME_DIR=/run/user/1000",
                          "pw-play", TONE], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True)
    t0 = time.monotonic()
    try:
        while p.poll() is None and time.monotonic() - t0 < TONE_S + 15:
            time.sleep(1)
            sample(bat, cur, volt)
            now = time.monotonic() - t0
            for name, d in substreams().items():
                st = rtext(d + "/status")
                state = re.search(r"state:\s*(\S+)", st)
                hw = re.search(r"hw_ptr\s*:\s*(\d+)", st)
                if state and state.group(1) == "XRUN" and name in ptr:
                    ptr[name]["bad"].append("%.0f s" % now)
                if state and state.group(1) == "RUNNING" and hw:
                    e = ptr.setdefault(name, {"first": (now, int(hw.group(1))), "bad": [],
                                              "rate": rtext(d + "/hw_params")})
                    e["last"] = (now, int(hw.group(1)))
            if now >= 30 and not top:
                top = True
                r = subprocess.run(["runuser", "-u", user, "--", "env",
                                    "XDG_RUNTIME_DIR=/run/user/1000", "pw-top", "-b", "-n", "3"],
                                   capture_output=True, text=True)
                log("pw-top at 30 s (rc %d):\n%s" % (r.returncode, (r.stdout + r.stderr)[-3000:]))
    finally:
        if p.poll() is None:
            p.terminate()
        out = p.communicate(timeout=10)[0]
    log("pw-play rc %s after %.1f s; output: %s" % (p.returncode, time.monotonic() - t0,
                                                  out.strip()[-300:] or "none"))
    for name, e in ptr.items():
        rate = re.search(r"rate:\s*(\d+)", e["rate"])
        (ta, pa), (tb, pb) = e["first"], e["last"]
        meas = (pb - pa) / (tb - ta) if tb > ta else 0
        log("%s: rate %s, hw_ptr advanced %.0f frames/s over %.0f s; XRUN seen at: %s" % (
            name, rate.group(1) if rate else "?", meas, tb - ta, e["bad"] or "never"))
    if not ptr:
        log("no playback substream was RUNNING")
    new = subprocess.run(["dmesg"], capture_output=True, text=True).stdout.splitlines()[kmsg0:]
    log("kernel lines during the tone: %d" % len(new))
    for ln in new[-40:]:
        log("  " + ln)
    j = subprocess.run(["journalctl", "--no-pager", "-o", "short-monotonic",
                        "--since", "@%d" % int(t0wall)], capture_output=True, text=True).stdout
    hits = [ln for ln in j.splitlines() if re.search(r"xrun|underrun|pipewire|wireplumber", ln, re.I)]
    log("journal pipewire/xrun lines during the tone: %d" % len(hits))
    for ln in hits[-40:]:
        log("  " + ln)
    log("== C tone")
    gauge(log, cur, volt)


def on_signal(signum, frame):
    raise Stop("signal %d" % signum)


def run():
    if os.geteuid() != 0:
        sys.exit("run as root")
    signal.signal(signal.SIGTERM, on_signal)
    signal.signal(signal.SIGHUP, on_signal)
    log = Log()
    log("V13, kernel %s, boot_id %s" % (rtext("/proc/sys/kernel/osrelease"),
                                        rtext("/proc/sys/kernel/random/boot_id")))
    log("rate_limit_us %s; policy0 governor %s, max %s; online %s; A72 module %s" % (
        rtext("/sys/devices/system/cpu/cpufreq/schedutil/rate_limit_us"),
        rtext(POLICY0 + "/scaling_governor"), rtext(POLICY0 + "/scaling_max_freq"),
        online(), os.path.isdir("/sys/module/mt6797_a72")))
    if rtext(POLICY0 + "/scaling_max_freq") != FULL:
        sys.exit("policy0 scaling_max_freq is not %s at the start" % FULL)
    make_tone()
    bat = battery()
    taken = []
    try:
        log("waiting up to %d s for external power to go away: unplug now" % WAIT_S)
        t0 = time.monotonic()
        while plugged():
            if time.monotonic() - t0 > WAIT_S:
                raise Stop("still plugged after %d s" % WAIT_S)
            time.sleep(1)
        log("unplugged; waiting up to %d s for the idle blank; do not touch the device" % WAIT_S)
        t0 = time.monotonic()
        while not blanked():
            if time.monotonic() - t0 > WAIT_S:
                raise Stop("no blank within %d s" % WAIT_S)
            if plugged():
                raise Stop("external power came back")
            time.sleep(1)
        log("blanked after %.0f s; online %s" % (time.monotonic() - t0, online()))
        time.sleep(20)
        for cpu in range(9, 0, -1):
            if rtext("/sys/devices/system/cpu/cpu%d/online" % cpu) == "1":
                wtext("/sys/devices/system/cpu/cpu%d/online" % cpu, "0")
                taken.append(cpu)
        log("took offline %s -> online %s" % (sorted(taken), online()))
        for tag, cap in (("A", FULL), ("B", "481000"), ("C", "221000")):
            set_cap(log, cap)
            time.sleep(10)
            window(log, bat, tag, TRACE_S, True)
            window(log, bat, tag, GAUGE_S, False)
        tone(log, bat)
        set_cap(log, FULL)
        time.sleep(10)
        window(log, bat, "A2", GAUGE_S, False)
        log("windows done; external power may come back now")
    except Stop as e:
        log("STOP: %s" % e)
    finally:
        try:
            set_cap(log, FULL)
        except Exception as e:  # keep restoring the CPUs
            log("RESTORE FAILED: scaling_max_freq: %s" % e)
        for cpu in sorted(taken):
            try:
                wtext("/sys/devices/system/cpu/cpu%d/online" % cpu, "1")
            except OSError as e:
                log("cpu%d did not come back: %s" % (cpu, e))
        log("restored -> online %s, scaling_max_freq %s" % (
            online(), rtext(POLICY0 + "/scaling_max_freq")))


def summary():
    pats = {
        "cpu_frequency": r"state=(\d+) cpu_id=(\d+)",
        "sched_wakeup": r"comm=(\S+)",
        "regulator_set_voltage": r"name=(\S+)",
        "hrtimer_expire_entry": r"function=(\S+)",
        "irq_handler_entry": r"name=(\S+)",
        "workqueue_execute_start": r"function (\S+)",
    }
    out = open("/tmp/v13-summary.txt", "w")
    for tag in ("A", "B", "C"):
        dat = "/tmp/v13-%s.dat" % tag
        if not os.path.exists(dat):
            continue
        txt = subprocess.run(["trace-cmd", "report", "-i", dat], capture_output=True,
                             text=True).stdout
        counts, first, last = {}, None, None
        for ln in txt.splitlines():
            m = re.search(r"\s(\d+\.\d+):\s+(\w+):\s+(.*)", ln)
            if not m:
                continue
            ts, ev, rest = float(m.group(1)), m.group(2), m.group(3)
            first = ts if first is None else first
            last = ts
            k = re.search(pats.get(ev, r"$^"), rest)
            key = (ev, " ".join(k.groups()) if k else "")
            counts[key] = counts.get(key, 0) + 1
        span = (last - first) if first is not None else 0
        out.write("== %s: %.1f s, lost-event lines %d\n" % (tag, span, txt.count("LOST")))
        for ev in pats:
            items = sorted(((c, k[1]) for k, c in counts.items() if k[0] == ev), reverse=True)
            out.write("%s total %d\n" % (ev, sum(c for c, _ in items)))
            for c, k in items[:12]:
                out.write("  %7d %7.2f/s  %s\n" % (c, c / span if span else 0, k))
    out.close()
    print(open("/tmp/v13-summary.txt").read())


if __name__ == "__main__":
    if sys.argv[1:] == ["run"]:
        run()
    elif sys.argv[1:] == ["summary"]:
        summary()
    else:
        sys.exit(__doc__)
