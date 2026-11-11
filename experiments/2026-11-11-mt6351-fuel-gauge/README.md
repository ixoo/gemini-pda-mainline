# Experiment: MT6351 fuel gauge — how the vendor reports the battery, and making ours reliable

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-11-mt6351-fuel-gauge` |
| Status | `running`: vendor study done; [0710](../../patches/proposals/0710-power-supply-mt6351-fuel-gauge-take-the-current-from.patch)-[0711](../../patches/proposals/0711-power-supply-mt6351-fuel-gauge-count-the-capacity-fr.patch) written and compiled, not on a device |
| Subsystem | MT6351 FGADC coulomb counter, `mt6351-fuel-gauge` battery supply |
| Device variant | Planet Computers Gemini PDA, MT6797X |
| Date(s) | 2026-11-11 |
| Investigator(s) | Gemini mainline project |
| Owner request | "RE Gemian to understand how it got battery status … make it better and reliable" |

Builds on [2026-10-31 fuel gauge](../2026-10-31-gemini-fuel-gauge/README.md) (registers, units,
the userspace estimator) and the [kernel charge guard](../2026-11-02-gemini-kernel-charge-guard/README.md)
record, which holds the first reports from the desktop and [0708](../../patches/proposals/0708-power-supply-mt6351-fuel-gauge-report-discharging-wi.patch).
Durable facts stay in [Gemini fuel gauge](../../docs/hardware/gemini-fuel-gauge.md).

## Question

What went wrong on card-31 (boot `242ba06e…`)?
- `current_now` read only 0, ±363, −727 and −1091 µA, including +363 while discharging.
- Capacity read 77-79 % on USB, then 60 % right after unplugging.
- Unplugged, the battery read `Not charging`, which 0708 fixes.

How does the vendor stack read the same values, and what makes ours reliable?

## Sources

- Vendor kernel `planet-community/android_kernel_planetcom_mt6797` `8cfe6596`:
  - `power/mt6797/battery_meter_hal.c`: `fgauge_read_current`, `fgauge_read_columb_internal`,
    `fgauge_initialization`;
  - `power/mediatek/battery_meter_fg_20.c`, `battery_common_fg_20.c`;
  - `mt6797/include/mach/upmu_hw.h`.
- MT6351 datasheet v12, FGADC register chapter.
- Retained private Gemian kernel logs (`[kernel]AvgVbat … IBat` lines): only counts are
  given here.
- Our driver: [0370](../../patches/proposals/0370-power-supply-add-the-MediaTek-MT6351-fuel-gauge.patch),
  0373, 0686, 0708.

No device access. Nothing private is quoted.

## How the vendor stack does it

| Value | Vendor kernel 3.18 (Gemian and the Android container both read its sysfs) |
| --- | --- |
| Status | `Charging` whenever a charger is detected and not in error, regardless of current. `Not charging` whenever no charger is present. `Full` when the userspace SOC is 100 on a charger. The current is never consulted. |
| Battery current (`IBattery`) | `FG_CURRENT_OUT` (`0x0CBA`) through the same latch as ours: `0x0200` to `CON0`'s upper byte, wait for bit 10, read, `0x0800`, wait, `0x0000`. Sign above `0x7FFF` means discharging. 158.122 µA per count × 20/R_FG × `CAR_TUNE`/100 × chip trim. |
| Charger current (`ICharging`, `BatteryAverageCurrent`) | Not the gauge: AUXADC `ISENSE` − `BATSENSE` across the charger sense resistor, 20 samples with the extremes dropped. 0 without a charger. |
| Coulomb counter | `FG_CAR` bits 30:14 and bit 34 as the sign, `0`/`0x1FFFF` as zero sentinels. 359.86 µAh ÷ 8 (OSR 8) = 44.98 µAh per step at 20 mΩ, then the same rescaling. Bits 13:0 are discarded. |
| Capacity | `UI_SOC2` from the proprietary `fuelgauged`/`libfgauge.so` daemon over netlink. It counts charge from the counter and anchors to OCV (`SET_SOC`, `SET_QMAX`, `SET_RBAT`). The kernel only republishes it and has a first-boot fallback. |
| Published voltage | The OCV table at the reported SOC, not the ADC. |
| Calibration | Header values only: `R_FG` 10 mΩ, `CAR_TUNE` 115, chip trim forced neutral, `FG_METER_RESISTANCE` 75 mΩ. The DT parser is disabled. No NVRAM calibration item is read on the kernel path. |
| FGADC set-up | Only `CON0` (`0x0029`: on, auto-calibration, 32 kHz) and `FG_OSR` (`CON15` = 8). Nothing writes `CON16`-`CON33` (sleep mode, FIR bypass, gain, mode). |

**The register works under Gemian.** In the retained logs, every one of 7446 `IBat` samples on
battery reads a discharge above 50 mA (−300 to −1600 mA). Near-zero values appear only on USB
(1190 of 1840), where a full battery sits idle. So a near-zero `FG_CURRENT_OUT` on battery is a
mainline-side state, not the chip's normal behaviour. The vendor reads the register no
differently from us.

**The vendor initialises the FGADC twice per boot; mainline relies on the first.** LK
(`lk/platform/mt6797/mt_battery.c`, under `DLPT_FEATURE_SUPPORT`) and then the vendor kernel
(`battery_meter_initial` → `fgauge_initialization`) each run:
1. `CON0` low byte `0x28`, then `0x29`: `FG_ON`, `FG_CAL` 2, `FG_AUTOCALRATE` 2;
2. `CON0` upper byte `0x71`: `SW_CR` with `OFFSET_RST`, `TIME_RST` and `CHARGE_RST`, which
   restarts the offset calibration and zeroes the counter;
3. `FG_OSR` 8;
4. reads the current until it is non-zero, up to 1000 tries.

Neither writes `FG_OFFSET` (`CON13`) or `FG_ADJUST_OFFSET_VALUE` (`CON12`) directly: the offset
comes from the hardware's own calibration after `OFFSET_RST`. Nothing writes `CON14`-`CON33`,
so `FG_SLP_EN` and the FIR bypasses keep their reset values. The kernel's capacity counts charge
in the userspace daemon from `FG_CAR`, anchored to OCV.

**Card-31 state, from the charging session's read-only dump (2026-11-11):**
- `CON0` `0x0029`, `CON15` `0x0008`, `CON16` `0x1000`, as on a working station boot.
- The FGADC is clocked and out of reset.
- **One difference: `CON13` `FG_OFFSET` reads 0, against `0x0032` on a working station boot**
  (station-work-86).
- **The counter agreed with the register: both were near zero.** The vendor slice moved from
  −41901 to −42005 µAh in about an hour. Raw `CON2` fell about 33 units per 10 s plugged into a
  500 mA port, about 0.6 mA.
- Plugged in, a near-zero battery current can be real. The unplugged snapshot is still pending
  (T1).

**Leading hypothesis (inference):** the offset calibration did not complete on this boot, and
the front end is not measuring the sense resistor. If unplugged readings also stay near zero,
the fix is the vendor's own boot step, re-run by the driver. That is an FGADC reset, a PMIC
write that needs its own test, not part of 0710-0711.

**The datasheet only names `FG_CURRENT_OUT` as the first stage's output.** It does not document
`CON15`-`CON33`. Names and fields come from the vendor header.

## What our driver did, and why it misread

- **Current:** `FG_CURRENT_OUT`, one latched sample per read. Our own records show it right on
  station 13b and in cpuidle window U0 (274 mA, matching the counter). They also show it wrong:
  - 93-95 mA against the counter's 67-70 after U1;
  - wrong again from N4 on ([cpuidle](../2026-11-07-mt6797-cpuidle/README.md));
  - near zero on card-31, where the counter was near zero too.

  Where the two disagreed, the counter matched the expected step resolution and gave consistent
  results across windows. The cpuidle record moved its power measurements to the counter.
- **Capacity:** the OCV table at V − I × R. With I near zero:
  - on USB, the charging voltage reads high;
  - on battery, the loaded voltage reads low, about 19 points of the jump from 79 % to 60 %.

  This is inference. The two voltages were not logged together.
- **Status:** the current alone with a ±20 mA band. 0708 now reports `Discharging` inside the
  band when no supply is online.

## The fix

[0710](../../patches/proposals/0710-power-supply-mt6351-fuel-gauge-take-the-current-from.patch):
**current from the counter.**
- Read the whole 35-bit counter, `CON1`-`CON3`, as a two's complement value. Bits 13:0 are the
  fraction the vendor drops: 6.31 nAh per bit on this board, against 103 µAh per vendor step.
- `current_now` is the counter's change over a window of at least 5 s, timed with the boot
  clock. The first window opens at probe.
- Until that window closes, the register value is used.
- A `dev_dbg` line logs both for each window, for the comparison in T2.
- `charge_counter` keeps its units and gains the fraction.
- The arithmetic uses `mul_u64_u64_div_u64`, so it cannot overflow at any realistic charge.

[0711](../../patches/proposals/0711-power-supply-mt6351-fuel-gauge-count-the-capacity-fr.patch):
**counted capacity.**
- Take an OCV reading (V − I × R in the OCV table) once the first window gives a current. From
  then on, capacity = that charge + the counter's change since, against `charge_full_design`.
- Take a new reading when the battery has rested in the ±20 mA band for 5 minutes. That
  happens when it is held at the charge limit on the charger, or when charging ends.
- Before the first window, the old voltage reading is reported.

Both are built-in changes to an existing built-in driver (`CONFIG_BATTERY_MT6351=y`), so they
need an image, batched with other built-in work.

**Checked:**
- W=1 compile of the driver against the station configuration, with no warnings;
- `checkpatch --strict` clean;
- both apply in sequence after 0708, and are appended to `patches/series` and
  `patches/series-a53-station`.

**Not checked:** any device run; a full kernel build.

**Ownership, agreed by message with the charging-protection session:**
- this record owns `mt6351-fuel-gauge.c`;
- the charging-protection session owns bq25890, the guard, 0695 and 0708's status rule, which
  0710 leaves as it is.

The guard needs these kept: the supply name `battery`; a `capacity` soon after registration;
`temp` and its four limits readable; and no `charge_control_*` properties on the gauge, which
0695 adds as an extension. 0710-0711 keep all of them. The guard reads `capacity`. Counted capacity removes the voltage swing near the limit that that
record flagged. A re-reading after a rest can still move capacity by a few points.

## Limitations

- **Full capacity is the design value, 4268 mAh.** An aged cell counts down too slowly and is
  corrected at the next rest reading. Learning the full charge from a full charge or discharge
  is not done.
- **Nothing is kept across boots.** Each boot starts from an OCV reading under load, so its
  accuracy depends on the 165 mΩ resistance in the DT.
- **The counter's absolute scale (`CAR_TUNE` 115, chip trim neutral) has not been checked**
  against a reference current. Both registers share it, so 0710 changes no scale.
- **Why `FG_CURRENT_OUT` reads near zero on mainline is unknown.** T1 is the discriminating
  read.
- **`fuelgauged`/`libfgauge.so` were not disassembled.** Their netlink interface shows a
  counter with OCV anchoring, which 0711 reproduces in its simplest form. Their tuning (Qmax
  ageing, Rbat) is not needed for correct status, current or a smooth capacity.

## Device tests (requests to the custodian)

### T1: read-only register dump on the running station (no new image)

- **Hypothesis:** on mainline the FGADC registers differ from the vendor set-up (`CON0` low
  byte `0x29`, `CON15` OSR 8, `CON16`-`CON27` as LK leaves them), or `FG_CURRENT_OUT` sits near
  zero while the counter moves.
- **Unique observation:** `FG_CURRENT_OUT` and the counter's slope side by side, on battery.
- **Procedure, unplugged, screen lit:**
  1. Read `0x0CA4`-`0x0CE6` (FGADC `CON0`-`CON33`) and `TOP_CKPDN_CON2` from the PMIC regmap
     debugfs, the way station 12 did. Read only those lines.
  2. Every 10 s for 60 s, read `current_now`, `charge_counter`, `voltage_now` and `capacity`
     from `/sys/class/power_supply/battery`, and the boot clock.
  3. Repeat step 1 once at the end.
- **Writes:** none, apart from the driver's own latch, which every sysfs read already performs.
- **Decision:**
  - `CON15` other than `0x0008`, or a `CON16`/`CON26`/`CON27` field set that the vendor never
    writes: name that field, and find what set it (LK or a mainline driver).
  - The counter's slope is at hundreds of mA and `FG_CURRENT_OUT` within a few counts of zero:
    the register is unreliable here, and 0710 is the fix.
  - The counter is near zero too, with `FG_OFFSET` 0: the FGADC is not measuring. 0710-0711
    would not help. The next item is re-running the vendor's init step, as its own write test.
  - Both read hundreds of mA: card-31's readings came from the cable, and nothing is broken.
- **Stops:** the battery under 30 %; any PMIC read error; the station not on the expected boot.

**T1 attempt 1, 2026-11-11 about 11:40, card-31, boot `242ba06e…`, unplugged:**
- Stopped at its first check: capacity read 2 %, under the 30 % floor. No register dump was
  taken.
- Three sysfs reads 2 s apart, backlight 512/1023, video playing over Wi-Fi:

  | `voltage_now` | `capacity` | `current_now` | `status` |
  |---|---|---|---|
  | 3631091 | 15 | −4364 | Discharging |
  | 3565502 | 3 | −1454 | Not charging |
  | 3592364 | 3 | −639714 | Discharging |

- **Reading:**
  - The register is not stuck. Unplugged, it gave one real-looking discharge (−640 mA) among
    near-zero samples under a steady load. That fits a single latched sample being unreliable,
    which is the case for 0710's counter window. `charge_counter` was not read, so this is not
    yet confirmed.
  - Capacity follows each sample's I × R correction: 15 % with −4 mA, 3 % with −640 mA.
  - The `Not charging` row is this image's pre-0708 status rule.
  - From 60 % at about 11:09 to about 3 % at about 11:40 is far more than 4268 mAh can lose in
    31 minutes at these currents. So the earlier readings, taken just after a charge, were high;
    the loaded 3.57-3.63 V now is genuinely low. Inference.
- **Rerun** above 30 %, with `charge_counter` in every sample.

**Owner report, minutes later:**
- Card-31 became unreachable.
- Started on the Gemian side with the cable in, Gemian read **86 %**: "the problem is that it
  reads low".
- Whether the card powered off on UPower's critical action or browned out is not yet known.

Two explanations, which need opposite fixes:
- **Our voltage is wrong by about 0.5 V.** The station table maps 3.63 V to 3 %, and 86 % needs
  about 4.19 V. Our voltage was checked only at the top, against the BQ25896 at 4.31 V.
- **Gemian's 86 % is not a measurement.** At boot, `dod_init_in_kernel` takes the SOC its last
  session saved in the RTC spare byte:
  - always, when no battery was removed and no charger is present, if that value is non-zero;
  - on a charger, unless that value is more than 10 points from its voltage-based `gFG_sw_soc`.

  A stale value can survive a mainline session that drained the battery.

**Asked of the custodian (read-only):**
- the previous card boot's journal: a clean UPower action, or an abrupt end;
- Gemian's `[dod_init_in_kernel] rtc_fg_soc=… gFG_sw_soc=… gFG_hw_soc=… preD0=…` line;
- its first `[kernel]AvgVbat … bat_vol` ADC line. Gemian's `voltage_now` is a table lookup,
  not the ADC.

**Answers so far:**
- **The power-off was the owner's own, from the desktop:** a clean `systemctl poweroff` in the
  journal. It was not a low-battery action and not a brownout.
- **Next station boot `eb10883d…`** (same station-work-100 kernel), cable in, about 87 s
  uptime, after a Gemian charging session of unknown length. Five reads 2 s apart:

  | Property | Reading |
  |---|---|
  | `voltage_now` | 4.041-4.083 V |
  | `current_now` | +79 to +112 mA |
  | `capacity` | 72-77 % |
  | `status` | `Charging` |

  Less I × R, that is an OCV of about 4.03-4.06 V, which the table maps to 71-73 %. The voltage
  path reads plausibly here.
- **Reading (inference):**
  - The 3.57-3.63 V earlier was the cell under a heavy load: video, Wi-Fi and the Wi-Fi
    worker's spin.
  - If its real resistance is well above the 165 mΩ in the DT, as an aged cell's can be, the
    voltage-based capacity reads far too low under load. That is the error 0711's counting
    removes.
  - The OCV reading taken at boot under load still carries it, until the first rest reading.
  - How much was recharged in between is unknown, so the 86 % against 3 % gap is not settled.
- **Still wanted:** Gemian's boot line (B) and T1 with the counter. A measured cell resistance
  would come from two voltage/current pairs at different loads a few seconds apart, from T1's
  samples.

**T1 attempt 2, card-31 boot `d41819cc…`, unplugged, video playing (about 2 CPUs busy):**
- Stopped at the 3.80 V floor: `voltage_now` read 3.47 V.
- Follow-up reads 2 s apart:

  | Uptime (s) | `voltage_now` | `current_now` | `charge_counter` | `capacity` |
  |---|---|---|---|---|
  | 621.5 | 3.546 V | −964 mA | −27003 | 23 |
  | 623.6 | 3.669 V | −575 mA | −27520 | 27 |
  | 625.6 | 3.529 V | −1262 mA | −28037 | 15 |
  | 627.7 | 3.573 V | −1059 mA | −28555 | 19 |
  | 629.8 | 3.587 V | −866 mA | −29072 | 49 |

- **The counter runs on this boot,** unlike `242ba06e…`: 2069 µAh in 8.26 s is 0.90 A. The
  register's mean over the same samples is 0.95 A. The two agree within 5 %, which supports the
  counter's scale, the same for both registers.
- **A straight-line fit of V = OCV + R × I gives R ≈ 0.20 Ω and an OCV of about 3.77 V,** about
  29 % on the table. The voltage and current come from separate reads 2 s apart and the
  register is one sample, so this is rough. It puts the resistance near the DT's 165 mΩ, not
  the 0.4-0.5 Ω a comparison with a different boot's charging voltage would suggest.
- **Reading (inference):**
  - The battery was genuinely low, about a quarter to a third, under a 0.9 A load.
  - The reported capacity jumped from 15 to 49 % because each read pairs the voltage with a
    different instantaneous current sample, not because of the table or the resistance.
  - 0710's windowed current and 0711's counting remove that jumping.

**T1 completed, same boot `d41819cc…`, light load** (private output
`artifacts/card-31-audio/fuel-gauge-t1b.txt`):
- **The gauge stopped measuring after a charger plug/unplug on this boot.**
  - At 621-630 s, before any plug, it measured 0.6-1.3 A.
  - The owner plugged in at about 830 s and unplugged at about 840 s.
  - From 849 to 913 s, unplugged: `charge_counter` moved one step, and `current_now` read
    0-1.5 mA.
  - The backlight from 0 to 512 dropped the voltage by about 40 mV (about 0.2 A at 0.2 Ω), with
    no change in the current read.
- **The FGADC kept converting.**
  - `FG_NTER` (`CON4`-`CON6`, conversions since boot) rose at about 16 per second, so it was
    not reset.
  - The full-resolution counter integrated about 1 mA over 61 s.
  - `CON17` (`FG_CIC2`) moved from −87 to −1.
- **The front end sees almost no voltage across the sense resistor.**
- **Configuration was unchanged across the event:**
  - `CON0` `0x0029`, `CON15` `0x0008`, `CON16` `0x1000`, `TOP_CKPDN_CON2` `0x3070`;
  - `FG_GAIN` (`CON27`) `0x0400`;
  - `FG_OFFSET` and `FG_ADJUST_OFFSET_VALUE` `0x0000` in both dumps.

  Since this boot measured correctly before the plug with the same zero offset, `FG_OFFSET`
  is not the trigger.
- **Gemian's charger-detect handler does nothing to the FGADC.** `chrdet_int_handler` pulses
  `RG_USBDL_RST` and runs the charger task. The fault is in what mainline does, or fails to
  restore, around a plug or unplug: a PMIC rail, a USB PHY or gadget step, or the bq25890 path.
  The datasheet gives the FG a 2.8 V supply without naming the rail.
- **Consequence for 0710-0711:** with the front end blind, the counter is blind too, so neither
  patch helps in this state. The charging session's bounded late-limit case applies.

### T4: what a plug/unplug changes (read-only request)

- **Hypothesis:** a PMIC register (an LDO, a USB or charger-detect control) or a bq25890 setting
  changes on the plug/unplug, and the FG front end then reads near zero.
- **Procedure:**
  1. Fresh station boot, unplugged, light load. Check that the gauge measures: `current_now`
     at tens to hundreds of mA, and `charge_counter` falling across 3 samples 10 s apart.
  2. Take a full PMIC regmap dump (A) and the bq25890 registers through the charging session's
     read-only method.
  3. Plug the same cable and port for 15 s; note whether USB enumerates. Unplug.
  4. Repeat the check from step 1. If the gauge is blind, take dump B and the bq25890
     registers again.
  5. Plug in again for 15 s, unplug, check once more: does a second event restore it?
- **Writes:** none. Plugging and unplugging is the owner's action.
- **Decision:**
  - The A/B diff names the registers that changed; each is traced to the driver that wrote it.
  - With no PMIC or bq25890 difference, the change is outside these registers: the board path or
    the USB PHY side.
  - If the gauge still measures after step 3, repeat with the other port type (computer or wall).
- **Stops:** voltage under 3.65 V; any PMIC read error.

**First run with 0710-0711, station-work-103, boot `b8fb3cbf…`** (from the custodian; private
log `artifacts/card-32/d2-thermal.txt`):
- Charging from a wall charger in constant-voltage mode at 4.207 V for 10 minutes.
- Current tapered from 483 to 376 mA; `capacity` read 67 → 69 %.

Reading:
- **The counting is right.** The logged current integrates to 70.8 mAh over 619 s, 1.66 % of
  4268 mAh, against the 2 points reported.
- **The OCV reading at boot was about 11 points low.** 4.207 V less 376 mA × 0.165-0.20 Ω is an
  OCV of 4.13-4.15 V, about 80 % on the table, not 67-69 %. The boot reading pairs one voltage
  sample with the first 5 s window's current, taken in an unsettled boot state. That state is
  not logged.
- **It self-corrects at charge termination.** The charger stops at its termination current, the
  battery then rests within ±20 mA, and 0711 takes a new reading after 5 minutes.
- **Follow-up:** [0721](../../patches/proposals/0721-power-supply-mt6351-fuel-gauge-log-each-OCV-reading.patch)
  logs each OCV reading at debug level, first or after a rest: the corrected voltage, the window
  current, the temperature and the result.
  - To see it: the first reading comes about 5 s after probe, at the first capacity read, which
    is usually before userspace could turn the message on. So use the boot parameter
    `dyndbg="file mt6351-fuel-gauge.c +p"`.
  - Rest readings can also be turned on at runtime through
    `/sys/kernel/debug/dynamic_debug/control`.
  - Compiled at W=1 and checkpatch clean; not on a device.

**Charge voltage (charging session's area):**
- The vendor charges this high-voltage cell to 4.34 V between 10 and 45 °C
  (`HIGH_BATTERY_VOLTAGE_SUPPORT`, `JEITA_TEMP_POS_10_TO_POS_45_CV_VOLTAGE`); 4.24 V outside that
  range, 4.04 V below 0 °C.
- Station-work-103 still had the bq25896's 4.208 V default, about 87 % on the vendor-derived OCV
  table. That accounts for part of "Gemian reads higher" on that boot.
- **Since 0722-0724** (`f6c96bde`, on the device from station-work-104, the owner's choice), the
  guard sets 4.336 V at 10-45 °C and 4.240 V outside that range. REG06 read `0x7e` on boots
  `db80c436…` and `ea3bef10…`. A full charge now ends near the vendor's full.

**Time to full and to empty (owner request, 2026-11-11):**
- UPower's Linux backend (`src/linux/up-device-supply-battery.c`, upstream master) picks charge
  units only when the battery has `charge_full`.
  - It then reads `charge_full`, `charge_full_design`, `charge_now` and `current_now`.
  - It converts them to energy with `voltage_max_design` (4.352 V here).
  - From those it computes `time-to-full` while charging and `time-to-empty` otherwise.
    `power_now` is not read in charge units.
- Without `charge_full` or `energy_full` it uses energy units, finds no energy and reports 0 Wh
  with no time estimates. That is what station-work-105 showed.
- [0730](../../patches/proposals/0730-power-supply-mt6351-fuel-gauge-report-the-charge-now.patch)
  adds:
  - `charge_now`: the counted charge behind `capacity`, clamped to full;
  - `charge_full`: the design 4268 mAh. The real capacity is not learned.
- Compiled at W=1 and checkpatch clean; not on a device.
- **Limits:**
  - UPower's time to full counts up to 100 % of the design capacity. With the 4.336 V charge
    voltage that is close. A charge limit below 100 %, or charging outside 10-45 °C (4.240 V),
    makes the estimate run long.
  - The time to empty is only as good as 0711's starting point.
- **To verify:** `upower -i /org/freedesktop/UPower/devices/battery_battery` should show:
  - `energy` about `charge_now` × 4.352 V;
  - `energy-full` about 18.6 Wh;
  - `energy-rate` about |`current_now`| × 4.352 V;
  - a `time to full` line while charging, or `time to empty` unplugged, within a minute or two.

**0730 verified on station-work-107** (boot2 `9e73c047…`, main `c386b7e9`, boot `a1651d02…`;
charging from a computer port at 1.5 A):
- sysfs:
  - `capacity` 89;
  - `charge_now` 3798837 and `charge_full` 4268000, a ratio of 0.890 that matches `capacity`;
  - `current_now` +258 mA.
- UPower: `energy` 16.53 Wh, `energy-full` and `energy-full-design` 18.57 Wh, `energy-rate`
  0.80-1.02 W. By 87 s uptime it read `charging` with `time to full: 2.0 hours`, on the battery
  and on the display device. The owner sees the time in Noctalia.
- At 33 s, UPower briefly read `discharging` with `time to empty: 20.6 hours`, about 0.8 W.
  Likely ours (inference):
  - the first counter window runs from probe to the first read, so it includes boot time,
    when the system can draw on the battery before the guard's first pass enables charging;
  - UPower treats any negative `current_now` as discharging;
  - the next window was right.

  It is one reading after boot and is left as it is.

## Learned capacity (owner request)

The owner: "It shows 100% battery health, but I think that's wrong". UPower's health is
`energy-full` ÷ `energy-full-design`. With 0730, that is `charge_full` ÷ `charge_full_design`,
and 0730 reports the design value for both.

**How Linux handles it.** Gauges with their own firmware (bq27xxx, max17042) learn the full
charge and report `charge_full`. The kernel does not persist anything. Userspace reads the
value, and UPower shows the ratio. A host-side gauge like this one has to do the learning
itself and needs userspace to keep the result across boots.

**What the vendor did:**
- `fuelgauged`/`libfgauge.so` learn a Qmax from two OCV points and the counter between them.
- They log it as `MTK_FG: [FGADC_AQ] (FG1%, OCV1, CAR1, FG2%, OCV2, CAR2, Qmax_T_new_0mA, …,
  aging factor1 …)` and `[FGADC_UI_FG] … Qmax_T_0mAH` through `/dev/kmsg`, and pass it to the
  kernel with `SET_QMAX`.
- The binaries reference no file path and no property, so the learned value is not persisted.
  It is relearned each session.
- The kernel shows it read-only in `/sys/devices/platform/battery_meter/FG_g_fg_dbg_bat_qmax`,
  beside `FG_Aging_Factor` and `FG_Battery_Cycle`.

**Proposed learning, in the driver.** It reuses 0711's rest readings:
- **The event is a pair of rest OCV readings with counted charge between them.** Each reading
  needs 30 min within ±20 mA, not the 5 min used for counting, so the voltage has relaxed.
  The end of a full charge counts as such a reading once the battery has rested on the charger.
- **The estimate is** Q = ΔCAR ÷ (SoC₁ − SoC₂).
- **A pair is rejected if:**
  - the SoC difference is under 40 points (each OCV reading carries about ±2-3 points);
  - either reading is outside 15-35 °C, or the two differ by more than 10 °C;
  - more than 72 h separate them (counter drift);
  - the counter or the current window was invalid, or the boot changed between them (the
    counter resets at boot);
  - Q falls outside 50-110 % of the design capacity.
- **An accepted Q moves `charge_full` a quarter of the way** toward the new value, so one bad
  pair cannot swing it.
- `capacity` and `charge_now` are then counted against `charge_full`, not the design value.
- Each accepted or rejected pair is logged at debug level, as in 0721.

**When it happens in practice.** On battery the Gemini never rests: it draws at least
70 mA. So the low point needs the charger attached with charging held off.
- **Passive:** a battery held at the charge limit gives high points. A low point only comes
  from plugging in below the start threshold with charging held, which rarely happens on its
  own.
- **A deliberate calibration cycle, about one discharge:**
  1. Charge to full with the limit at 100. Leave it on the charger 30 min after it finishes.
  2. Unplug and use it down to about 20-30 %.
  3. Plug in with charging held: set the end threshold below the current level. Leave it
     30 min.
  4. Restore the limits.

  A small script can drive steps 1, 3 and 4 and say when a pair was accepted.

**Keeping it across boots** (owner decision):
- `charge_full` becomes writable in the driver, accepting 50-110 % of the design.
- A unit restores it at boot from `/var/lib/gemini/battery-charge-full`, and saves it at
  shutdown and whenever the driver reports a change.
- The unit belongs in the board package (gemini-base), installed by the Arch root work.
- No hardware write is involved: a sysfs attribute and a file.

**What UPower then shows:**
- Health: `capacity` = `charge_full` ÷ `charge_full_design`, for example 83 % after learning.
- The percentage is counted against the learned full charge.
- The time to full and to empty use that full charge.

**Reference value:** one read-only Gemian boot (`dmesg | grep FGADC_AQ\|FGADC_UI_FG`, the
`battery_meter` attributes above) gives the vendor's Qmax for this cell. It is a sanity check,
not a seed: its units and temperature basis are the vendor model's.

**Owner decisions (2026-11-11, through the custodian):**
- "Yes, build it": driver learning, a writable `charge_full`, and a gemini-base unit that keeps
  it.
- "Yes, build the helper": the calibration-cycle script.

**Driver side:** [0732](../../patches/proposals/0732-power-supply-mt6351-fuel-gauge-learn-the-full-charge.patch).
- Learning: as above.
  - A pair is taken at the first capacity read after 30 min at rest.
  - The first reading of a boot has no partner, because the counter resets at boot.
  - An accepted result is logged at info level (`full charge … uAh from … uAh over … points`)
    and raises a `power_supply` change event. Rejections are logged at debug level.
- `charge_full` is readable and writable.
  - A write outside 50-110 % of the 4268 mAh design gets `ERANGE`.
  - A write keeps the current capacity reading: the last OCV reading is rescaled.
- `capacity` and `charge_now` count against `charge_full`; `charge_full_design` stays 4268000.
- Compiled at W=1 and checkpatch clean. The pair arithmetic was checked by hand: 2.45 Ah over
  70 points gives 3.5 Ah, and the full charge moves from 4268 to 4076 mAh. Not on a device.

**Userspace side (arch-root, gemini-base):**
- **The unit:**
  - at boot, write the saved value to `/sys/class/power_supply/battery/charge_full`;
  - on a `power_supply` change event for `battery`, and at shutdown, save `charge_full` to
    `/var/lib/gemini/battery-charge-full`, only if it differs from `charge_full_design`, or a
    value was already saved.
- **The calibration helper:** it drives the cycle above through the guard's
  `charge_control_*` thresholds, which belong to the charging session (0695). It restores the
  thresholds it found, and reports `charge_full` before and after.
- **Built** in gemini-base 41 (`c7f2a0d1`), recorded in the
  [Arch root record](../2026-11-06-gemini-arch-root/README.md) under "Keeping the learned
  battery capacity".
  - The guard's end threshold cannot go below 50. The helper holds charging at the low point
    with end 50 and start 0, set once the battery is full, relying on the guard's full latch.
  - The low reading needs the charger to carry the whole system: on a 500 mA computer port, a
    lit screen can pull the battery current outside ±20 mA. A wall charger and an idle screen
    are safer.
  - Not on a device.

### T2: the image with 0710-0711 (next built-in batch)

- **Hypothesis:** `current_now` follows the counter and capacity no longer jumps on unplugging.
- **Procedure:**
  1. `echo 'module mt6351_fuel_gauge +p' > /sys/kernel/debug/dynamic_debug/control`, or
     `file mt6351-fuel-gauge.c +p` when built in.
  2. On USB with charging allowed, read the battery supply every 10 s for 2 minutes.
  3. Unplug, keep reading for 5 minutes with the screen lit, then plug back in.
  4. Save `dmesg` with the window lines.
- **Read only:** sysfs, dynamic debug. **Writes:** the dynamic-debug switch.
- **Expected:**
  - `current_now` negative and in hundreds of mA on battery;
  - `status` `Discharging` unplugged and `Charging` with current flowing in;
  - capacity changing by at most 2 points across the unplug, then falling steadily;
  - the debug lines show the counter against the register.
- **Decision:**
  - Capacity jumps by more than 5 points at the first reading: check the 165 mΩ resistance.
  - The current's sign is wrong: check the counter's sign.
  - With the charge limit active: after 5 minutes held at the limit, note the re-reading's
    change.
- **Stops:** an Oops or `WARNING` from the driver; the battery under 30 %; the charger guard
  reporting an error.

### Optional T3: Gemian comparison, only when a Gemian session is already needed

Read the same `0x0CA4`-`0x0CE6` range through the vendor PMIC sysfs access (read only), next to
a `[kernel]AvgVbat` log line. It shows which FGADC fields LK→Gemian and LK→mainline leave
differently.
