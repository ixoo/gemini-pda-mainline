# Experiment: what thermal protection the station needs

| Field | Value |
| --- | --- |
| ID | `2026-10-31-gemini-thermal-protection` |
| Status | `running`: vendor policy read; charger temperature settings read on the device; no protection implemented |
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

## The Gemian vendor kernel

From a source read of the Gemian 3.18 kernel at `8cfe6596`. Paths are in
that tree.

**Hardware reset at 117 °C:**
- `THERMAL_CONTROLLER_HW_TP=1`
  (`drivers/misc/mediatek/thermal/mt6797/inc/tscpu_settings.h`).
- At probe, the kernel thermal driver programs each bank of the SoC
  thermal controller (`0x1100b000`):
  - TEMPPROTCTL `+0x0c0` set to `0x20000`;
  - TEMPPROTTC `+0x0cc` set to the 117 °C threshold, converted with the
    efuse calibration;
  - TEMPMONINT `+0x00c` bit 31 set, the hot request
    (`set_tc_trigger_hw_protect`, `mt6797/src/mtk_tc.c`).
- The thermal request is then routed to a reset on the TOPRGU watchdog
  (`0x10007000`): REQ_MODE `+0x30` and REQ_IRQ_EN `+0x34`, thermal bit 18
  (`drivers/watchdog/mediatek/wdk/wd_api.c`, `wdt/mt6797/mt_wdt.h`).
- The source notes that every bank must be read before the threshold is
  written, or a false reset request reaches the watchdog
  (`common/thermal_zones/mtk_ts_cpu.c`).
- This tree has no bootloader source, so whether the preloader or LK also
  arms it is unknown.

**Software, the CPU zone only:**
- polled every 40 ms, with four trips (`mt6797/inc/tzcpu_initcfg.h`):

  | Trip | Action |
  |---|---|
  | 65 °C | adaptive power limit |
  | 85 °C | CPU frequency limit |
  | 95 °C | CPU frequency limit |
  | 117 °C | deliberate crash-reset |

- **Other zones:** battery, board NTCs, PMIC, PA, Wi-Fi, DA9214 and DRAM
  are built, but have no trips unless a userspace daemon configures them.
- **The cooling actions that exist:** charge current (BCCT), modem TX and
  backlight. None is configured by default.

**Charging:**
- **Software stop:** charging stops at 50 °C and resumes below 47 °C, with
  the battery NTC read through the PMIC and fuel gauge (`mt6797.dtsi`
  `max_charge_temperature`).
- **Off:** the low-temperature stop and software JEITA.
- **Not used by the vendor:** the BQ25896's own TS input.

**Reading:** on Gemian, the effective protection is the CPU zone, the
117 °C hardware reset and the 50 °C charging stop. On mainline, none of the
three exists:
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

## What mainline needs (proposal, not admitted)

In order:
1. **One valid SoC temperature reading.** The
   [thermal series](../2026-09-04-mt6797-thermal-snapshot/README.md)
   (0057, 0512-0542) never produced one on the device. Everything below
   depends on the calibrated conversion.
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
- the MT6351's own over-temperature threshold;
- the TOPRGU request state under mainline;
- the calibrated sensor accuracy.
