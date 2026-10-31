# Gemini charging

Scope: how the named MT6797X Gemini charges, from the bootloader through the
kernel state machine, including the thermal gates on charge current. This is a
source, datasheet and firmware study; no runtime measurement is claimed.

Evidence lives in two records: the
[2026-10-04 charging reverse engineering](../../experiments/2026-10-04-gemini-charging-re/README.md)
(charger identity, register configuration, per-cable current table, fuel gauge,
mainline gap) and the
[2026-10-31 charging chain](../../experiments/2026-10-31-gemini-charging-chain/README.md)
(boot chain, state machine, thermal gates, datasheet limits).

## 1. Topology

| Element | Part / interface | Role |
| --- | --- | --- |
| Switch charger | TI BQ25896 at I2C0 `0x6b` (live DTB node `mediatek,sw_charger`) | Charges the cell, input current limit, VBUS/OTG |
| Charger type detection | MT6351 BC1.1 block (`CHR_CON20`) | SDP/CDP/DCP/non-standard/Apple classification |
| Cable presence | MT6351 `CHRDET` comparator, PMIC EINT176 | "Charger exists", not the charger's PG pin |
| Charger voltage | MT6351 AUXADC channel 2 (`VCDT`), 330 k/39 k divider | VBUS measurement and over-voltage |
| Battery temperature | MT6351 AUXADC channel 3 (`BATON`), 24 k pull-up to VBIF28 | Charge temperature gate and fuel-gauge temperature |
| Fuel gauge | MT6351 FGADC coulomb counter + AUXADC | SOC, current, OCV/ZCV |

The public board DTS does not describe the live charger node; the live DTB
does, and its values are authoritative for the unit.

## 2. Boot chain

**Preloader.** Runs BC1.2 detection, checks VBAT and VCHR and prints the
battery decisions, but no BQ25896 code or strings were found in the retained
image. Until LK starts, the
charger therefore runs on its power-on defaults: 2.048 A charge current,
4.208 V regulation, 128 mA pre-charge, termination enabled, 12 h safety timer,
watchdog expired (default mode). This matches the default register values seen
when no kernel driver is bound.

**LK.** Initialises the charger explicitly: watchdog reset, OTG off, safety
timer on, 128 mA pre-charge and termination, `VREG` 4.352 V, VBAT clamp +224 mV,
80 mΩ IR compensation, 3.0 V pre-charge-to-fast threshold, 2048 mA charge
current, 3.25 A input limit, absolute 4.5 V VINDPM. It then runs the same BC1.2
sequence through the MT6351 and applies a type-dependent input limit (vendor
comments: 2 A for a standard charger with the large-current flag, 1.2 A
otherwise, 500 mA for host/non-standard), enables charging, and enforces the
low-battery boot policy: wait until VBAT reaches 3450 mV, power off below
3200 mV without a charger, reject charger voltage above 6500 mV, require
battery presence through `BATON`, and power off if eight consecutive polls show
under 100 mA at under 4.4 V.

**Kernel.** Takes over with the state machine below.

**Observed at a mainline handoff** (station 11, boot `b4cde2f8…`; plain
SMBus reads and the
[S3b test](../../experiments/2026-10-31-gemini-thermal-protection/README.md)):
- **Charging is disabled at handoff.** REG03 read `0x0a` (`CHG_CONFIG`
  clear) and REG0B `0x26` (not charging) at every read from 16 to 39 s of
  uptime.
- **The watchdog then restores the defaults:** at 41 s REG03 read `0x1a`
  and REG0B `0x36` (fast). No mainline code had written the charger. That
  is the 40 s I2C watchdog expiring, and it ends whatever LK programmed.
- **The settings after that** are the power-on defaults, as read on
  station 9:
  - REG04 `0x20`, 2048 mA;
  - REG06 `0x5e`, 4.208 V;
  - REG07 `0x9d`, termination on and a 12 h timer;
  - REG00 `0x48`, a 500 mA input limit with the computer and the owner's
    fast charger both classified SDP.
- **Inference:** a step before the kernel leaves `CHG_CONFIG` off, against
  the "enables charging" reading of the LK source above. This was seen on
  a boot2 mainline handoff only; whether a Gemian boot sees the same is
  not established, and the Gemian kernel would rewrite it anyway.
- **What it explains:** the `no`-then-`fast` pattern seen on every mainline
  boot.

## 3. Kernel charging algorithm

`mt_battery_charging_algorithm()` runs every battery-task period and performs,
in order: kick the BQ25896 40 s I2C watchdog; run the input-current-limit
algorithm (AICL) unless PE+ is connected; run the PE+ state check; dispatch the
charge state; dump registers.

| State | Behaviour | Transition |
| --- | --- | --- |
| `CHR_PRE` | Charger on, pre-charge timer | SOC 100 and full check → full; above `V_PRE2CC_THRES` → CC |
| `CHR_CC` | Charger on, CC timer | full check → full |
| `CHR_BATFULL` | LED off, timers reset, CV re-selected | full check false → recharge (CC) |
| `CHR_HOLD` | Charger off during a call | call idle or voltage below talking-recharge → CC |
| `CHR_ERROR` | Charger off, PE+ reset | error clears → pre-charge |

PE+ 1.0 starts in pre-charge: 5 → 7 V (three retries, ±1 V tolerance) → 9 V;
12 V is compiled out (`TA_12V_SUPPORT` commented out, no DT property), and the
exit restores the adapter voltage. PE+ raises the permitted charge and input
currents.

"Full" is decided from the charger's own `CHRG_STAT`: six consecutive
"termination done" readings (60 s at the 10 s tick) plus an SOC-100 path in the
battery task. Hardware termination is enabled (see §6).

## 4. Current and voltage policy

- Per-cable charge currents come from the board DT: SDP 500 mA (70 mA
  unconfigured), CDP 650 mA, DCP/AC 800 mA (2050 mA header default),
  non-standard 500 mA, Apple 0.5/1.0/2.1 A → 500/650/800 mA. Requests are
  rounded down to the chip's 64 mA (charge) and 50 mA (input) steps, so 800 mA
  becomes 768 mA and 650 mA becomes 640 mA.
- The AC **input** limit is separate: the DT omits `ac_charger_input_current`,
  so the header default **3200 mA** applies for a DCP even though the charge
  current is 768 mA. SDP/CDP/non-standard use the same value for both.
- Voltage regulation is nominally 4.352 V with IR compensation; the vendor
  policy enum also carries a 4.34 V class, and `charging_set_cv_voltage()`
  computes the correct code but then writes a fixed `0x24` that decodes to
  4.416 V, which does not match the live 4.336 V readback. The CV value is
  therefore not a safe source for a mainline `ti,battery-regulation-voltage`;
  treat the cell as a 4.35 V-class part and start any mainline test at 4.2 V.
- Input voltage protection is absolute 4.5 V VINDPM plus the PMIC `VCDT` high
  threshold; outside PE+ the charger voltage ceiling is 6500 mV.

## 5. Thermal gates

Three independent mechanisms can reduce or stop charging; only one lives in
the charger hardware.

1. **Battery NTC window.** `T ≥ 50 °C` fails the charge check; charging resumes
   below 47 °C (pre-charge). The low-temperature gate exists but is disabled in
   the retained DT (`bat_low_temp_protect_enable = 0`), and the error
   temperature is 255 (disabled), so a missing NTC does not stop charging.
2. **PCB-temperature limiter.** With the backlight on, the board NTC
   (`mtktsAP`) computes a charge-current cap: below 42 °C none, 42-44 °C
   1500 mA, 44-45 °C 1350 mA, above 45 °C 1300 mA (lower with PE+ or VBUS above
   6 V). In this build the cap is **ineffective**: it runs inside
   `pchr_turn_on_charging()` *after* `mtk_select_ichg_aicr()` has already
   recomputed the currents from the cable type and written REG00/REG04, and it
   only modifies the in-memory values with no second write. The next tick
   recomputes them again. The function also has a duplicated 44 °C branch
   (level 2 unreachable) and an unhandled level 4.
3. **Thermal-zone coolers.** The Android `.tp` policy drives staged charge
   current from 46 °C on the battery zone (`mtk-cl-bcct00/01/02`), plus adaptive
   charge current at 47 °C and an LCD-off variant at 56 °C on the board zone.
   This is the path that actually reaches REG04, through
   `set_bat_charging_current_limit()` → `select_charging_current_bcct()`.

The BQ25896's own JEITA is configured by the vendor but the board's TS input
reads as a fixed divider, so hardware JEITA does not trip; the software gates
above are the effective protection. This makes the battery, not the SoC, the
thermally constrained subsystem.

## 6. Termination and recharge

- Hardware termination is **enabled**. `charging_sw_init()` writes
  `CON7 bit7 = 1` with the comment "disable ICHG termination detect"; the
  comment is wrong, since bit 7 is `EN_TERM`. The chip therefore terminates at
  the programmed 128 mA, and the policy confirms "full" with six consecutive
  `REG0B CHRG_STAT == 3` readings (60 s at the 10 s tick), plus an
  SOC 100 + charger-present path in the battery task.
- The software recharge constants (`v_cc2topoff_thres` 4050 mV,
  `recharging_voltage` 4110 mV) are parsed by the HAFG_20 battery path but not
  used; recharge is the chip's own `VREG − 100 mV` (`VRECHG = 0`).
- The BQ25896 safety timer is 12 h in fast charge (4 h below `VBATLOWV`),
  counting at half rate while in input or thermal regulation; expiry reports
  `CHRG_FAULT = 11`.

## 7. Safety and failure paths

- Watchdog: 40 s; kicked every battery period by the kernel and reset by LK.
- VBUS over-voltage: PMIC `VCDT` high comparator, plus LK's 6500 mV limit.
- Battery presence: `BATON` detection in LK, gauge in the kernel.
- A vendor `BATFET_DIS` workaround cuts the battery FET for the RT5735 SDA-low
  fault (recovery hook, not a charging feature).
- Charger-not-delivering rule in LK: under 100 mA at under 4.4 V for eight
  polls powers the unit off.

## 8. Mainline position

**On the development station (2026-10-31):**
- the battery NTC reads through the MT6351 AUXADC (0357-0360) and
  `power-status`;
- `charge-guard` implements gate 1, the 50/47 °C window, by REG03
  `CHG_CONFIG` with watchdog kicks while stopped. It runs at boot.
- `charge-guard` also stops charging at a capacity limit from the fuel
  gauge, 80 % by default and set in `/run/station/charge-limit`, resuming
  5 points lower
  ([fuel-gauge record](../../experiments/2026-10-31-gemini-fuel-gauge/README.md)).
  This is a longevity policy, not a safety stop.

Gates 2 and 3 are not implemented. The 500 mA SDP input limit bounds the
current meanwhile.


Upstream `bq25890_charger` matches the silicon and most of the vendor register
configuration, but mainline has no MT6351 ADC, gauge, BC1.1, charger-detect or
board-NTC consumer, and the current Gemini DT has no charger, gauge, host
AUXADC or VBUS nodes. Reproducing only the register configuration would omit
the NTC window, the PCB limiter and the `.tp` gates; reproducing only a generic
driver would omit charge-enable policy and the BC1.1 result entirely.

## 9. Open questions

1. The live CV value and the correct cell voltage class (4.34/4.35/4.416 V).
2. Whether the BQ25896 TS input is a fixed divider on every Gemini variant.
3. Which `.tp` policy a SKU selects, and the exact `clbcct` parameter mapping.
4. The preloader's exact thresholds and whether it writes any PMIC charger
   register before LK.
5. Which boot stage leaves `CHG_CONFIG` clear at a mainline handoff
   (§2, observed), against LK's charge enable.

## Evidence index

- Vendor kernel commit `8cfe6596a503612e3332d9c26e292a19525a7f07`;
  `switch_charging.c`, `battery_common_fg_20.c`, `mtk_pep_intf.c`,
  `power/mt6797/{bq25890.c,charging_hw_bq25890.c,pmic_chr_type_det.c}`.
- LK commit `f4988d74bb70a0a15d7f362f412afba7e7fcda46`;
  `platform/mt6797/{bq25890.c,mt_battery.c}`.
- TI BQ25896 datasheet (SLUSC76C), MT6351 PMIC datasheet.
- Retained private preloader and charger register captures; redistribution
  status in the [firmware boundary](firmware.md).
- [2026-10-04 charging record](../../experiments/2026-10-04-gemini-charging-re/README.md),
  [2026-10-31 charging chain](../../experiments/2026-10-31-gemini-charging-chain/README.md).
