# Experiment: what thermal protection the station needs

| Field | Value |
| --- | --- |
| ID | `2026-10-31-gemini-thermal-protection` |
| Status | `running`: steps 1 and 2 work on station 10 (temperature live, 117 °C reset armed, untriggered); step 3 designed |
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

## Step 3 design: a battery-temperature charging stop (not implemented)

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
