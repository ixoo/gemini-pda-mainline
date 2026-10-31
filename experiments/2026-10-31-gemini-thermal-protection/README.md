# Experiment: what thermal protection the station needs

| Field | Value |
| --- | --- |
| ID | `2026-10-31-gemini-thermal-protection` |
| Status | `running`: steps 1-3 work on the device and run from boot |
| Subsystem | SoC thermal controller, TOPRGU, BQ25896, MT6351 |
| Device variant | named Gemini PDA (MT6797X), development station |
| Date(s) | 2026-10-31 |
| Investigator(s) | project custodian |
| Tracking issue | none |

## Question

The [development station](../2026-10-30-mainline-dev-station/README.md) runs
for hours with Wi-Fi on and the charger on its own defaults. It has no
thermal driver.

**Question:** what does Gemian protect against, and what is the minimum
mainline needs?

## Vendor policy

The durable source and firmware facts are in
[MT6797 thermal management](../../docs/hardware/mt6797-thermal-management.md):
sensors, calibration, conversion, thresholds, firmware roles and the Android
userspace policy. What matters for the station:
- **Gemian's effective protection** (no Android thermal manager runs) is the
  kernel default set:
  - the 117 °C hardware reset through TEMPPROTTC and TOPRGU;
  - the CPU zone's 95/85 °C clamps;
  - the device tree's 50/47 °C charging window.
- **Mainline has none of the three:**
  - the station's thermal node is disabled;
  - upstream `mtk_wdt` never sets the thermal request;
  - nothing programs TEMPPROTTC;
  - no charger driver runs.

## Device reads on station 9 (boot `960b9505…`)

Taken during the Wi-Fi hold, without touching Wi-Fi.

**TOPRGU:** not read. This kernel has no `/dev/mem` (`CONFIG_DEVMEM` is
off), and `mtk_wdt` owns `0x10007000-0x100070ff`. Whether the bootloader
arms the thermal reset stays unknown; a read needs a small module.

**BQ25896** (I2C0, `0x6b`): plain SMBus byte reads with busybox `i2cget`.
REG14 read `0x06` first (the BQ25896), and REG0C, whose fault bits clear on
read, was not read.

| Register | Value | Decoded (datasheet) |
|---|---|---|
| REG00 | `0x48` | input limit 500 mA, ILIM pin on |
| REG03 | `0x1a` | charging enabled, SYS_MIN 3.5 V |
| REG04 | `0x20` | charge current 2048 mA |
| REG05 | `0x13` | precharge 128 mA, termination 256 mA |
| REG06 | `0x5e` | charge voltage 4.208 V |
| REG07 | `0x9d` | termination on, I2C watchdog 40 s, safety timer 12 h, JEITA cool current 20% |
| REG08 | `0x03` | die thermal regulation at 120 °C |
| REG09 | `0x44` | timer doubled in regulation, JEITA warm voltage −200 mV |
| REG10 | `0x3e` | TS at 49.8% of REGN |

**What the readings show:**
- The values are the chip's defaults, as expected with no driver.
- The input limit (500 mA) is the real bound on charging, from either the
  computer or the owner's fast charger, which the chip also classified as
  SDP ([power status record](../2026-10-31-gemini-power-status/README.md)).
- **The TS reading has never moved:** `0x3e` in all 54 reads over two days,
  four boots, charging and not, plugged and unplugged. That code is the
  nearest to exactly 50%.
- **Inference:** the TS pin sits on a fixed divider, not the battery NTC.
  The vendor reading the NTC through the PMIC instead fits that. If so, the
  BQ25896's hardware JEITA never trips, and mainline has no
  battery-temperature charging cutoff at all. What remains is the die's
  120 °C regulation and the 12 h safety timer. The schematic would settle
  it.

## Station 10: the TOPRGU read (predeclared)

**The image:**
- built at `cb64339d` (830 patches): boot2 `862af578…`, `Image.gz`
  `1a900bf3…`, boot DTB `8fc41f04…`, `auxadc_thermal.ko` `4a92c807…`. It
  replaces the `0e082142` image that had `/dev/mem` only;
- the station profile with `CONFIG_DEVMEM=y`, `CONFIG_STRICT_DEVMEM=y` and
  no `IO_STRICT_DEVMEM`, so RAM stays off-limits while driver-owned
  registers can be read;
- its modules are byte-identical to the ones station 9 ran its hold on:
  `mac` `b0a49e5c…`, core `fbb2407b…`, CONSYS `72147b51…`.

**The read:** after boot and before Wi-Fi starts, three reads with
`busybox devmem` and no write. Bit 18 is the thermal request in each
([register map](../../docs/hardware/mt6797-thermal-management.md#4-protection-thresholds-and-actions)):
- `0x1000700c`: status, a thermal reset asserted;
- `0x10007030`: request enable;
- `0x10007034`: an IRQ instead of a reset.

| Observation | Reading |
|---|---|
| `0x10007030` bit 18 set, `0x10007034` bit 18 clear | A thermal request resets the chip under mainline, as the bootloader left it; protection still needs TEMPPROTTC armed |
| `0x10007030` bit 18 clear | Thermal requests are ignored; mainline must enable the route itself |
| `0x10007034` bit 18 set | A request raises the watchdog interrupt instead, and what mainline does with it decides the outcome |
| `0x1000700c` bit 18 set | The last reset was a thermal one; record it |
| A read fails or the station stops responding | `devmem` cannot reach TOPRGU this way; record and stop |

## Implementation for station 10 (2026-10-31, owner request)

**Steps 1 and 2, in the station series:**
- **The sensor driver:**
  - from the earlier series: 0517 (ordered start with a valid first sample
    from every bank), 0518 (its test), 0519 (the thermal reset in the
    DTSI), 0520, and 0541 (the V4 conversion fix);
  - [0353](../../patches/proposals/0353-thermal-mediatek-build-the-MT6797-variant-without-th.patch):
    the driver links as a module without the DVFSP handoff;
  - it is built as the `auxadc_thermal` module and loaded first by the
    station's init.
  - **The first-valid gate:** 0517's first-sample check takes one valid
    sample from every bank right after a controller reset. It rejects raw 0
    and out-of-range values, so it serves as the gate as long as the reset
    clears TEMPMSR, which is not verified. The vendor's `0xda1` sentinel is
    not added.
- **[0354](../../patches/proposals/0354-thermal-mediatek-arm-the-MT6797-hardware-thermal-res.patch),
  the 117 °C hardware reset:**
  - **When it arms:** only when the board names TOPRGU and a threshold, and
    only while every bank reads valid and at least 20 °C below it.
  - **The threshold code** is the highest raw value that still converts to
    117 °C, found with the driver's own conversion.
  - **Order:** the vendor's. The TOPRGU route goes off, each bank's
    TEMPPROTCTL and TEMPPROTTC are written and its hot bit set, then the
    route goes back on as a reset.
  - **On unload:** it disarms, then unregisters the zone before the clocks
    stop.
- **[0355](../../patches/proposals/0355-dt-bindings-thermal-mediatek-add-the-hardware-reset-.patch):**
  the binding for `mediatek,toprgu` and `mediatek,hw-reset-millicelsius`.
- **[0356](../../patches/proposals/0356-arm64-dts-mediatek-add-the-Gemini-PDA-development-st.patch),
  the station board** (the wifi-service board plus):
  - one zone, polled every second;
  - a hot trip at 95 °C, which only notifies;
  - a critical trip at 110 °C, an orderly power-off forced after 10 s
    (`CONFIG_THERMAL_EMERGENCY_POWEROFF_DELAY_MS`);
  - the reset armed at 117 °C.
- **Station fragment:** `THERMAL`, `THERMAL_OF`, `THERMAL_HWMON`, `NVMEM` and
  the LK devinfo provider built in; the sensor driver as a module.

**Tested in the VM:**
- the station profile builds;
- W=1 is clean in `drivers/thermal/mediatek` and `drivers/nvmem`;
- the station DTB carries the zone, both trips and the reset properties;
- `station-dt.sh` passes on it.

Not run on the device.

**Readings on station 10 (predeclared),** after the TOPRGU read above:

| Observation | Reading |
|---|---|
| `thermal=loaded`, zone 0 between 25 and 60 °C, `hardware thermal reset armed at 117000 mC` with six raw codes | Steps 1 and 2 are in place; the raw codes are recorded against the TOPRGU read |
| The zone reads, but `not armed` names a bank | Protection rests on the software trip; that bank's reading is the item |
| `MT6797 transaction failed` or no valid first sample | No temperature; the station runs as before, and the log names the step |
| An unexpected reset shortly after the load | A false hot request: boot without the module, and record it |

## Station 10, boot `e7139954…`: temperature live, reset armed

**Identity:**
- boot2 `862af578…`, release `7.1.3-gemini-a53-station`, 8 CPUs, data
  partition mounted;
- modules match the package: `auxadc_thermal` `4a92c807…`, `mac`
  `b0a49e5c…`, CONSYS `72147b51…`, core `fbb2407b…`.

**Thermal at boot:** `/run/station/status` reported
`thermal=loaded zone=33900`, and the driver logged:

> `hardware thermal reset armed at 117000 mC: raw 2759/2737/2742/2742/2742/2742, REQ_MODE=0x003c0003 REQ_IRQ_EN=0x00300004`

- **The zone:** `soc-thermal`, enabled, read 33.5 °C, with its hot (95 °C)
  and critical (110 °C) trips.
- **The raw codes:** banks 2-5 share sensor MCU2, so they carry the same
  code.

**TOPRGU, read with `devmem` after the arm:**

| Register | Value | Decoded |
|---|---|---|
| `WDT_MODE` `0x10007000` | `0x00000015` | enabled, external reset, auto-start |
| `WDT_STATUS` `0x1000700c` | `0x00000000` | no thermal (or other) reset recorded |
| `REQ_MODE` `0x10007030` | `0x003c0003` | bit 18 (thermal, set by 0354), plus bits 0, 1 and 19-21 |
| `REQ_IRQ_EN` `0x10007034` | `0x00300004` | bit 18 clear: a thermal request resets the chip |

- **Deviation from the predeclared read:** the station's init loads the
  driver before any SSH command, so the registers were read after the arm,
  not before it.
- **What that leaves unknown:**
  - whether the bootloader had already set bit 18 (0354 ORs it in);
  - who set bits 0 (SPM thermal), 1 (SPM/SCPSYS) and 19-21, which were not
    written here and must come from before Linux. Bit 0's interrupt bit is
    clear, so an SPM thermal request would also reset.
- **The watchdog runs** (`WDT_MODE` bit 0), which the reset route needs.

**Wi-Fi:** joined from the image's own modules (no SSH copy), with a lease
and 3 of 3 gateway pings.

**Bounded load** (Wi-Fi connected, 8 busy loops for 180 s, a reading every
5 s, a stop at 80 °C):

| Time | Temperature |
|---|---|
| rest | 34.5 °C |
| 15 s | 47.6 °C |
| 60 s | 49.5 °C |
| 120 s | 50.9 °C |
| 180 s | 51.7 °C (load stopped by time) |
| 10 s after | 37.6 °C |
| 60 s after | 35.9 °C |

No trip fired, no reset occurred, and the station stayed up with Wi-Fi
connected.

**Readings:**
- **The first predeclared row:** steps 1 and 2 are in place. The reset is
  armed, and the arm itself raised no false request.
- **The readings are live:** they respond within one 5-10 s sample, rising
  13 °C in 15 s and falling 14 °C in 10 s. That rules out the stale-value
  worry for this use, though it does not measure conversion age.
- **About 52 °C after 3 minutes of full A53 load** at a fixed frequency,
  far below the 95 °C hot trip. Accuracy against a reference thermometer is
  still unmeasured.
- **Not tested, on purpose:**
  - whether the 117 °C reset fires;
  - whether the 110 °C critical trip powers off.
  Both would need the SoC heated to those temperatures.

## Step 3 implementation for station 11 (2026-10-31, owner request)

**The reading:**
- [0357](../../patches/proposals/0357-dt-bindings-iio-adc-mt6359-auxadc-add-MT6351.patch)-[0360](../../patches/proposals/0360-arm64-dts-mediatek-mt6797-add-the-MT6351-AUXADC.patch)
  add the MT6351 to the upstream `mt6359-auxadc` IIO driver, with its
  binding, its MFD cell and the DT node.
- **One channel,** the battery NTC:
  - request: channel 3's bit in `AUXADC_RQST0` through its set alias
    (`0x0e98`);
  - result: ready bit 15 of `AUXADC_ADC3` (`0x0e06`), 12 bits;
  - scale: ×2 against 1.8 V.
- **What it never touches:**
  - channel 11, whose read switches the VBIF28 pad;
  - the modem's `RQST1` and the ring;
  - the clocks, which LK leaves on (the
    [PMIC ADC doc](../../docs/hardware/mt6351-pmic-adc.md#32-adc-clock)
    has the reads).
- **Wiring:**
  - the station loads the driver as `mt6359-auxadc` after the thermal
    module;
  - `IIO` is built in.
- **Conversion in `power-status` (`d43534da…`):**
  - `R = 24000 × V / (2800 − V)`, with `V = raw × 3600 / 4096`;
  - the 17-entry vendor table;
  - 2.8 V is VBIF28's set voltage, where the vendor measures it and falls
    back to 2.77 V (about 0.3 °C apart here).
  - **Host test:** within 0.1 °C of the table at 25, 50 and 55.5 °C; codes
    outside the range read as unavailable.

**The stop:** [`charge-guard`](../2026-10-30-mainline-dev-station/charge-guard.c)
(`c23f655b…`), in the RAM root and not started at boot.
- **A pass every 10 s:**
  - at 50 °C or more, or with no reading, it clears `CHG_CONFIG` (REG03
    bit 4);
  - while stopped, it rewrites REG03 with `WD_RST` (bit 6), so the chip's
    40 s I2C watchdog never returns it to its defaults;
  - below 47 °C it sets `CHG_CONFIG` once and stops the kicks.
- **Its only write is REG03,** after REG14 confirms the BQ25896, with every
  other bit written back as read. `-n` makes it a dry run.
- **Host test (fake bus):**
  - 25 → 51 → 51 → 46.6 → 44 → 25 °C gave three writes, all to REG03, and
    REG03 ended at `0x1a`, as it started;
  - with no reading it stopped;
  - the dry run and a wrong part number wrote nothing.

**Station 11 image:**
- built at `6ed7637e` (834 patches): `Image.gz` `993149dc…`, boot2
  `cf4a2196…`;
- `mt6359-auxadc.ko` `78d033bb…`; the other modules are unchanged;
- flashed from station 10 with a matching readback (predecessor
  `862af578…`).

**Device tests (predeclared):**

*S3a, read-only, on the first station 11 boot:*
- `battery-adc=loaded`;
- `power-status` shows `batt_temp` between 15 and 40 °C, a few degrees
  under the SoC zone at rest;
- `charge-guard -n -c 6` logs `none` six times.

| Observation | Reading |
|---|---|
| `batt_temp` plausible and steady within 1 °C across reads | The NTC path works |
| `batt_temp=unavailable` or an ADC timeout | The request or the clocks are the item; the raw code names it |
| A value outside 0-60 °C at room temperature | The scaling or the pull-up assumption is wrong; stop before S3b |

*S3b, the first charger write. It needs the owner's approval first: it is
a C2b charger write.*
- **The run:** cable in, `charge-guard -s <current-20> -r <current-40> -c 9`.
  The thresholds sit below the present temperature, so it stops and holds
  for about 80 s.
- **The restore:** then thresholds above it, `-s 600 -r 550 -c 2`, so it
  resumes.
- **The check:** read REG03 and REG0B with `power-status -r` after each.

| Observation | Reading |
|---|---|
| REG03 `0x0a` and charge state `no` while held; REG03 `0x1a` and the state back to `pre` or `fast` after the resume | The stop works and is reversible |
| The state stays `fast` with REG03 bit 4 clear | `CHG_CONFIG` alone does not stop this chip; stop and record |
| REG03 returns to `0x1a` by itself while held | The watchdog kick does not hold; stop and record |

### Station 11, boot `b4cde2f8…`: S3a, the battery temperature reads

- **Identity:**
  - release `7.1.3-gemini-a53-station`;
  - `/run/station/status` shows `thermal=loaded zone=34500` and
    `battery-adc=loaded`;
  - `mt6359-auxadc.ko` `78d033bb…`, `charge-guard` `c23f655b…`,
    `power-status` `d43534da…`.
- **The driver:** `mt6359-auxadc` probed in 317 µs. IIO device 0 is
  `MT6351`, with `in_temp0_raw` (labelled `batt_temp`).
- **Readings at 16-41 s:** `batt_temp` 29.1-29.4 °C (raw 837-843), steady
  across three `power-status` reads and six `charge-guard` passes. The SoC
  zone read 32.9 °C.
- **`charge-guard -n -p 2 -c 6`:** six passes, all `action=none`, and no
  write.
- **REG03 changed by itself** during those passes:
  - it read `0x0a` (`CHG_CONFIG` clear) up to 39 s and `0x1a` at 41 s;
  - REG0B went from `0x26` (not charging) to `0x36` (fast).

**Reading:**
- **The first S3a row:** the NTC path works and reads plausibly, a few
  degrees under the SoC at rest.
- **Inference:** the bootloader leaves charging disabled (`CHG_CONFIG` = 0)
  under host mode, and the chip's 40 s I2C watchdog then returns it to its
  defaults, which charge. That explains the `no`-then-`fast` pattern on
  every mainline boot so far
  ([power status record](../2026-10-31-gemini-power-status/README.md)).
- **It also shows `CHG_CONFIG` = 0 stops charging** on this chip, since the
  bootloader's own write did. S3b still tests the guard's write and its
  watchdog kick.

### Station 11, boot `b4cde2f8…`: S3b, the charger write (owner-approved)

**Run 1, `charge-guard` `c23f655b…`, cable in, battery at 29.2 °C:**
- **The hold:** `-s 273 -r 250 -p 10 -c 9`, so thresholds below the present
  temperature:
  - the first pass `action=stop` read REG03 `0x1a` and wrote `0x4a`
    (`CHG_CONFIG` clear, `WD_RST`);
  - eight `hold` passes followed, 10 s apart, each reading REG03 `0x0a`;
  - while held: `charging=no`, REG0B `0x26`.
- **The resume:** `-s 600 -r 550 -c 2` reported `action=none` twice and
  left REG03 at `0x0a`.
  - **A bug:** a new run started with no memory of the stop, so it never
    set `CHG_CONFIG` again.
  - With the kicks gone, the chip's watchdog returned it to its defaults
    about 47 s after the last write: `charging=fast`, REG0B `0x36`.

**Fix:** whenever charging is allowed and `CHG_CONFIG` reads clear,
`charge-guard` sets it (`dc4d00db…`).
- **Host test:** a fresh run at 25 °C finds `0x0a` and restores `0x1a` with
  one write. The other cases are unchanged.
- **Deployed** to `/bin` on the running station.

**Run 2, `dc4d00db…`:**
- **The hold:** `stop` at 280 s, then three `hold` passes with REG03 `0x0a`.
  While held: `charging=no`, REG0B `0x26`.
- **The resume:** `action=resume` read `0x0a` and wrote `0x1a`. The next
  pass read `0x1a` and did nothing.
- **Right after, and 15 s later:** `charging=fast`, REG0B `0x36`.

**Kernel log:** no I2C error and no fault. The only matches are the
ramoops lines and the known I2C6 guard message.

**Reading (first S3b row):**
- **The stop works and is reversible:** clearing `CHG_CONFIG` stops
  charging, and the `WD_RST` kicks hold it there past the 40 s watchdog.
- **Two ways back:** setting `CHG_CONFIG` resumes charging at once, and
  without the guard the chip resumes on its own within about 47 s.
- **Not shown:**
  - a real 50 °C battery, not heated on purpose;
  - `charge-guard` running at boot, which the station image does not do
    yet.

### Station 11b: `charge-guard` at boot (owner decision, 2026-10-31)

**The change:**
- the station's inittab respawns `charge-guard -q`, logging to
  `/run/station/charge-guard.log`;
- `-q` logs only the passes that act, plus one every 60 passes (10 min);
- `charge-guard` `b3eb2fb9…`; its host tests are unchanged.

**The image:** the same kernel package (`6ed7637e`, `Image.gz` `993149dc…`)
with a new RAM root `9cea3734…`: boot2 `86445297…`.

**Effect at boot:**
- the first pass sets `CHG_CONFIG`, so charging starts within seconds of
  init instead of after the 40 s watchdog;
- from then on the 50/47 °C window holds.

**Readings (predeclared):**

| Observation | Reading |
|---|---|
| The log's first line shows `action=resume` with REG03 `0x0a`, then one line per 10 min with `none` | The guard runs from boot and ends the handoff's disabled state |
| The log shows repeated starts | The guard exits; it is respawned, and its exit is the item |
| No log | inittab did not start it |

**Station 11b, boot `82e5d1a2…`:**
- **Identity:** `thermal=loaded zone=33800`, `battery-adc=loaded`, and
  `charge-guard` `b3eb2fb9…` running as PID 163 (`-q`).
- **The log at 14 s of uptime:**
  - `charge-guard: stop=500 resume=470 (0.1 C) period=10s`;
  - `t=1 temp=296 raw=831 reg03=0x0a action=resume`.
- **`power-status` at 14 s:**
  - `charging=fast`, REG0B `0x36`, battery 4.30 V, `batt_temp` 28.8 °C;
  - `ichg=0.15A` (REG12 `0x03`), the first nonzero charge current read on
    mainline: charging now starts early, before the battery tops off.

**Reading:** the first predeclared row. The guard runs from boot, ends the
handoff's disabled state at its first pass, and holds the 50/47 °C window
from then on.

## Station 12: protection in the kernel (owner decision, 2026-10-31)

Two changes, so a hot SoC or battery ends in a power-off whatever userspace
is doing:
1. **The SoC driver and the PMIC ADC driver are built in**
   (`MTK_SOC_THERMAL=y`, `MEDIATEK_MT6359_AUXADC=y`):
   - the 117 °C reset arms during boot, before init;
   - an `rmmod` can no longer disarm it;
   - init only records the zones.
2. **A kernel battery zone,**
   [0361](../../patches/proposals/0361-arm64-dts-mediatek-gemini-station-add-a-battery-temp.patch):
   - the upstream `generic-adc-thermal` driver on the BATON channel, with
     the vendor table converted to the IIO processed value (raw × 3600,
     the node voltage in mV × 4096);
   - a zone polled every 10 s, with a critical trip at 60 °C, the table's
     end and the vendor battery zone's critical point;
   - **why it is needed:** a dead or hung `charge-guard` stops its watchdog
     kicks, and the charger then resumes charging within 40 s. This trip
     covers that.
   - **Limits:** readings beyond 60 °C clamp to 60 °C, so a shorted NTC
     powers off (fail-safe), while an open NTC reads −20 °C and does not.

`charge-guard` keeps the 50/47 °C window.

**Tested in the VM:**
- the station profile builds;
- W=1 is clean in `drivers/thermal` and `drivers/iio/adc`;
- the DTB carries the zone, the table and the trip.

**Readings (predeclared):**

| Observation | Reading |
|---|---|
| Two zones in init's status: `soc-thermal` near 33 °C and the battery zone within 2 °C of `power-status`'s `batt_temp`; the arm logged during boot | Both kernel backstops are in place |
| The battery zone missing, or reading −20 or 60 °C at room temperature | The IIO scale or the lookup units are wrong; the zone is the item |
| No arm line | Built in, the driver probed before a supplier; the log names the deferral |

## Step 3 design: a battery-temperature charging stop

The charger cannot see the battery, so the stop needs two things:
- **A reading:** the battery NTC on MT6351 AUXADC channel 3 (`BATON`), as the
  vendor reads it, converted against the measured VBIF28 rail
  ([PMIC ADC](../../docs/hardware/mt6351-pmic-adc.md#31-battery-ntc-conversion-vendor-fuel-gauge-path)).
  Mainline has no MT6351 ADC driver; the nearest, `mt6359-auxadc`, has a
  different register layout.
- **An action:** stopping charging is a BQ25896 write (`CHG_CONFIG`, REG03
  bit 4). That is charge control, so it belongs to C2b and its review.

**The smallest form:**
- a read-only IIO driver for the battery NTC channel:
  - it requests through `AUXADC_RQST0` and reads the AP result registers;
  - it never touches `RQST1`, the wrapper's ring pointers or the MDBG
    engine, which belong to the modem's GPS/crystal temperature channel
    ([modem share](../../docs/hardware/mt6351-pmic-adc.md#6-sharing-the-adc-with-the-modem));
  - its timeout allows for a modem-side engine that may run from a
    hardware default, since who enables it is still open;
- the vendor's conversion (24 kΩ to VBIF28 and the 17-entry 10 kΩ table),
  which `power-status` reports;
- in C2b, charging stopped at 50 °C and resumed below 47 °C, as Gemian does.

**Until then:** charge only from a USB host port (500 mA input), and keep
sessions attended.

## What mainline needs (proposal, not admitted)

In order:
1. **The SoC temperature on the station.**
   - The corrected V4 observer of the
     [thermal series](../2026-09-04-mt6797-thermal-snapshot/README.md#corrected-v4-runtime-result)
     (0535-0542) read all seven slots validly on one boot: 34.9-35.4 °C at
     rest.
   - Still unresolved: the conversion age and the calibrated accuracy.
   - The station series carries the sensor driver only up to 0513, so the
     next step is the V4 reading on the station, as a module, next to a known
     load.
   - Add the vendor's `0xda1` first-valid gate, which protection needs
     anyway.
   - Everything below depends on the calibrated conversion.
2. **The 117 °C hardware reset:**
   - program TEMPPROTCTL, TEMPPROTTC and the hot request as the vendor
     does, reading every bank first;
   - route TOPRGU thermal bit 18 to a reset;
   - it needs no software running, so it also covers a hang.
3. **A software critical trip** around 110 °C for an orderly `poweroff`, and
   a warning near 85-95 °C. No cooling device is needed while the CPU runs
   at a fixed frequency.
4. **A battery-temperature charging stop:** the battery NTC through the
   MT6351 AUXADC (power status S2), stopping charging at 50 °C as the
   vendor does. This is part of C2b, since the BQ25896 cannot see the
   battery temperature itself.

**Until then:**
- keep station sessions attended;
- keep charging on USB host power (500 mA input).

**Still unknown:**
- the TOPRGU request state under mainline (station 10);
- the calibrated sensor accuracy;
- whether the BQ25896 TS pin is really on a fixed divider (the schematic).

The MT6351 shuts down in hardware at 150 °C per its datasheet.
