# Experiment: the charging guard moves into the kernel

| Field | Value |
| --- | --- |
| ID | `2026-11-02-gemini-kernel-charge-guard` |
| Status | `completed`: G1-G6 passed on the device, and the fix for the battery reading's overflow is confirmed at 24.8-25 °C; the temperature stop is shown by emulation, and no charge current was measured |
| Subsystem | BQ25896 charger, MT6351 fuel gauge and battery NTC |
| Device variant | named Gemini PDA (MT6797X), development station |
| Date(s) | 2026-11-02 to 2026-11-03 |
| Investigator(s) | project custodian |
| Tracking issue | none |

## Question

The owner, on charging and display blank: "1 and 2 need to be fixed in priority,
they are too sensitive to stay user side".
[`charge-guard`](../2026-10-30-mainline-dev-station/charge-guard.c) keeps the
[50/47 °C window](../2026-10-31-gemini-thermal-protection/README.md#step-3-design-a-battery-temperature-charging-stop)
and the [capacity limit](../2026-10-31-gemini-fuel-gauge/README.md) from
userspace. If it dies, the chip's watchdog restores charging within about 47 s.

**Question:** can the same behaviour run in the kernel, with no daemon and no
new charger write?

## Why this route

The route is mainline `bq25890_charger`, built in, with two opt-in patches.

Stock `bq25890` doesn't fit this board as it stands:
- Probe resets the chip, or with `linux,skip-reset` forces `CHG_CONFIG` on.
- It turns the watchdog off (REG07) and writes the ADC bits (REG02).
- It requires an interrupt. The only candidate is GPIO246/EINT158 `CHR_STAT`,
  [probably STAT rather than /INT](../2026-10-06-gemini-c2b-charger/README.md#interrupt-wiring-open).
- It caches REG03, so it wouldn't see a watchdog reset.
- It has no temperature or capacity stop.

The [C2b patches](../2026-10-06-gemini-c2b-charger/README.md) program current and
voltage, a decision the owner hasn't made, so they aren't used.

`charger-manager` wants the charger as a regulator. A new board driver would
duplicate this one and leave nowhere for later current control or charger status.

## The change

- [0517](../../patches/proposals/0517-dt-bindings-power-supply-bq25890-describe-firmware-c.patch):
  the binding.
- [0518](../../patches/proposals/0518-power-supply-bq25890-add-a-mode-that-leaves-the-chip.patch),
  `linux,no-chip-config`:
  - Only `CHG_CONFIG` and `WD_RST` reach the chip, enforced in
    `bq25890_field_write()`, which all the driver's writes go through.
  - Each is a read-modify-write of REG03, other bits as read.
  - Registers are read uncached. No interrupt or regulators.
  - Properties can't be written.
  - The ADC properties and the thermal zone are left out, since the gauge reports
    those. Reading `current_now` on the charger gives no data.
  - Any chip but a BQ25896 refuses to bind.
  - A failed probe stays failed, so its chip reads retry 5 times, 200 ms apart, and
    giving up logs at critical level. This came from an independent review of the
    patches. `-EPROBE_DEFER` doesn't do this job, because deferral only runs again
    when another driver happens to bind.
- [0519](../../patches/proposals/0519-power-supply-bq25890-stop-charging-by-the-battery-s-.patch),
  `linux,guard-battery`: a 10 s work item with `charge-guard`'s decisions.
- [0520](../../patches/proposals/0520-arm64-dts-mediatek-gemini-station-guard-charging-fro.patch):
  the board node and the battery's limits.
- Fragment: `CHARGER_BQ25890=y`, and `THERMAL_EMULATION=y` for testing. It stays for
  now: the [GPU test's `COOL` mode](../2026-11-02-mali-t880-first-job/gpu-test.sh)
  uses it too.
- Station alarm: `init` records `charge-guard=bound` or `charge-guard=MISSING` in
  `/run/station/status`, and logs `MISSING` to the kernel log.
- RAM root: `charge-guard` is out, and `power-status` uses `I2C_SLAVE_FORCE`, since
  the driver now owns the address. Hand reads need `i2cget -f`.

### Behaviour

| Condition | `charge-guard` | Kernel guard |
| --- | --- | --- |
| Battery at 50 °C or above | stop | stop, from `operating-range-celsius` |
| Below 47 °C | resume | resume, from `alert-celsius` |
| Temperature unreadable, or no battery supply | stop | stop; logged at critical level once it has lasted three passes |
| Open NTC | reads unreadable from the raw code, stop | reads the table's −20 °C clamp, stop at −20 °C or below; resume above −18 °C |
| Real battery at −20 °C or below | no stop | **stop: a new, stricter case** |
| Capacity at the limit, default 80 | stop | stop |
| 5 points below the limit | resume | resume |
| Limit 100 | off | off |
| Capacity unreadable | no stop | the last answer stands, with one warning; no stop if it has never been read |
| Set the limit | `/run/station/charge-limit` | `charge_control_end_threshold`, 50-100 |
| Stopped | `WD_RST` every 10 s | `WD_RST` every 10 s |
| Bootloader left it disabled, charging allowed | set at first pass | set at the first pass with a readable battery |

The first pass runs at probe. The gauge may not have registered yet, in which case
charging stays held off until the next pass, 10 s later. Before, `charge-guard`'s
first pass came at about 2 s.

`charge_control_start_threshold` reads the limit minus 5 and is read-only.

The first pass starts from `hot`, so a battery already inside 47-50 °C stays stopped
whatever the probe order. A guard property without `linux,no-chip-config` fails the probe,
and the binding says so.

## Writes to the chip

Registers written:

| Register | Bit | Effect |
| --- | --- | --- |
| REG03 | `CHG_CONFIG` | stop and resume, as before |
| REG03 | `WD_RST` | kick while stopped, as before |

Nothing else, so this needs no new-risk decision. The chip's watchdog stays on, so
registers stay at the chip's defaults, as on every station so far.

Also new: the driver reads REG0C, whose fault bits clear on read. Upstream does
this on each state update, and it doesn't affect charging. `charge-guard` and
`power-status` avoided it to preserve the fault evidence, so a fault read by hand
afterwards may already be cleared.

`power-status` still writes REG02 by design, one `CONV_START` per run when the ADC
isn't already converting, now through `I2C_SLAVE_FORCE`. This is acceptable: it's the
same on-demand write as before, only when someone runs the tool, it starts a
measurement and doesn't touch charging, and the driver writes only REG03, so the two
never modify the same register. The driver's write block doesn't cover it, because
that block only covers the driver's own writes.

## Where it can't protect

- **Charger unreachable on I2C:** the guard can't stop it. It logs at critical
  level and retries. The [60 °C critical trip](../2026-10-31-gemini-thermal-protection/README.md)
  remains the backstop. A power-off wouldn't stop the charge anyway, because the
  chip keeps charging with the system off.
- **Driver fails to probe after its retries:** no guard runs until a reboot, and the
  chip runs on its defaults, with the 60 °C trip behind it. The old daemon retried
  every 10 s for as long as it ran. The critical log line and `charge-guard=MISSING`
  report it. Nothing here depends on the gauge or the IIO channel at probe: the
  charger probes once its I2C adapter exists, and an absent gauge only keeps charging
  stopped.
- **Kernel hang, or power-off, or unbinding the driver, while stopped:** the watchdog
  restores charging within about 47 s even if the battery is hot, the same as a dead
  `charge-guard`. Turning the watchdog off would keep the stop,
  but it's a REG07 write and needs the owner's decision. It would also need a
  restore at shutdown.
- **System off or on the charging screen:** the bootloader decides, so there's no
  80 % limit there. This is unchanged.
- **Suspend:** the work doesn't run during suspend. The station has none today.
- **Root:** can still write the chip with `i2cset -f`, unbind the driver or set
  `emul_temp`.

## Tested so far

In the VM, on the station series, with no device:
- `drivers/power/supply/bq25890_charger.o` is clean at `W=1`.
- `dt_binding_check` passes for `bq25890.yaml`.
- The station DTB carries the charger node and the battery limits.
- 0517-0519 also apply on top of the C2b patches, as in the full `patches/series`.

On the device: see [G1 and G2](#g1-and-g2-boot-7197708f) and
[G3-G6](#g1-g6-boot-7197708f).

## Device plan (predeclared)

Needs a boot of an image with these patches, through the custodian. Exact hashes go
in the request.

**G1, first boot, read-only, cable in.** Check first, since it decides whether the
rest can run:
- `/sys/bus/i2c/drivers/bq25890-charger/0-006b` exists.
- `dmesg` has a `guard: charging` line.
- No `charge-guard` process.
- REG03 `CHG_CONFIG` clear at capacity over 80 %.

| Observation | Reading | Next |
| --- | --- | --- |
| Bound, `stopped ... full` logged, `CHG_CONFIG` clear | The guard runs from boot | G2 |
| Bound, `stopped ... hot` that doesn't clear | The battery's limits aren't reaching the guard | Stop; read `battery/temp_max` and `temp_alert_max` |
| Not bound | No guard. The chip charges on its defaults | Stop. Run `charge-guard` from the previous package with `I2C_SLAVE` free, or power off and restore |

**G2, the watchdog hold.** Stopped by the limit, sample REG03 and `status` every 20 s
for 3 minutes. `CHG_CONFIG` staying clear shows the kicks work.

**G3, negative control.** While stopped, unbind the driver. `CHG_CONFIG` should go
set within about 47 s, which shows the watchdog is live and that the driver was
holding it. Bind again; it should clear at the first pass.

**G4, the capacity limit.** On the live capacity C, in a boot whose capacity is over
the limit:
- `end_threshold` 100: resumes.
- C + 2, while stopped: stays stopped, the untested hysteresis case.
- C - 2 or lower: stops.
- 80: stays stopped.
- A value outside 50-100: `EINVAL`.

Capacity reads about 3 points lower with the charger on, so C is read just before
each step.

**G5, temperature by emulation.** A real 50 °C isn't reachable or wanted. With
`end_threshold` 100, write `emul_temp` on the battery zone:

| Written (m°C) | Expected |
| --- | --- |
| 52000 | stops, `hot` |
| 48000 | stays stopped |
| 46000 | resumes |
| −20000 | stops, the open NTC clamp |
| 0 | emulation off, real temperature, resumes |

Limits:
- Never write 60000 or more: that fires the critical trip and powers off.
- The kernel ignores emulation once the real temperature reaches 60 °C.
- Emulated temperature also moves `capacity`, through the OCV tables.
- Lifting the limit enables charging above 80 % for at most 3 minutes. This did the
  same on [station 13b](../2026-10-31-gemini-fuel-gauge/README.md), where the cell,
  above the chip's default 4.208 V regulation, discharged. `end_threshold` goes back
  to 80 at the end. Budget one run.

**G6, unreadable battery.** Unbind `mt6351-fuel-gauge`: stops within a pass, as `hot`.
Bind again: back to normal.

**Won't be shown on the device:** a real 50 °C battery, an ADC read failure, a charger
I2C failure, or the probe retry and the `MISSING` alarm firing.

## Results

### G1 and G2, boot `7197708f…`

Image `6bc70ab8…` from kernel package `b590193b`, SHA256SUMS `6a977869…`, run by the
custodian with `charger-g12.sh` `95164604…`, about 29 minutes after boot. The cable was
in throughout. The raw output stays private.

**G1:**
- `init` status `charge-guard=bound`; tainted 0.
- The driver bound with no deferral or retry logged. Model BQ25896, health Good.
- The guard's first pass ran at 0.89 s, before the gauge registered, and held charging
  off: `guard: charging stopped: temp=-2147483648 capacity=-1 limit=80 hot`.
- Battery limits read −20, 50, −18, 47. Thresholds read 75 and 80.
- REG07 `0x9d`: the chip's 40 s watchdog is still on. REG03 `0x0a`.

**G2:** 9 samples from 1731.78 s to 1892.19 s, 160 s, plus an end sample at 1925.25 s.
All read:
- REG03 `0x0a`, `CHG_CONFIG` clear;
- `status` Not charging, `online` 1;
- capacity 92, limit 80;
- battery 22.9 to 23.5 °C.

**Reading:** with no daemon in the image, the kernel keeps charging stopped across more
than four periods of the chip's 40 s watchdog. An
[earlier run](../2026-10-31-gemini-thermal-protection/README.md) saw the chip restore
charging about 47 s after the last kick, so this hold most likely comes from the driver's
kicks. That's an inference: G3, the control on this kernel, hasn't run.

**What this doesn't show:**
- **A stop at 80 or a resume at 75.** The battery stayed at 92 %.
- **Why charging is stopped.** The only guard log line is the first pass's `hot`. The
  log printed only when the stop itself changed, so the move from `hot` to `full` at
  23 °C left no line. A guard stuck on `hot` would look the same, and that's the G1 row
  this was meant to rule out. The temperature and limits do read correctly through the
  same properties the guard uses, which makes a stuck `hot` unlikely, but this isn't
  shown. G4 and G5 would show it. Since this run, 0519 logs every change of reason. The
  booted image doesn't have that.
- **That no `charge-guard` was running, from this script.** Its check used `pgrep`, which
  the station doesn't have, so the script printed `not running` without checking. The
  evidence for it is the custodian's check that the image has no `charge-guard` in `/bin`
  or `inittab`. `charger-g.sh` now reads process names instead.
- **Anything in G3-G6:** a temperature stop even by emulation, a capacity resume, the
  negative control or an unreadable battery.

**Register state:** REG06 read `0x82`, 4.352 V, the bootloader's setting, not the chip's
default 4.208 V. Because the first kick comes before the chip's watchdog first expires,
the bootloader's values stay for as long as charging stays stopped. A first resume
therefore runs at 4.352 V and 500 mA input for up to about 47 s, until the watchdog
returns the defaults. `charge-guard` started at about 2 s, so this probably isn't new, but
I didn't compare it. At a normal resume, at 75 %, the cell is well below both voltages.
It matters for testing: on `charger-g.sh`, G3 runs first and returns the defaults, so
later steps charge at 4.208 V.

### G1-G6, boot `7197708f…`

The owner approved charging above 80 % for G3-G6. The same boot and image as above, about
10.5 hours after boot, run by the custodian with `charger-g.sh` `bfccb244…`, cable in.
`lid-guard` had been swapped live, which doesn't touch the charger. Result `all passed`,
tainted 0, no oops and no `guard cannot reach` in `dmesg`. The raw output stays private.

| Step | What was done | REG03 and `status` | Result |
| --- | --- | --- | --- |
| G1 again | Read-only, with a real process check | `0x0a`, Not charging | no `charge-guard` process; limits and thresholds as before |
| G2 again | 9 samples over 160 s, capacity 91-92 | `0x0a` at all, Not charging | stop held |
| G3 | Driver unbound at 38005.6 s | `0x0a` to 38035.66 s, `0x1a` at 38045.67 s | watchdog restored `CHG_CONFIG` 30-40 s after the unbind |
| G3 | Driver bound again | `0x0a`, first pass logs `full` | stopped again |
| G4 | Limit 100, capacity 92 | `0x1a`, Full | resumes |
| G4 | Limit 50 | `0x0a`, Not charging | stops, `full` |
| G4 | Limit 94, in the hysteresis band | `0x0a`, Not charging | holds |
| G4 | Limit 97, at the resume point | `0x1a`, Full | resumes |
| G4 | Limit 50, then 49 and 101 | `0x0a`, Not charging | stops; both refused with `EINVAL` |
| G5 | Limit 100, emulated 52 °C | `0x0a`, Not charging | stops, `hot` |
| G5 | Emulated 48 °C | `0x0a`, Not charging | holds |
| G5 | Emulated 46 °C | `0x1a`, Full | resumes |
| G5 | Emulated −20 °C | `0x0a`, Not charging | stops, `hot`, the open NTC clamp |
| G5 | Emulation off, 23.7 °C | `0x1a`, Full | resumes |
| G6 | Limit 100, gauge unbound | `0x0a`, Not charging | stops, `temp=-2147483648 capacity=-1 hot` |
| G6 | Gauge bound again | `0x1a`, Full | resumes |
| Restore | Limit 80, no emulation, both drivers bound | `0x0a`, Not charging | stopped, `full`, still so at 38277 s |

**Reading:** with no daemon, the kernel stops and resumes charging on temperature and
capacity, with the hysteresis on both, and holds the stop past the chip's watchdog. G3 is
the control the earlier reading lacked: without the driver the stop ends, so the driver's
kicks were what held it.

**The stuck `hot` question from G1 and G2:** G6 gave the rebound driver the same input as
the first pass at boot, no battery supply, and `hot` cleared as soon as the gauge came
back. The driver instance from boot itself was unbound in G3 without having been shown to
clear it.

**Time enabled:** about 87 s across six windows in the guard's log, plus at most 10 s from
the watchdog in G3, against the 4 minutes budgeted. `status` read Full at every enabled
sample. The custodian read the cell at 4.261 V before and 4.263 V after, and capacity at
92 both times. The chip's defaults were back afterwards, REG06 `0x5e`, 4.208 V, against
`0x82` at G1, read only at those two points. The voltages and this second REG06 read come
from the custodian's report, not the retained files.

**Capacity moved with emulated temperature:** 91 at emulated 46-52 °C and 94 at −20 °C,
against 92 at 23.7 °C. The gauge takes capacity from the OCV table nearest the temperature,
so emulation changes the table used. This was expected in the plan, and it crossed no
threshold here. A real battery crossing a table's boundary would step the same way, by an
unmeasured amount near 80 %. It could move a stop or a resume by a point or two, inside the
5-point hysteresis, and capacity is the longevity limit, not the safety stop.

The plan expected capacity to read about 3 points lower with the charger on. It didn't,
which fits no current flowing here.

**What this doesn't show:**
- **That charge flows after a resume.** "Resumes" here means `CHG_CONFIG` set. The cell
  sits above the chip's 4.208 V regulation and the chip reported Full, so these windows
  probably put nothing in. Charge current wasn't measured.
- **A real charge reaching 80 %, or a real fall to 75 %.** Capacity stayed at 91-94, and
  the limit moved around it. The comparison is the same, but the path of a real charge
  hasn't run on this kernel.
- **Ending the bootloader's disabled state at boot.** This boot started above the limit. So
  the first resume at 4.352 V described above hasn't run either.
- **A real 50 °C.** The guard saw emulated values through the thermal zone. The real NTC
  path was read only at room temperature.
- **An unreadable capacity alone.** With the gauge gone both readings fail, and temperature
  decides.
- **The failure paths:** an ADC read failure, a charger I2C failure, the probe retry and the
  `MISSING` alarm firing.
- **The reason-change log line in 0519.** It's on main for the next image, compile-checked
  only. This image logged `hot` and `full` on each stop, but no line for a change of reason
  while stopped.
- **Suspend**, which the station doesn't have.

`CONFIG_THERMAL_EMULATION` stays in the station fragment, despite the earlier plan to drop
it after G5, while the GPU test depends on it. Any root process can already set
`emul_temp`, which feeds this guard.

## The battery reading flip: an overflow in the table lookup

**Found:** on boot `64622312…` the custodian saw `battery/temp` move between about 24.4 and
15.4 °C from one read to the next. The cause is an integer overflow in the kernel's table
lookup, not the ADC, the battery or the board. This is shown from the code and the retained
output. The fix isn't yet on a device.

**Withdrawn:** an earlier version of this section, at e13b4eb9 and 3a292d05, treated the low
value as a real conversion 246 codes away, and warned that a true 50 °C could read 35-42 °C
and that the 50 °C stop and 60 °C trip could be late. That was wrong, and so was calling
the first sample "no flip": `baton-s.sh` read only the raw channel, which never flips.

**The bug:** `thermal-generic-adc` interpolates with
`mult_frac(temp_lo - temp_hi, val - adc_hi, adc_lo - adc_hi)`, in 32 bits. This board's
table is in the IIO processed unit, 3600 × the code, so one 5000 mC step times a distance
above 429496 wraps. Reads differ because ADC noise crosses the edge of a wrapping range:

| Code | True temperature | Reads |
| --- | --- | --- |
| 936 | 25.042 °C | 25.042 °C |
| 937 | 24.999 °C | **15.802 °C** |
| 946 | 24.652 °C | **15.455 °C** |
| 947 | 24.614 °C | **15.416 °C** |
| 948 | 24.575 °C | 24.575 °C |

**Evidence:**
- The raw channel stayed at 936-956 through the flips, and `in_temp0_raw` doesn't go through
  this lookup. The zone and the gauge's `temp` both do.
- Running the driver's arithmetic over every code reproduces all 52 retained battery zone
  samples, from values it can produce. That includes the repeated 15.802 °C, which is code
  937, and the pairs 15.802 and 25.0 °C, which are codes either side of the 25 °C entry.
- The gap is 2³² divided by the entry's width: 9.20 °C here, and 8.40 °C on boot `04cc38ee…`,
  11.45 against about 20 °C.
- It explains why `7197708f…` looked steady: at 23.6-24.2 °C it was below the range.
- It predates this guard: `charge-guard` used its own conversion, but the zone, the gauge and
  the status lines had the bug from the start.

**Every affected range:**

| True temperature | Reads | Error |
| --- | --- | --- |
| 24.61 to 25.00 °C | 15.42 to 15.80 °C | 9.20 °C |
| 19.21 to 19.99 °C | 10.82 to 11.59 °C | 8.40 °C |
| 13.92 to 14.99 °C | 6.14 to 7.21 °C | 7.78 °C |
| 8.68 to 9.97 °C | 1.33 to 2.62 °C | 7.35 °C |
| 3.56 to 4.98 °C | −3.52 to −2.09 °C | 7.07 °C |
| −1.51 to 0 °C | −8.44 to −6.93 °C | 6.93 °C |
| −6.49 to −5.03 °C | −13.46 to −12.00 °C | 6.97 °C |
| −11.36 to −10.03 °C | −18.59 to −17.26 °C | 7.23 °C |
| −16.15 to −15.03 °C | −23.81 to −22.69 °C | 7.66 °C |

**What it does to the protection:**
- **Hot side, none.** From 25 °C up every table entry is narrower than 429496, so no code
  wraps. The 50/47 °C window and the 60 °C trip convert correctly.
- **Cold side:** at −16.15 to −15.03 °C the guard would stop charging, as the reading is
  under −20 °C. That's the safe direction. The −11 °C range can read below the −18 °C resume
  point, which only holds an existing stop.
- **Capacity:** a low reading can select another OCV table, as at 19.21-19.99 °C, where it
  picks the 0 °C table. That can move the capacity limit a little. It isn't a safety stop.

**The fix:** [0526](../../patches/proposals/0526-thermal-generic-adc-do-not-overflow-the-table-interp.patch)
uses a 64-bit product. Compiled at `W=1` in the VM; the arithmetic was checked offline over
all 4096 codes, where only the codes above differ. It could go upstream.

**Confirmed on boot `fcb98505…`,** image `3e429f70…` from package `b024a5df` at `d5daaff4`, at
31-50 s, cable in, radios down. The custodian took 20 lines of raw, gauge and zone reads:
- Raw 931-942, zone 24.806-25.255 °C, gauge 24.8-25.2 °C, with nothing near 15-16 °C.
- 10 of the 20 zone readings were 24.806-24.999 °C. The old lookup could never give a value
  from 24.615 to 24.999 °C, because those codes wrapped to about 15.4-15.8 °C. So this is
  the fixed lookup working inside the affected range, not the battery avoiding it. Raw
  937-942 is also inside the wrapping codes, 937-947.

Only this range ran on the device. The other eight are from the offline check.

**Also on that boot:**
- `guard: charging stopped: temp=251 capacity=95 limit=80 full` at 10.98 s, after the first
  pass's `hot` at 0.89 s, with charging stopped throughout. So 0519's log of a change of
  reason works, and this time the original boot bind cleared `hot`, the case G6 couldn't
  show.
- Capacity read 95, up from 92 before a 14-minute power-off with the cable in. This is the
  known gap [above](#where-it-cant-protect): with the system off nothing enforces the limit.
  Charge current wasn't measured.

G1-G6 still stand, and their temperatures were true readings or emulation.

## Review before the first full image (2026-11-03)

An independent reader went through 0517-0520 and 0526, with `checkpatch` and the schema
checks, and booted nothing. They found no memory-safety bug, race or arithmetic bug. I
checked each finding against the code.

**Fixed in 0517 and 0519:**
- **F3:** one failed capacity read lifted a capacity stop, and a lasting failure charged past
  the limit with nothing logged. The last answer now stands, and the first failure warns once.
  If the capacity has never been read since boot, charging isn't stopped by it, with the same
  warning.
- **F9:** the first pass could start from "not hot", so a boot inside 47-50 °C charged up to
  50 °C, depending on probe order. It now starts from `hot`.
- **F10:** a gauge that never came gave no charging and one info line. Now there's one critical
  line per episode, after three passes. The reader suggested a ratelimited line, but that
  would fire at every normal boot, when the gauge registers after the first pass, and then
  every 10 s.
- **F6:** a guard property without `linux,no-chip-config` validated, and the driver would have
  reset the chip and turned its watchdog off with no guard. Now the binding has dependencies,
  and the probe fails. Not binding leaves the chip on its defaults, untouched.

Compiled at `W=1`. The binding check passes, and a test example breaking the dependency fails
it. `git am` of 0517-0520 and 0526 on the station series gives the same tree. The patches
touching these two files apply in order in both series. **None of this has run on a device.**
One visible change at boot: with the gauge absent the first pass no longer logs
`stopped ... hot`, because the reason hasn't changed. The next `guard:` line comes about 10 s
later.

**Blockers before upstream, not changed now:**
- **F1:** suspend fails open. Not live here, as `CONFIG_SUSPEND` is unset, but the guard needs
  an answer before the station gets suspend.
- **F2:** unbinding fails open, as G3 measured. The commit message says so.
  `suppress_bind_attrs` would close the casual route, but the tests use unbind.
- **F4:** `TEMP_MAX` and the alert limits come through in whole degrees, against the ABI's
  tenths. Giving the charger a `monitored-battery` would fix it.
- **F7:** the device tree interface encodes policy (`linux,guard-*`, `linux,no-chip-config`).
  This is the main upstream blocker.
- **F8:** 0520 needs `i2c0` enabled in the source. Today `station-dt.sh` does that.
- **F12:** the patches have no `Signed-off-by`, and none can be added for the owner.

**F5, for the owner:** there's no cold charging stop between −20 and 0 °C, matching the vendor.
The custodian is raising it.
