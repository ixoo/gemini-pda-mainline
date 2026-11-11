# Experiment: the charging guard moves into the kernel

| Field | Value |
| --- | --- |
| ID | `2026-11-02-gemini-kernel-charge-guard` |
| Status | `completed`: G1-G6 and the cold stop's emulation run passed, the overflow fix is confirmed, and charger-type detection and the wall-charger currents ran on the device; a really hot or cold battery was not tested |
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
| Battery at 0 °C or below | no stop | **stop: the owner's cold stop**, from `operating-range-celsius` |
| Above 3 °C | not applicable | resume, from `alert-celsius` |
| Open NTC, or a battery below −20 °C | open NTC: unreadable from the raw code, stop; cold battery: no stop | reads the table's −20 °C clamp, so stopped |
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

The first pass starts as stopped by temperature, so a battery already inside 47-50 °C stays stopped
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

**First boot with the fixes,** `fccba04c…`, image `96338704…`, as reported by the custodian:
- No `stopped ... hot` line at 0.89 s, and no `battery supply missing` line.
- First line at 10.98 s: `guard: charging stopped: temp=231 capacity=93 limit=80 full`.
- Not charging, 93 %, 23 °C, tainted 0.

This shows the normal boot path only. The failed capacity read, a missing gauge's critical
line, the 47-50 °C boot and the refused probe haven't run on a device.

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

**F5, for the owner:** there was no cold charging stop between −20 and 0 °C, matching the vendor.
The owner chose to add it; see [the cold stop](#the-cold-stop).

## The cold stop

The owner's decision: add the stop for −20 to 0 °C. It's a change of the battery's limits in
0520, to `operating-range-celsius = <0 50>` and `alert-celsius = <3 47>`. The driver needs no
change, because the guard already reads its limits from the battery. Rows above in
**What it does to the protection** that mention the −20 and −18 °C limits describe the old values.

| Reading | Result |
| --- | --- |
| 0.0 °C or below, which is under 0.1 °C after the gauge truncates to tenths | stops, logged as `temperature` |
| 0.1 to 3.0 °C | the last answer stands |
| 3.1 °C or above | resumes, unless another stop applies |
| Below −20 °C, or an open NTC | reads the −20 °C clamp, so stopped |
| Read failure, or no battery supply | stopped, with a critical line after three passes |
| 47 °C up to 50 °C, and 50 °C or above | unchanged |

A boot at 0.1-3.0 °C stays stopped until 3.1 °C, since the first pass starts as stopped by
temperature. The log reason is now `temperature` for either end of the range, in place of `hot`,
so a cold stop doesn't read as hot; the `temp=` value tells them apart. The log lines quoted
earlier in this record came from older images and stay as they were.

**The table's cold end, checked offline:** with 0526's arithmetic over all 4096 codes, from the
table in 0361:
- Readings fall steadily as the code rises, with no step over 94 m°C.
- Code 1693 and up is at or below 0 °C, code 1591 and down is above 3 °C, and code 2357 and up is
  the −20 °C clamp.
- The open NTC, about code 3185 at 2.8 V, reads −20 °C.
- The hot end hasn't moved: 50 °C at code 470, 47 °C at code 513.

The stop depends on 0526. Without it, a true 3.56-4.98 °C would read −3.52 to −2.09 °C and stop
falsely, and a true −1.51 to 0 °C would read lower still. Both are in the same series.

**Compiled and checked in the VM:** the station DTB carries `0 50` and `3 47`, the DTB's schema
check reports nothing for the battery or the charger, and `W=1` is clean. **Nothing has booted.**

**What can't be shown without a cold battery:** that the real NTC and the vendor's table agree
near 0 °C. The table has only run at about 20-30 °C on this device, and the table comes from the
vendor's source, not a measurement. Emulation would show the guard's decisions but not that.

**Device check, on an image with `THERMAL_EMULATION`,** with the limit left at 80 so nothing
enables charging, only the reason log changes:

| Written to `emul_temp` | Expected |
| --- | --- |
| −1000 | `stopped`, `temperature full` |
| 2000 | holds, no new line |
| 4000 | `stopped`, `full` |
| 0 | emulation off |

0 can't be written as a temperature, as it turns emulation off. The release fragment turns
`THERMAL_EMULATION` off, so this needs a station image.

**Result, boot `c08abf6b…`,** image `2d6a20a5…` from package `447fb237` at `d493fbad`, as reported
by the custodian. The live device tree carried `0 50` and `3 47`. The first guard line came at
10.98 s: `charging stopped: temp=243 capacity=94 limit=80 full`. Each step on `battery-thermal`
lasted 45 s:

| Written | Battery `temp` | Log |
| --- | --- | --- |
| −1000 | −10 | `charging stopped: temp=-10 capacity=95 limit=80 temperature full`, at 41.70 s |
| 2000 | 20 | no new line |
| 4000 | 40 | `charging stopped: temp=40 capacity=95 limit=80 full`, at 133.86 s |
| 0 | 238 (zone 23766) | no new line |

Tainted 0.

**Reading:** with emulated temperatures, the guard stops below 0 °C, holds at 2 °C and clears the
cold reason by 4 °C, and the new neutral log reason works.

**What this doesn't show:**
- **A cold battery.** The real NTC near 0 °C and the table there are still unmeasured.
- **The exact edges.** 0.0 and 3.1 °C weren't tried; the steps were −1, 2 and 4 °C.
- **Charging stopping or resuming on this stop.** Capacity stayed above the limit, so `full` kept
  charging off throughout, and only the reason changed.
- **Why capacity read 95.** It read 94 before the power-off and at 10.98 s, and 95 by 41.7 s. That
  was after a powered-off period on the cable, and during emulation, which selects another OCV
  table. These can't be separated here.

## The limit from the desktop's battery widget (2026-11-11)

The owner asked whether the charging limit could be chosen from the Noctalia battery widget, and
then asked for it.

**Where it stood,** from the custodian's read-only check on boot `58bcf387…`:
- The charger, `bq25890-charger-0`, has `charge_control_start_threshold` 75 and
  `charge_control_end_threshold` 80. The `battery` supply, from the fuel gauge, has neither.
- UPower 1.91.5 runs, and reports `ChargeThresholdSupported=false` for the battery.
- Noctalia 5.4.1 already offers the control, through UPower's `EnableChargeThreshold`, on a
  device that reports support. So Noctalia needs no change.

**What UPower 1.91.5 does,** from its source:
- **Support:** decided only by a udev property on the battery device, `CHARGE_LIMIT`, written as
  start and end, such as `75,80`. Without it the battery is never offered. If the battery has the
  two attributes, their live values replace those in `CHARGE_LIMIT` when they're between 0 and 100,
  exclusive. UPower reads all this once, when it first sees the battery.
- **Enable:** writes start, then end, using the values read at that first look.
- **Disable:** writes start 0, then end 100.
- A write fails only if both files fail.
- **Persistence:** UPower keeps the choice in `charging-threshold-status` in its state directory.
  When it starts, it writes the thresholds again only if that says enabled. With no file, or one
  that says disabled, it writes nothing and reports the limit as off.
- **Permission:** polkit action `org.freedesktop.UPower.enable-charging-limit`, allowed for an active
  local session and refused for an inactive one.

**The kernel side,**
[0695](../../patches/proposals/0695-power-supply-bq25890-offer-the-guard-s-thresholds-on-.patch):
- While the guard runs, it adds the two thresholds to the `battery` supply as a power supply
  extension. They're backed by the charger's own values, so both places always agree.
- The start becomes writable, from 0 to below the end. Writing an end still sets the start 5
  points below it, as before, so a different start has to be written after the end. UPower writes
  the end last, so through UPower the start is always 5 points below the end. With
  `CHARGE_LIMIT` `75,80` that's what it asks for anyway.
- The boot default stays 80 and 75, from the device tree, and the guard's decisions don't change.
- Disabling through UPower gives end 100, which turns the limit off, and start 95.
- The attributes appear when the guard first finds the battery. A notifier runs that pass as soon
  as the battery registers, about 1 s into boot rather than 11 s.
- **Gauge unbound and bound again:** the new battery gets the extension again. The old one keeps a
  small record of it, because unregistering from a battery that's going would queue work on it.
- **Not handled:** the charger and the gauge unbinding at the same moment. Only root can do that, as
  in tests.

Compiled at `W=1` on top of the later 0601 and 0630, with `checkpatch --strict` clean. It applies in
both series, and the station series then gives the file that was compiled. **Nothing has booted.**
It's built into the driver, so it needs an image, not a module.

**Needed in the root filesystem,** for the session that packages it:
- A udev rule on the battery, `SUBSYSTEM=="power_supply", KERNEL=="battery",
  ENV{CHARGE_LIMIT}="75,80"`. Without it UPower never offers the control.
- UPower's `charging-threshold-status` set to `1` on a new install, so the widget starts by showing
  the limit that the kernel applies at boot.
- **One mismatch remains:** after the user turns the limit off, the next boot starts at 80 again in
  the kernel, while UPower still says off. A boot step before UPower that writes 100 to the
  battery's end when the file says `0` would keep the two in step. The alternative, a kernel that
  boots with the limit off, would leave the station and any boot without UPower charging past 80,
  against the owner's policy.
- **Polkit:** no rule is needed if Noctalia's session is active in logind; `loginctl show-session`
  should report `Active=yes`. Otherwise a rule for that user and action is needed.

**Device plan,** read-only apart from the threshold writes, and never lifting the limit above the
live capacity, so nothing enables charging:

| Step | Expected |
| --- | --- |
| Read `battery/charge_control_{start,end}_threshold` and `battery/extensions` | 75, 80, a `bq25890-guard` link |
| On the battery: end to a value at or below capacity, then start 5 lower than that | The charger's attributes show the same values; `full` holds |
| Start at or above the end | `EINVAL` |
| With the udev rule, restart UPower | `ChargeThresholdSupported=true`, start 75, end 80 |
| `EnableChargeThreshold(true)` | 75 and 80 written; no change |
| Restore end 80 | 75 and 80 |

`EnableChargeThreshold(false)` writes end 100, which lets the device charge above 80 %. It needs
the owner's go-ahead before it's tried.

### First reports from the widget, boot `242ba06e…` (2026-11-11)

From the custodian, on the owner's card, gemini-base 37 with 0695.

**The switch works.** Turned off from Noctalia, both supplies read start 95 and end 100, and the
guard logged `charging allowed: temp=255 capacity=71 limit=100`. The charger read online,
`Charging`, `Fast`, with a 500 mA input limit on the computer's USB port. The battery's current
read −363, then 0. So 500 mA in covered little more than the lit screen, and the owner saw
nothing happen.

**Input limit on a wall charger:** earlier boots read REG00 `0x48`, 500 mA, with both the
computer and the owner's fast charger classified as a computer port
([charging notes](../../docs/hardware/gemini-charging.md#2-boot-chain)). A wall charger would
probably be held at 500 mA too. Raising it means the driver writing REG00, a charger write
beyond `CHG_CONFIG` that needs the owner's decision, plus a way to know the charger can supply
more. The candidates are the MT6351's own charger detection and the Type-C port. A read-only
check on a wall charger would read REG00 (limit), REG0B (`VBUS_STAT`, bits 7:5) and REG13 (the
limit in force).

**"Plugged in" while unplugged:** the charger read offline and `Discharging`, but the battery read
`Not charging`, and UPower showed `pending-charge`, which Noctalia shows as plugged in. The
battery's `current_now` read −1091, about 1 mA, while it was running on the battery with the
screen lit. The gauge reported anything within 20 mA as not charging, from the current alone.
That logic is the gauge's, not the guard's or 0695's.
[0708](../../patches/proposals/0708-power-supply-mt6351-fuel-gauge-report-discharging-wi.patch)
reports discharging within that band unless some supply is online. A battery held at the limit
on the charger still reads not charging. Compiled at `W=1`, `checkpatch --strict` clean, and
applies in both series. Not on a device.

**Open, the current reading and the jump from 79 % to 60 % on unplugging:** earlier records show
this gauge's `current_now` at 93-300 mA when the station ran, but also stuck at 0, and
disagreeing with `charge_counter` after some steps ([cpuidle](../2026-11-07-mt6797-cpuidle/README.md)).
A reading near zero under load would explain the jump. Capacity is the voltage corrected by I × R,
so with I read as about 0, the loaded voltage under a few hundred mA reads several percent low.
This is an inference. A read-only sample unplugged would separate a stuck current register from
a stopped counter: `current_now`, `voltage_now`, `charge_counter` and `capacity` every 10 s for a
minute, the suspend count, and `FGADC_CON0`.

**Follow-up, same boot:** 15 one-second samples of `current_now` read 0, ±363, −727 and −1091
only, with +363 appearing while discharging. A 30 s average read −363.
- **The steps are the gauge's normal resolution.** One count is 158.122 µA, scaled by
  20/10 mΩ for the sense resistor and by 1.15 for `car-tune` 115: 363.68 µA. `current_now` is
  in µA, so −1091 is about 1.1 mA, not 1.1 A.
- **What's wrong is that the register stays within three counts of zero** while the device runs
  unplugged with a lit screen and Wi-Fi. Earlier station boots read 93-300 mA from the same
  register, so this is a state on this boot, not the scale or a calibration. A `car-tune`
  calibration would change readings by a percentage, not take them from hundreds of mA to zero.
- **Capacity doesn't count charge.** It's the OCV table at the voltage less I × R. With I read as
  about 0, it reads the loaded voltage, which fits 79 % falling to 60 % on unplugging.
  `charge_counter` isn't used for capacity.
- **Effect on the guard:** it uses this capacity. While charging, the uncorrected voltage is
  raised by the charging current, so capacity reads high and charging stops before a true 80 %,
  the safe side. When the voltage relaxes after the stop, capacity can fall back inside the
  5-point band and charging resumes, so short stop-and-resume cycles near the limit are possible.
  This is an inference, not observed.

## A wall charger stays at 500 mA (2026-11-12)

The owner asked for faster charging on a wall charger. On card-32, boot `0bad0df9…`, with a QC
wall charger, the custodian read:
- REG00 `0x48`: 500 mA input limit.
- REG02 `0x11`: the chip's own detection on; `HVDCP_EN` and `MAXC_EN` off.
- REG0B `0x36`: `VBUS_STAT` SDP, charging fast, power good.
- REG13 `0x48`: the input limit in force, 500 mA.
- The battery took about 0.1 A.

**Why:** the vendor detects the charger type on the MT6351, switching the USB D+/D- to the
PMIC's BC1.1 block, and writes the input limit from the result. It turns the BQ25896's own
detection off ([F6-F7](../2026-10-04-gemini-charging-re/README.md)). Mainline leaves the chip's
detection at its defaults, and it reports SDP for a computer and for this wall charger alike.

**Proposed, not run:** one forced detection (`FORCE_DPDM`) on the wall charger with no host, to
learn whether the chip can see the lines at all. The driver change follows from that:
- **If it reads DCP:** force a detection after a plug.
- **If not:** classify on the PMIC, or use a rule that a supply no USB host configures within a few
  seconds is a wall charger.

Either way the proposal caps the result at 1.5 A input and 1.024 A charge, falls back to
500 mA from 45 °C, and keeps QC's high voltage off: the bootloader rejects VBUS above 6.5 V.
These are charger writes beyond `CHG_CONFIG`, so they wait for the owner.

**T1, boot `a71d4762…`, with the owner's approval:** the custodian ran `dpdm-t1.sh` `53e81d61…` on
card-32, with only the QC charger attached.
- It wrote `FORCE_DPDM` once. The chip had cleared the bit by the first read, 60 ms later.
- REG0B stayed SDP and REG00 stayed 500 mA across 15 reads over 3.5 s, so no restore was
  needed. Tainted 0.

So the chip can't classify a charger through these lines. It's not proven that detection
actually ran, but the bit clearing itself suggests it did.

Another reading rules out the simpler fallback: after the Mac was unplugged, the USB gadget still
reported `configured`. A rule of "no USB host configures the gadget within a few seconds" would
therefore misread a wall charger plugged in after a computer.

**Proposed next:** classify on the MT6351, as the vendor does, in a new module.
- **Detection:** the PMIC's BC1.1 steps in `CHR_CON20`, wrapped in the USB PHY switch that hands
  D+/D- to the PMIC. It runs on a plug, signalled through the battery supply's change from the
  charger-detect interrupt.
- **Result:** reported as a power supply with a USB type.
- **First device test:** loading the module and reading the result, with the Mac and with the wall
  charger, with no charger write at all.
- **Then:** the guard sets the capped input limit and charge current from that type, a separate
  step with its own approval.

**Implemented, with the owner's approval of the change and the caps:**
- [0717](../../patches/proposals/0717-power-supply-add-MT6351-BC1.1-USB-charger-type-detec.patch):
  a module that runs the vendor's BC1.1 steps at each plug and reports `mt6351-usb`'s `usb_type`.
- [0718](../../patches/proposals/0718-power-supply-bq25890-raise-the-currents-on-a-dedicat.patch):
  the guard sets 1.5 A input and 1.024 A charge on a dedicated or Apple charger, as the owner
  approved, rewriting both each pass with the watchdog fed. It returns to 500 mA from 45 °C on the
  battery until it's under 43 °C, or when the charger goes. A host, a charging host and a
  non-standard charger keep 500 mA. The module reports a non-standard charger as `Unknown` while
  online, and retries a failed detection rather than report it.
  **Decided by the owner:** "1.5A is great for all the chargers we know can support it. 500mA
  otherwise". So non-standard chargers stay at 500 mA, as 4aef2e99 has it. d037922f had briefly
  given them the caps without approval. A 1.5 A or 3 A Rp advertisement from the FUSB301 would be a
  charger known to support it, which is future work that needs the FUSB301's board nodes.
- [0719](../../patches/proposals/0719-dt-bindings-power-supply-bq25890-name-a-USB-type-sup.patch) and
  [0720](../../patches/proposals/0720-arm64-dts-mediatek-gemini-station-raise-the-charge-c.patch):
  name the supply to the guard with `linux,guard-usb-detect`.

All four are clean at `W=1`, and the binding and station DTB pass their schema checks. They apply
in both series, and the station series gives the exact driver files compiled. Nothing has
booted.

**Known effects and limits:**
- Feeding the watchdog on a wall charger keeps whatever charge voltage the bootloader left, at
  most the battery's design 4.352 V. Each limit still stops charging first.
- The module finds the PMIC and the PHY port from the device tree and creates its own device,
  because the PMIC's MFD has no cell for this block yet. That's a blocker before upstream.

D1 tests the module alone on the running card; D2 tests the guard on the next image.

**D1 and D2, boot `b8fb3cbf…`,** station-work-103, boot2 `14c0112b…`, built from main at 4aef2e99.
Run by the custodian with `usbtype-d1.sh` `ada8e11c…` and `mt6351-usb-type.ko` `8ee622fb…` from that
package. Tainted 0.

**D1, detection:**

| Step | Result |
| --- | --- |
| Load with the Mac attached and enumerated | `CDP (charging host)`; USB SSH stayed up |
| QC charger plugged | `DCP (dedicated charger)` |
| Unplug, Mac plugged | `CDP`; REG00 `0x48`, REG04 `0x20`; USB SSH up |
| `rmmod` | the supply goes; `0fa0` keeps `BB_CTRL` and `RST` set, as the vendor leaves them |
| Loaded again with the Mac still attached and enumerated | **`SDP`**, against `CDP` at both plugs |

So detection gives a different answer while a host session is already running than at a plug.
Today it changes nothing, since SDP and CDP both keep 500 mA. If CDP were ever given the higher
currents, a module load or a boot with a computer already attached would under-classify it, which
errs on the safe side.

**D2, the guard on the QC charger:**
- 1.6 s after detection: `guard: dedicated charger: input 1500 mA, charge 1024 mA`, with REG00
  `0x5c`, REG04 `0x10`, and REG13 `0x1c`, a 1.5 A input limit in force.
- The battery took 495 mA at 67 %, against about 0.1 A before. Over 10 minutes, sampled every
  30 s:
  - current fell from 483 to 376 mA, at a constant 4.207 V;
  - capacity went from 67 to 69 %;
  - battery 25.9-26.5 °C, SoC 33.9-34.4 °C;
  - REG00 and the DCP type held.
- Unplugging brought `guard: input back to 500 mA`.

**Reading:** the wall charger now charges about five times faster, with no heating seen in
10 minutes. The cell sat at the chip's default 4.208 V charge voltage throughout, so this was the
constant-voltage phase, and the current followed the cell, not the 1.024 A cap. The cap and the
45 °C fallback haven't been reached on the device. A 4.2 V cell at 67-69 % also says the reported
capacity may be low; that belongs to the fuel gauge.

**The owner adds charging hosts, 2026-11-12:** asked whether the MacBook's CDP ports should get
1.5 A too, with both caveats stated, the owner answered "Yes, add CDP". The custodian relayed it.

0718 now gives CDP the same caps and the same 45 °C fallback as a DCP; a CDP port is rated for
1.5 A. The log line reads `guard: 1.5 A charger: input 1500 mA, charge 1024 mA`. A plain host
and a non-standard charger keep 500 mA. A computer already attached at boot or at a module load
reads SDP, as D1 showed, so it gets 1.5 A only from its next plug. Some hubs and docks report
CDP too. Compiled at `W=1` and clean under `checkpatch --strict`; it needs an image, and isn't on
a device yet.

## Charge voltage by temperature (2026-11-12)

The fuel-gauge session found that the vendor charges this cell to 4.34 V between 10 and 45 °C,
4.24 V at 0-10 and 45-60 °C, and 4.04 V below 0 °C. Mainline left whichever voltage was in place:
the bootloader's 4.352 V until the chip's watchdog first expired, then the chip's 4.208 V. At
4.208 V a full charge reads about 87 % on the vendor's OCV table.

**The owner chose B, Gemian's 4.34 V**, from: always 4.208 V; the vendor's voltages by
temperature; or leave it.

- [0722](../../patches/proposals/0722-power-supply-bq25890-set-the-charge-voltage-by-the-b.patch):
  with `linux,guard-charge-voltage-by-temperature`, the guard writes REG06 `VREG` each pass when it
  differs: 4.34 V (4.336 V in the chip's steps) from 10 °C to under 45 °C, and 4.24 V outside,
  with 2 °C of hysteresis back in. It feeds the watchdog every pass while this is on.
- Below 0 °C charging is already stopped by the cold stop, so 4.04 V isn't needed. REG06 joins
  the guard's writes.
- [0723](../../patches/proposals/0723-dt-bindings-power-supply-bq25890-describe-the-guard-.patch) and
  [0724](../../patches/proposals/0724-arm64-dts-mediatek-gemini-station-charge-voltage-by-.patch): the binding and the station property.

Tested: `W=1` and `checkpatch --strict` clean. The binding, as the series builds it, passes its
schema check, and the station DTB carries the property. Everything applies in both series and gives
the compiled driver file. Nothing has booted.

**Side effect:** feeding the watchdog every pass keeps every other register as the bootloader left
it while the guard runs, including its IR compensation and clamp in REG08. If the guard stops, the
watchdog returns the chip's defaults, including 4.208 V.
