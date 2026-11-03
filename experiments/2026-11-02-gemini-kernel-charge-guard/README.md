# Experiment: the charging guard moves into the kernel

| Field | Value |
| --- | --- |
| ID | `2026-11-02-gemini-kernel-charge-guard` |
| Status | `planned`: patches compile-checked; not booted, nothing below is shown on the device |
| Subsystem | BQ25896 charger, MT6351 fuel gauge and battery NTC |
| Device variant | named Gemini PDA (MT6797X), development station |
| Date(s) | 2026-11-02 |
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
- Fragment: `CHARGER_BQ25890=y`, and `THERMAL_EMULATION=y` for the test only.
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
