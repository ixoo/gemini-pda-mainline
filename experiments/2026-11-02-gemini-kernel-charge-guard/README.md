# Experiment: the charging guard moves into the kernel

| Field | Value |
| --- | --- |
| ID | `2026-11-02-gemini-kernel-charge-guard` |
| Status | `running`: G1-G6 passed on the device, but the battery temperature the guard reads can flip about 9 °C low; cause open |
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
| Temperature unreadable, or no battery supply | stop | stop |
| Open NTC | reads unreadable from the raw code, stop | reads the table's −20 °C clamp, stop at −20 °C or below; resume above −18 °C |
| Real battery at −20 °C or below | no stop | **stop: a new, stricter case** |
| Capacity at the limit, default 80 | stop | stop |
| 5 points below the limit | resume | resume |
| Limit 100 | off | off |
| Capacity unreadable | no stop | no stop |
| Set the limit | `/run/station/charge-limit` | `charge_control_end_threshold`, 50-100 |
| Stopped | `WD_RST` every 10 s | `WD_RST` every 10 s |
| Bootloader left it disabled, charging allowed | set at first pass | set at the first pass with a readable battery |

The first pass runs at probe. The gauge may not have registered yet, in which case
charging stays held off until the next pass, 10 s later. Before, `charge-guard`'s
first pass came at about 2 s.

`charge_control_start_threshold` reads the limit minus 5 and is read-only.

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

## Open: the battery reading flips

Found by the custodian on boot `64622312…`, during a Bluetooth soak: `battery/temp` moved
between about 24.4 and 15.4 °C over samples 13 s apart, with the SoC at 27.8 to 29.6 °C.
No device step has run for this yet.

**Observed in retained output from earlier boots:**

| Boot | Readings |
| --- | --- |
| `4ac95e75…`, 2026-11-01 | 15 of 20 zone and gauge pairs low, 15.4-15.8 °C; 4 pairs with the zone at 15.8 and the gauge at 25.0-25.1 °C |
| `7dd24578…` | at `init`, the zone 15.8 °C and the gauge 25.1 °C; 25.4 °C at 47 s |
| `04cc38ee…` | at `init`, 11.5 °C; 20.1 °C later in the same start-up, SoC 21.4 °C |
| `64622312…` | as above |

So it isn't specific to one boot, and it predates this guard and Bluetooth: the first two
boots ran the `charge-guard` daemon. The pairs are read a few milliseconds apart, so the
battery can't have changed temperature between them.

`7197708f…` looked steady, but that is weak evidence. `charger-g.sh` reads `capacity`
just before `temp`, and `capacity` itself makes a pack voltage and a battery conversion.
All its samples follow other conversions. The low pairs show the first read of a pair is
sometimes the low one, though not always.

**Inference:**
- The high value is the true one. It agrees with the SoC and the earlier boots.
- The low value is about 246 ADC codes higher on the NTC divider, about 216 mV at the node.
  It stays about the same size at the one other temperature seen, which is two samples.
- Bit errors don't fit, as the gap isn't a power of two and varies by a few codes.

**What it would do to the protection,** if the same offset held when hot, which isn't
measured:

| True temperature | Reads, as a fixed voltage offset | Reads, as a fixed injected current |
| --- | --- | --- |
| 47 °C | 33 °C | 39 °C |
| 50 °C | 35 °C | 42 °C |
| 60 °C | 41 °C | 52 °C |

The gap is larger than the 9 °C seen at room temperature, because the NTC's curve flattens
when hot. Then:
- **The guard:** a true reading at 50 °C stops charging, and the next low reading, under
  47 °C, resumes it. A run of low readings stops it late. This is the unsafe direction.
- **The 60 °C trip:** it fires only on a reading that isn't low, so a run of low readings
  delays it.
- **No false stop:** low readings stay far above −20 °C at room temperature.
- **Capacity:** a reading below 12.5 °C selects the 0 °C OCV table, which moves it a little.

**Not known:** the cause, and whether it happens with the battery hot. One lead: the
driver waits 80 µs before it checks the ready bit, while the vendor polls at 1.3 ms, so a
ready bit left from the last conversion could return an old result. That alone wouldn't
explain where a low value first comes from. Other candidates are a pad or VBIF28 state,
and another ADC requester. The next step is a read-only sample: back-to-back reads, first
read after idle, after a voltage conversion, the result register alone, and the control
registers in both states.

G1-G6 still stand as tests of the guard's decisions, since their temperatures were true
readings or emulation. This is about the input.
