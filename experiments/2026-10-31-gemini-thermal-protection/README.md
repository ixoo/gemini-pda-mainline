# Experiment: what thermal protection the station needs

| Field | Value |
| --- | --- |
| ID | `2026-10-31-gemini-thermal-protection` |
| Status | `running`: charger temperature settings read on the device; TOPRGU read prepared; no protection implemented |
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
- built at `0e082142`: boot2 `4a32af25…`, `Image.gz` `176badf3…`;
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
