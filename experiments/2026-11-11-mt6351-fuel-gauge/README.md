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

## Opportunistic learning (owner request)

The owner: "our driver should learn when a charge/discharge cycle gives the opportunity".
0732 already learns from any pair of 30-minute rests. The gap is the low point: on battery the
Gemini draws at least 70 mA, so it never rests.

**What the vendor did:**
- The MT6351 samples the battery voltage itself when it wakes from sleep, before the system
  loads it: `AUXADC_ADC_OUT_WAKEUP_SWCHR`, read by `get_hw_ocv`.
- After a long suspend at a few mA, that is a rested OCV. The kernel tells the daemon with
  `IS_HW_OCV_UPDATE` and keeps `g_hw_ocv_before_sleep`.
- The daemon's aging thresholds are `AGING1_LOAD_SOC 70` and `AGING1_UPDATE_SOC 30`. By
  inference, the pair starts at or above 70 % and spans at least 30 points. The daemon's
  algorithm itself was not disassembled.
- So the vendor's natural rest points came from suspend.

**The sources, with expected accuracy per reading (inference):**

| Source | When it happens | Error per reading | Step toward Q |
|---|---|---|---|
| Rest of 30 min on the charger (0732) | held at the limit, or after charge termination | ±1-2 points | 1/4 |
| Charge termination at 4.336 V, then the 30 min rest | an overnight charge | ±1 point; the high end | 1/4 (already 0732) |
| (a) Load-corrected OCV, V − I × R, R ≈ 0.20 Ω, at a light steady load | screen off and idle on battery: steady 70-150 mA for 10 min, windows within ±10 mA of each other | ±3-4 points: about 0.05 Ω of R uncertainty × I, plus polarisation; worst in the flat 40-60 % region | 1/8; 1/16 if both readings are load-corrected |
| (b) A charging hold-off at plug-in, the battery idle on the charger | plug-in after a discharge | 10 min: ±3 points; 30 min: ±2 | 1/8 at 10 min, 1/4 at 30 |
| (c) The first reading after a long suspend, as the vendor did | once suspend draws a few mA | ±2 points | 1/4 |

**Driver rules (image items):**
- A pair still needs 40 points (50 when either reading is load-corrected), the same boot,
  72 h, 15-35 °C and 10 °C between the readings.
- The step toward Q is the smaller of the two readings' steps.
- Each accepted step is capped at 5 % of the design capacity, so ordinary use converges over a
  few cycles without a jump.
- (a): a reading is taken once per steady period, and only below 30 % or above 70 %, where
  the OCV curve is steep enough for a 10 mV error to stay within about 3 points.
- (c): needs a fresh 5 s current window after resume. The window spanning the suspend would
  correct the waking voltage with the sleep current. It waits on working low-current suspend:
  the measured 73 mA is not a rest.
- The counter's own gain error (CAR_TUNE, chip trim) is absorbed: the learned Q is in counter
  units, so the percentage stays consistent with the counter.

**A normal cycle with (a) and (b):**
1. Charge overnight: termination plus a 30 min rest gives the high point.
2. Through the day, an idle stretch below 30 % gives (a), or plugging in at the end of the day
   with a hold-off gives (b).
3. The pair is accepted with a 1/8 step.

Without a reboot in between, a few such days bring `charge_full` within about 5 %.

**Owner decisions:**
- (b) needs a guard change, the charging session's: hold charging off for 10 or 30 minutes at
  plug-in. Only below some level (for example 40 %), only at 15-35 °C, and skipped when the
  owner wants a fast charge. It delays every such charge by that long.
- Whether (a) is enough on its own: no charging change, slower convergence.
- (c) waits on suspend.

**Owner decision (2026-11-11, through the custodian):** "Light use only": (a) plus the
existing rest and overnight-charge readings. (b) is declined, with no charging change. (c)
waits for suspend.

**Built:** [0734](../../patches/proposals/0734-power-supply-mt6351-fuel-gauge-learn-from-light-stea.patch),
on top of 0732.
- **The steady reading:**
  - a steady period starts at a window discharging 70-150 mA, and ends at any window outside
    that range or more than 10 mA from the first;
  - after 10 minutes, one reading is taken: V − I × R in the OCV table, used only below 30 % or
    above 70 %.
- **Spans and steps:**
  - a pair including such a reading needs 50 points and steps 1/8 of the gap;
  - two such readings step 1/16;
  - rest pairs keep 40 points and 1/4.
- **Every step is capped at 5 % of the design** (213 mAh).
- **The log line** gains the step: `full charge … uAh from … uAh over … points, step 1/N`.
  Steady readings are logged at debug level (`steady reading: …`).
- **Convergence, checked by hand:**
  - a 1/8 step closes 12.5 % of the remaining gap, so light-use pairs alone take about 15
    pairs to bring an 18 % error within 5 %;
  - a 30-minute rest pair (1/4) closes a quarter;
  - the first light-use pair against a 3.5 Ah cell moves 4268 to 4172 mAh.
- Compiled at W=1 and checkpatch clean; not on a device.

## Capacity falling while charging (station-work-107, boot `a1651d02…`)

**Observed by the owner:**
- The guard's boot line read `capacity=89`.
- About 50 minutes into charging from a computer's charging port (1.5 A input), it read 85 %,
  `Charging`, +191 mA, 4.335 V (the 4.336 V constant-voltage setpoint), 24.6 °C.
- UPower showed 0.85 W and 3.2 h to full.

**Reading:**
- **Not the counter.** `current_now` is the counter's own change, and it was positive.
- **The 89 % came before the first current window,** from the old voltage reading, which the
  charging current raises.
- **0711's starting point came from the first window.** That window opens at probe and spans
  boot, when the battery carries the load (the brief `discharging` UPower showed at 33 s on
  the same boot). It came out low, and the counted charge since had climbed back to 85.
- **In the taper,** 4.335 V less 191 mA × 0.165 Ω is 4.303 V, 95 % on the table. So the start
  was about 10 points low, as on station-work-103.

**Fix:** [0735](../../patches/proposals/0735-power-supply-mt6351-fuel-gauge-correct-the-capacity-.patch),
on top of 0734.
- It drops the first window.
- While charging at up to 300 mA within 40 mV of the 4.352 V design maximum, which is the
  charger's taper, it takes a new OCV reading, V − I × R, at most every 5 minutes. On these
  numbers it would read 95 %.
- Readings are logged at debug level (`taper OCV reading: …`). They feed the count, not the
  learning.
- Compiled at W=1 and checkpatch clean; not on a device.
- Outside 10-45 °C the charger stops at 4.240 V, below the 4.312 V threshold, so no taper
  reading is taken. The rest after termination still corrects.

**Follow-up on the same boot** (private log `artifacts/card-32/cv-taper-10min.txt`):
- Sampling started at 3003 s, after the charger had already terminated:
  - `status` `Not charging`, 4.263 V, current about 0, capacity 85.
- At 3243 s the 5-minute rest reading moved capacity from 85 to 92 % and `charge_now` from
  3642 to 3927 mAh. That is 4.263 V on the table, 92 %. No fault.

**What it shows: a completed charge rests at about 92 % on the table, not 100 %.**
- The charger stops at 4.336 V with its termination current still flowing (the bq25896
  default, 256 mA), and the cell then relaxes.
- The vendor-derived table puts 100 % at 4.357 V, which this charge never reaches.
- The vendor reported 100 % at termination because its UI SOC is scaled: `Full` when
  `UI_SOC2` is 100 with a charger. So "Gemian reads higher" is also a difference of scale.
- 0735's taper reading (about 95 %, V − I × R, which ignores the charging overpotential) will
  be followed by the rest reading (about 92 %). So a 2-3 point drop just after a charge is
  expected. V12's 3-point tolerance covers it.

**Owner decision: what 100 % means.**
1. **Table-true:** keep it as it is. A full charge reads about 92-94 %, and `charge_full` (the
   learned Q) is the cell's whole table capacity.
2. **Charger-full is 100 %, as the vendor did:**
   - each rest reading after a termination records the table capacity there (about 92);
   - the driver reports capacity scaled so that value is 100;
   - `charge_full` becomes the usable charge, Q × that share, so health, time to full and time
     to empty are on the same scale;
   - learning stays on the table scale.

   This is a driver change, an image item.

Option 2 is recommended (inference): a phone that never shows 100 % after charging looks broken,
and the usable charge is what the time estimates should use.

**Owner decision (2026-11-11, through the custodian):** "Charger finished = 100 %".

**Built:** [0736](../../patches/proposals/0736-power-supply-mt6351-fuel-gauge-report-a-finished-cha.patch),
on top of 0735.
- **Scale:** `capacity`, `charge_now`, `charge_full` and `charge_full_design` are reported
  against the usable charge, a fixed 93 % of the table's. That is the measured 92 % rest after
  termination, with a point of margin.
- **Why it is fixed rather than learned per boot:** a saved and restored `charge_full` must mean
  the same on every boot. A scale learned per boot would make the value drift by about 1 % per
  boot.
- **A finished charge:**
  - a 5-minute rest on the charger after a taper reading (0735) counts from 100 % of the usable
    charge, and the OCV re-readings are held off for the rest of that rest;
  - a discharge clears the taper mark.
- **Learning is unchanged,** on the table scale. `charge_full` written by userspace is in usable
  units: the accepted range becomes 1984620-4366164 µAh.
- **At design capacity:**
  - the usable charge is 3969 mAh;
  - a plain rest at 92 % on the table shows 99 %;
  - a taper reading of 95 % shows 100 %;
  - health is `charge_full` ÷ `charge_full_design`, still the learned share of the design.
- **The guard** (0695) compares its limits with this capacity. An 80 % limit now stops at
  about 74 % of the table, the same 80 % the owner sees. The charging session confirmed it reads
  only `capacity`.
  - Its 5-point resume band is now 5 displayed points, about 4.65 table points.
  - With the limit at 80, charging ends about 6 table points lower than before.
- Compiled at W=1 and checkpatch clean; not on a device.

## Station-work-108 (0732, 0734, 0735), boot `940593bc…`

From the custodian. Charging from a computer's charging port at 1.5 A, limit 100.
- **V1 pass:**
  - `charge_full` 4268000, equal to the design;
  - `capacity` 94, with `charge_now` 4015690, a ratio of 0.941;
  - UPower health 100 %, 1.3 h to full.
  - The boot reading was 94, where station-work-107 started at 85. That supports 0735's
    dropping of the boot window.
- **V2 pass:** `charge_full` is `-rw-r--r--`.
- **V3 pass:**
  - 3800000 was accepted. `capacity` stayed 94, `charge_now` rescaled to 3576513, and UPower
    showed 16.54 Wh and 89.0 % health within 50 s.
  - 1000000 gave `ERANGE` and left 3800000.
  - 4268000 restored it.
- **V4 pass:** no warning or Oops; the kernel is not tainted.
- **V10 pass:** no early `discharging` with the charger online from boot.
- **Pending:** V5-V9 and V11-V13, which need a cycle, a steady light-use period or a charge
  from below 80 %.
- **Test residue:**
  - V3's writes made gemini-base save `/var/lib/gemini/battery-charge-full` = 4268000, the
    design value on 0732's table scale.
  - Under 0736 that would be restored as a usable charge, so capacity would read about 7 % low.
  - **Fix, in gemini-base** (asked of the Arch root session; the custodian holds the 0736 image
    until it lands):
    - save `<charge_full> <charge_full_design>` together;
    - restore value × current design ÷ saved design;
    - treat a legacy single-integer file as saved against 4268000, since only 0732 wrote that
      format.
  - This is exact across 0732, 0736 and later scales. The legacy 4268000 restores as 3969240
    (100 % health), and a 0732-learned 3500000 as 3255000.

## Values stay within 0-100 % (owner requirement)

The owner: "Values must be consistent and should never be above 100% or below 0%".
[0737](../../patches/proposals/0737-power-supply-mt6351-fuel-gauge-keep-the-full-charge-.patch),
on top of 0736, keeps the full charge at or below the design:
- A learning pair may still estimate up to 110 % (noise), and a write still needs 50-110 %, so
  a saved value from another scale is not refused outright. Either is then held at the design.
- With 0711-0736 already clamping `capacity` to 0-100 and `charge_now` to 0-`charge_full`,
  every value now holds:

  | Value | Range |
  |---|---|
  | `capacity` | 0-100 |
  | `charge_now` | 0 to `charge_full` |
  | `charge_full` | at most `charge_full_design` |
  | health in UPower | at most 100 % |

- `capacity` is computed against the same `charge_full` that is reported.
- Card-32's saved 4268000 converts to 3969240 under gemini-base 47. Any higher value from
  another card or scale is now held at the design, or refused if above 110 %.
- Compiled at W=1 and checkpatch clean; not on a device.

## Station-work-109 (0736, 0737, gemini-base 47), boot `359475be…`

From the custodian. Charging from a computer's charging port at 1.5 A, limit 100.
- **V14/V21 pass:**
  - `charge_full` = `charge_full_design` = `charge_now` = 3969240, `capacity` 100, UPower
    health 100 %;
  - the legacy file (4268000) converted, and now reads `3969240 3969240`.
- **V19 pass:** 4200000 reads back as 3969240.
- **V20 pass:** 5000000 gives `ERANGE` and changes nothing.
- **V17 pass:** 3800000 reads back 3799999 and UPower shows 95.7 % health; 1900000 gives
  `ERANGE`; the restore to 3969240 was saved.
- **No warning or Oops;** the kernel is not tainted.
- **Pending:** V15, V16, V18 and V22, which need a charge to the end, an unplug or the 80 %
  limit.
- **Known:** the write converts to the table scale rounding down, so a value that is saved and
  restored loses 1 µAh per boot (3800000 → 3799999). That is negligible. A round-up in
  `set_property` would make it exact, and is left for the next driver change.

## The cell's resistance is about 0.4 Ω, not 0.165 Ω (station-work-110, boot `0ce7590c…`)

**The data:**
- During the calibration discharge, unplugged with a browser keeping about four cores busy.
- Five samples 30 s apart (private `artifacts/card-32/gauge-stuck-sample.txt`):
  - `capacity` 98 → 96;
  - `charge_now` falling 14.6 mAh per 30 s, about 1.75 A, matching `current_now`;
  - 3.48-3.55 V.
- The count started from this boot's "charge finished" point, so the charge is the most
  trustworthy value available.

**Effective resistance:** at the counted charge (89.3-90.7 % of the table), the table's OCV is
4.237-4.246 V.

| Table % | OCV | V | I | (OCV − V) ÷ I |
|---|---|---|---|---|
| 90.7 | 4.246 | 3.546 | 1.79 A | 0.390 Ω |
| 90.4 | 4.244 | 3.522 | 1.66 A | 0.435 Ω |
| 90.0 | 4.242 | 3.477 | 1.79 A | 0.427 Ω |
| 89.7 | 4.239 | 3.520 | 1.77 A | 0.405 Ω |
| 89.3 | 4.237 | 3.552 | 1.73 A | 0.396 Ω |

- About 0.40 Ω under a sustained load. That includes the polarisation that builds over minutes
  and the whole path, not only the cell's ohmic part.
- The DT's 165 mΩ (0372) is the vendor profile's new-cell mid-range 90 mΩ plus the 75 mΩ meter
  path. This cell is the original one.
- The earlier 0.20 Ω fit (`d41819cc…`) paired voltages and currents read 2 s apart over a narrow
  current range. It is superseded.

**What a low R explains (inference):**
- **The first reading under boot load comes out low.** At 0.5 A, 0.24 Ω missing is about
  120 mV, about 10 points in the mid-range. That matches station-work-103 and -107.
- **Card-31's 2-15 % at about 1 A.**
- **Taper readings (0735) come out high.** At 191 mA, about 45 mV, which the clamp at 100 hides.
- **0734's light-load readings are biased low**, about 25 mV at 100 mA. So the learned capacity
  would come out a few percent low. Rest pairs are unaffected, since the current is near zero.

**Brownout under load (inference):** at 1.8 A and 0.4 Ω the terminal sits about 0.7 V below the
OCV. A cell at an OCV of 3.75 V (about 20 %) would read about 3.0 V under that load. A heavy
load at a low charge can therefore drop the system before 0 %. This bears on UPower's critical
action level, which belongs to arch-root.

**Next:**
1. **Measure (T5, read-only).** At about 60 %, unplugged, alternate an idle minute (screen
   blanked) and a loaded minute (the browser), three times. Read `voltage_now` and
   `current_now` every 5 s.
   - The step at each change gives the fast resistance.
   - The end of each minute gives the one-minute value.
   - With today's sustained figure, that fixes the value to use.
2. **Fix (DT, image):** set `factory-internal-resistance-micro-ohms` in 0372's battery node
   from T5.
   - It is one value for every use. The steady readings (0734, 10 min at 70-150 mA) and the
     boot reading are closest to the one-minute-to-sustained figure.
   - The vendor's per-temperature resistance profiles could scale it later.
3. **Learning R in the driver** is possible: each steady period at a counted charge gives
   (OCV − V) ÷ I. It is not proposed until a fixed measured value shows its limits.

**Voltage backstop (owner-approved, gemini-base, built by arch-root):**
- **The rule:** power off cleanly after 3 consecutive 10 s reads below a threshold while
  discharging. The threshold given is **3.00 V**, refined after T5.
- **The hardware cut-off:**
  - The MT6351's UVLO switches the board off when VSYS falls below `RG_UVLO_VTHL` (`CHR_CON17`
    `0x0F9A` bits 4:0, 2.50 V + 50 mV per step).
  - The vendor kernel sets 2.60 V (`POWER_UVLO_VOLT_LEVEL 2600`). Mainline does not write it;
    T5 reads it.
- **What the vendor did in software:** DLPT shuts down at 3.1 V
  (`SHUTDOWN_SYSTEM_VOLTAGE 3100`), after throttling the CPUs, which mainline does not do.
  `V_0PERCENT_TRACKING` is 3.45 V.
- **Margins:**
  - bursts between polls, about 1 A at a fast-step R of about 0.25 Ω (pending T5), go about
    0.25 V below the polled value;
  - VSYS sits about 0.05 V under the battery through the BATFET;
  - a polled 2.90 V could therefore touch 2.60 V. 3.00 V leaves 0.1 V, and is the usual Li-ion
    discharge cut-off.
- **Why not 3.30 V:** at 1.8 A and 0.4 Ω, 3.30 V loaded is an OCV of about 4.02 V, about 70 %.
- **In use:** 3.00 V trips around 15-20 % under a 1.8 A load. At 0.5 A or less it would need an
  OCV under 3.2 V, below the table's empty point, so the gauge's levels act first.

## Adaptive resistance and capacity to the cut-off (owner direction)

The owner: "This sounds very specific to this battery... what will happen with the same setting
on other devices? I'd like this to be more adaptive". So instead of a measured value for this
unit:
- the driver learns R;
- the capacity runs to the voltage cut-off under the learned R;
- the backstop is a device constant.

The DT keeps only the new-cell starting value.

**New facts:**
- **LK sets the hardware cut-off to 2.70 V on this unit.** `CHR_CON17` `0x0F9A` read `0x0004`, so
  `RG_UVLO_VTHL` = 4, 2.50 V + 4 × 50 mV. Mainline does not change it; the vendor kernel set
  2.60 V.
- **The vendor's resistance profiles** (`r_profile_t0`-`t3`, at −10/0/25/50 °C) have a mid-range
  median (3.7-3.9 V) of 1006, 567, 92 and 51 mΩ. Relative to 25 °C that is about ×11, ×6.2,
  ×1 and ×0.55.

### 1. Learning R

**Two estimates,** both only while discharging on battery, at 15-35 °C, normalised to 25 °C with
the vendor profile's ratio (log-interpolated between its four temperatures):

| Estimate | From | Rule | Used for |
|---|---|---|---|
| Sustained, R_eff | a steady load of at least 300 mA for 2 min (windows within 10 % of each other), with the charge counted from a reading of the last 24 h | (OCV(counted charge) − V) ÷ \|I\| | OCV corrections and the 0 % point |
| Fast, R_fast | two consecutive 5 s windows with a current change of at least 300 mA, with the voltage sampled at each window's close | ΔV ÷ ΔI | the margin against bursts |

**Bounds and steps:**
- accepted between 50 mΩ and 1.5 Ω;
- each update moves 1/16 of the way, capped at ±10 %, at most once per 10 minutes;
- debug log for each estimate, info log for each update.

**Starting value:** the DT's 165 mΩ, which stays a new-cell value. This unit should converge
toward about 0.4 Ω (R_eff) over a few days of use. T5 validates both estimates.

### 2. Capacity to the cut-off

- **0 % is the charge at which the cell, under its typical recent load, reaches the cut-off.**
  - The typical load I_typ is a slow average of the discharge current, with a 30-minute time
    constant, bounded 0.2-2 A, starting at 0.5 A.
  - The empty point SoC₀ (on the table) is where OCV(SoC₀) − I_typ × R_eff(T) = V_cut.
  - V_cut = the backstop + 0.10 V, so the gauge reaches 0 % before the backstop acts.
- **The scale:**

  | Value | Definition |
  |---|---|
  | `capacity` | (table SoC − SoC₀) ÷ (93 % − SoC₀), clamped 0-100 |
  | `charge_now` | Q × (table SoC − SoC₀) |
  | `charge_full` | Q × (93 % − SoC₀) |
  | `charge_full_design` | Q_design × (93 % − SoC₀ for a new cell at 0.5 A and 25 °C) |

  - Health is `charge_full` ÷ `charge_full_design`, clamped to 100. It now includes the
    resistance ageing, as Impedance Track's full charge does.
  - Capacity is always `charge_now` ÷ `charge_full`.
- **No jumps:** SoC₀ moves at most one point per 5 minutes. The cold-temperature rise in R
  shrinks the usable charge gradually and visibly.
- **Example, this cell at 25 °C:**
  - at 0.5 A and 0.4 Ω, SoC₀ is where OCV = 3.20 + 0.20 = 3.40 V, the table's 0 %. So
    light use loses nothing.
  - under sustained 1.8 A browsing, OCV = 3.20 + 0.72 = 3.92 V, about 57 % of the table. The
    display then tells the truth: at that load the cell has only that much left above the
    cut-off.

### 3. Persistence

- `charge_full` becomes derived and read-only.
- **Two new driver attributes,** read-write, under the battery's device:
  - `learned_full_uah`, Q on the table scale;
  - `learned_resistance_uohm`, R_eff at 25 °C.
- **gemini-base saves** `<value> <basis>` for each, the basis being the DT's design value
  (4268000) and starting R (165000), and rescales on restore.
- **Migration:** the existing file's `charge_full charge_full_design` converts as Q =
  value × 4268000 ÷ design_saved.

### 4. Backstop: a device constant, **3.10 V**

- **What it covers:**
  - the cut-off: UVLO 2.70 V (LK);
  - bursts between polls: up to 1 A at an aged cell's fast R of up to 0.25 Ω, 0.25 V;
  - the BATFET drop: 0.05 V;
  - a margin: 0.10 V.
- **Same on every Gemini,** since LK is the same. T5's fast R confirms the burst figure.
- **Why not 3.00 V:** the 3.00 V given earlier assumed the vendor's 2.60 V UVLO.

### Owner decisions (2026-11-11, through the custodian)

- (a) "Yes, build it". (b) "Load-aware": the percentage falls faster under heavy use, gives
  some back when the load lightens, and 0 % means about to shut down.

### Built

**[0745](../../patches/proposals/0745-power-supply-mt6351-fuel-gauge-learn-the-cell-s-resi.patch),
the learned resistance:**
- **R_eff** comes from a steady discharge of at least 300 mA for 2 min, windows within a tenth
  of the first.
  - It is only taken within 24 h of a rest or finished-charge reading, so the counted charge it
    compares against does not itself come from a loaded reading.
  - 15-35 °C, normalised to 25 °C by the vendor profiles' log-interpolated factor in 5 °C steps.
  - 1/16 steps capped at a tenth, once per 10 min, bounded 50 mΩ-1.5 Ω. The DT's 165 mΩ is the
    start.
- **Every I × R correction** (first, rest, taper, steady and learning readings) uses R(T).
- **The fast step estimate** between windows is logged at debug level (`step resistance: …`)
  for T5. It drives nothing, because the backstop is a fixed constant.
- **Attributes** under the battery's device: `learned_resistance_uohm`, read-write within the
  bounds, and `design_resistance_uohm`, the basis.
- A change raises a `power_supply` event.

**[0746](../../patches/proposals/0746-power-supply-mt6351-fuel-gauge-count-the-capacity-do.patch),
capacity to the cut-off:**
- **Empty** is where OCV − I_typ × R(T) = 3.20 V.
  - I_typ is a time-weighted 30-min average of discharge, held on the charger, bounded
    0.2-2 A, starting at 0.5 A.
  - Empty moves a point a minute at most, and stops at 80 % of the table.
- **Derived values:** `capacity`, `charge_now` and `charge_full` are the usable charge above
  empty. `charge_full_design` is a new cell's at 0.5 A and 25 °C, and `charge_full` is capped
  there.
- **Interface:** `charge_full` is read-only again. The table Q is in `learned_full_uah`,
  read-write within 50-110 % held at the design, and `design_full_uah` is the basis.
- **Simulated on this cell** (R₂₅ 0.40 Ω, 25 °C, Q unlearned):

  | Load | Empty point (table) | Health | 90 % of the table shows | 60 % shows |
  |---|---|---|---|---|
  | 0.5 A | 0 % | 100 % | 97 % | 65 % |
  | 1.0 A | 2 % | 98 % | 97 % | 64 % |
  | 1.8 A sustained | 58 % | 38 % | 91 % | 6 % |

  A new cell at 1.8 A empties at 1 %. **Health therefore depends on load:** under a sustained
  heavy load it shows what this cell offers against a new one at that load. Owner to note.

Both compiled at W=1 and checkpatch clean, applied in sequence after 0737. Not on a device.

**gemini-base change (Arch root):**
- save `learned_full_uah design_full_uah` and `learned_resistance_uohm design_resistance_uohm`;
- restore each as value × basis now ÷ saved basis;
- migrate today's file `charge_full charge_full_design` (usable units, or a legacy single
  number) as Q = value × 4268000 ÷ the saved design, the legacy basis being 4268000.

### Owner decisions (as proposed)

- Build 1-4 as described, as an image item plus a gemini-base change?
- With part 2, the displayed charge depends on recent load. Heavy use makes the percentage drop
  faster, and it recovers partly when the load lightens, as phones with Impedance Track do. Is
  that wanted, or should 0 % stay fixed at the table's empty point under a light load, with
  only the backstop handling heavy load?

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
