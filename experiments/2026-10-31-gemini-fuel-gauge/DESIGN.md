# Battery gauge event and polling design

Status: **proposal**, not implemented. The current mainline gauge is
`0370`/`0373`; it reads the hardware on every `power_supply` property access.

## 1. Goal

Replace per-property hardware reads and uncontrolled userspace polling with
one event-aware gauge path:

- one cached snapshot per refresh;
- one coalesced 30 s delayed work item;
- PMIC threshold IRQs shorten the next refresh immediately;
- no gauge I2C in `get_property()` or in IRQ context;
- no gauge polling while suspended;
- only low-battery and charger-detect are wake sources.

This is about the battery/gauge path. SoC thermal zones keep their own trip
IRQs and 1 s fallback; charger control stays in the charger driver.

## 2. Current behaviour

`mt6351_fg_get_property()` in
[0370](../../patches/proposals/0370-power-supply-add-the-MediaTek-MT6351-fuel-gauge.patch)
does the work per property:

- `CURRENT_NOW`, `CHARGE_COUNTER`, `STATUS` and `CAPACITY` each run
  `mt6351_fg_read()`, which performs the FGADC latch sequence and several
  regmap reads.
- `VOLTAGE_NOW` reads the IIO channel each time.
- `TEMP` calls `thermal_zone_get_temp()` each time.
- `CAPACITY` reads voltage, temperature and OCV on each access.

Nothing caches the result, nothing coalesces readers, and no PMIC IRQ is
requested. A single `upower` or sysfs sweep can therefore trigger several
latch sequences back to back.

## 3. Design

### 3.1 One snapshot

Add a cached snapshot to `struct mt6351_fg`:

```c
struct mt6351_fg_snapshot {
	ktime_t updated;
	bool valid;
	int voltage_uv;
	int current_ua;
	int charge_uah;
	int temp_mc;
	int capacity;
	int capacity_level;
	int status;
	bool charger_online;
};
```

`get_property()` only maps this snapshot to `power_supply` values. It must not
call `regmap`, IIO or the thermal framework. If the snapshot is not valid yet,
return `-ENODATA`; probe fills it before registration completes.

Capacity is still computed in the refresh work from the same OCV table and
`V - I * R` rule as `0370`. The cached value is what userspace sees.

### 3.2 One work item

`struct mt6351_fg` gains:

```c
struct delayed_work gauge_work;
struct mutex lock;              /* protects the latch and snapshot */
struct mt6351_fg_snapshot snap;
bool work_running;
bool rerun;
```

Refresh sequence:

1. Take `lock`.
2. Run one `mt6351_fg_read()` for current and charge counter.
3. Read battery voltage from the IIO channel once.
4. Read battery temperature from the thermal zone once.
5. Read charger online/status from the charger `power_supply`, if present.
6. Compute OCV and capacity.
7. Compare with the previous snapshot using sane tolerances.
8. Publish the new snapshot.
9. Release `lock`.
10. Call `power_supply_changed(fg->psy)` once, only if a published value
    changed.
11. Re-arm for 30 s, or immediately if `rerun` was set.

`power_supply_changed()` runs in work context, never in the IRQ handler.

### 3.3 IRQ coalescing

Request the MT6351 child IRQs from the gauge MFD cell:

- `MT6351_IRQ_BAT_L` — low battery
- `MT6351_IRQ_BAT_H` — high battery
- `MT6351_IRQ_FG_CUR_L` — battery over-current low
- `MT6351_IRQ_FG_CUR_H` — battery over-current high

The MFD cell should expose them as named resources:

```c
DEFINE_RES_IRQ_NAMED(MT6351_IRQ_BAT_L, "battery-low"),
DEFINE_RES_IRQ_NAMED(MT6351_IRQ_BAT_H, "battery-high"),
DEFINE_RES_IRQ_NAMED(MT6351_IRQ_FG_CUR_L, "battery-current-low"),
DEFINE_RES_IRQ_NAMED(MT6351_IRQ_FG_CUR_H, "battery-current-high"),
```

Each threaded handler only does:

```c
mod_delayed_work(system_wq, &fg->gauge_work, 0);
return IRQ_HANDLED;
```

If the work is already running, set `rerun`; do not start a second refresh.
If one of the IRQs is absent, keep the 30 s fallback.

The PMIC IRQ is level-triggered and shared. The MT6351 MFD thread reads and
acknowledges the PMIC status banks; the gauge child handler must not touch
PMIC registers. This preserves the existing `mt6397-irq.c` nesting.

### 3.4 Charger events

`CHRDET` belongs to the charger/PMIC path, not the gauge. The charger driver
should request it and publish `power_supply_changed()`.

If a charger supply exists, the gauge work reads its online/status once per
refresh. A `power_supply` notifier can shorten the next gauge refresh on a
charger transition. If no charger driver exists yet, the gauge sees
`-ENODEV` and reports status from current alone, as `0370` does.

Do not make the gauge responsible for charger control or charger state.

### 3.5 Wake policy

Enable wake only for the sources that need to wake the AP:

| IRQ | Wake |
| --- | --- |
| `BAT_L` | yes |
| `CHRDET` | yes, in the charger driver |
| `BAT_H` | no |
| `FG_CUR_L/H` | policy choice, normally no |
| `THR_H/L` | separate PMIC thermal driver, optional |

`enable_irq_wake()` is called on the child IRQ, not on the PMIC parent. The
MT6351 IRQ controller already maps this to its wake mask and the PM notifier
enables the parent EINT176 (`drivers/mfd/mt6397-irq.c`). The MT6797 EINT
driver supplies `irq_set_wake()`.

On suspend:

- cancel `gauge_work` with `cancel_delayed_work_sync()`;
- leave only the wake IRQs armed;
- on resume, schedule an immediate refresh before restoring the 30 s cadence.

No gauge polling occurs while suspended.

### 3.6 Critical battery stages

`BAT_L` is a single MT6351 comparator, not a 2% SOC signal. The vendor
re-arms the same interrupt at two thresholds:

| Stage | Threshold | Meaning |
| --- | ---: | --- |
| Normal | 3250 mV (`BAT_L`) | first low-battery comparator |
| Stage 1 | 3250 mV, 5 s | enter powersave and notify userspace |
| Stage 2 | 3100 mV (`BAT_L2`) | forced poweroff |
| Recovery | 3400 mV (`BAT_H`) | restore normal policy |

The thresholds come from `POWER_INT0_VOLT`/`POWER_INT1_VOLT`/
`POWER_INT2_VOLT` in the vendor `mt_pmic.h`. The low-level handler must
reprogram `PMIC_AUXADC_LBAT_VOLT_MIN`:

```text
normal:  threshold = 3250 mV, BAT_L enabled
first BAT_L:  stage 1, threshold = 3100 mV, re-arm BAT_L
second BAT_L: stage 2, forced poweroff, BAT_L disabled
BAT_H:   threshold = 3250 mV, stage 0
```

`BAT_L2` is therefore the **second assertion of BAT_L after the threshold is
lowered**, not a separate interrupt source.

#### Stage 1 — powersave and notify

On the first `BAT_L` assertion, confirm it for 5 s and then:

- force the CPU policies to a low-power ceiling (a `freq_qos` max constraint
  on each policy, boost disabled);
- force GPU devfreq to a low-power ceiling (lowest usable OPP, or the
  powersave governor);
- publish `POWER_SUPPLY_PROP_CAPACITY_LEVEL = CRITICAL`,
  `STATUS = DISCHARGING`, and the last valid voltage/current/capacity;
- call `power_supply_changed()` once;
- ask userspace for a normal poweroff through the power-supply event;
- re-arm the comparator at 3100 mV.

No forced poweroff happens at stage 1. The powersave policy buys time for the
userspace save-and-shutdown path while the hardware descends to stage 2.

#### Stage 2 — forced poweroff

On the second `BAT_L` assertion at 3100 mV:

- do not wait for userspace inhibitors;
- run `orderly_poweroff(true)` immediately;
- if the userspace helper cannot run, fall back to `kernel_power_off()`.

This is the hard floor. The gauge capacity can still publish an early warning
at 2% for the UI, but the forced policy is the staged voltage comparator.

#### Recovery

On `BAT_H` (3400 mV) or a valid charger insertion:

- restore the previous CPU/GPU constraints;
- reset the stage to normal;
- reprogram the comparator to 3250 mV;
- publish the recovered `power_supply` state.

Use hysteresis so a load transient does not flap stage 1. If stage 2 has been
entered, recovery is not expected; poweroff is already in progress.

#### Why not capacity alone

Under load, terminal voltage can cross 3250 mV well before 2% SOC, and at low
temperature the OCV estimate can be pessimistic. The comparator is the
hardware backstop; the gauge capacity is the userspace-visible estimate. Do
not force poweroff on a single capacity sample.

## 4. Timing

| State | Gauge refresh |
| --- | --- |
| Running, on battery | 30 s |
| Running, charging | 30 s |
| Gauge threshold IRQ | immediate, coalesced |
| Charger transition | immediate if notified, otherwise next 30 s |
| Resume | immediate |
| Suspend | none |

Thirty seconds is the single gauge cadence. Battery temperature is read in the
same pass. If charging safety needs a faster software path, that belongs to
the charger/thermal driver, not a second gauge timer.

## 5. Error handling

- A failed FGADC latch or regmap read keeps the last valid snapshot and logs
  once per failure burst.
- The latch is always cleared/released even after a failed read, preserving
  the `0370` cleanup path.
- A failed refresh does not call `power_supply_changed()`.
- Back off to 60 s after repeated failures, then return to 30 s on success.
- `get_property()` never returns a partially updated snapshot; publish under
  the lock.

## 6. API and device tree

No `power_supply` ABI change. The same properties remain:

`STATUS`, `PRESENT`, `TECHNOLOGY`, `VOLTAGE_NOW`, `CURRENT_NOW`,
`CHARGE_COUNTER`, `CAPACITY`, `CAPACITY_LEVEL`, `TEMP`, `CHARGE_FULL_DESIGN`,
`VOLTAGE_MAX_DESIGN`, `VOLTAGE_MIN_DESIGN`.

`CAPACITY_LEVEL` is the critical-battery notification path. It is mapped from
the cached capacity at 2% and 3% hysteresis; it is not a PMIC property.

The MFD cell gains IRQ resources; the gauge node does not need a new
compatible or a new register. `wakeup-source` is optional because wake is
enabled per child IRQ, not by the device node alone.

## 7. Validation

Static and runtime checks:

1. Read every `power_supply` property repeatedly while tracing
   `i2c_transfer`/`regmap`; expect zero gauge I2C from `get_property()`.
2. Confirm one refresh per 30 s when idle, and one extra refresh per gauge
   IRQ.
3. Confirm `power_supply_changed()` fires only when a value changes.
4. Suspend, wait, confirm no gauge work runs; trigger `BAT_L` and `CHRDET`
   separately and confirm wake plus an immediate refresh.
5. Inject a regmap failure and confirm the old snapshot survives and the
   backoff engages.
6. Confirm capacity tracks the existing OCV result at the same temperature
   and current; this proposal changes cadence, not the estimator.
7. Drive the pack to the first `BAT_L` at 3250 mV and confirm the 5 s
   confirmation, powersave transition, one `CAPACITY_LEVEL=Critical` uevent,
   and re-arm at 3100 mV.
8. Drive to the second `BAT_L` at 3100 mV and confirm the forced poweroff
   path, with no userspace inhibitor wait.
9. Insert AC or raise the pack to `BAT_H` during stage 1 and confirm the
   previous CPU/GPU constraints are restored and the comparator returns to
   3250 mV.
10. Confirm a capacity-only 2% warning does not force poweroff; only the
    staged comparator does.

The existing VM build checks cover compile/DT only. Any wake or IRQ claim
requires a device run with the exact candidate identity.

## 8. Implementation order

1. Add the snapshot, lock, work and cache to `0370`; keep `0373` reporting.
2. Add the MT6351 gauge IRQ resources in `mt6397-core.c`.
3. Request the optional gauge IRQs and add coalescing.
4. Add the two-stage `BAT_L` comparator state machine: 3250 mV, re-arm at
   3100 mV, reset on 3400 mV.
5. Add the stage-1 powersave transition through the CPU `freq_qos` and GPU
   devfreq interfaces, with a saved/restored prior state.
6. Add the stage-2 forced poweroff path.
7. Add wake for `BAT_L`; leave the other gauge IRQs non-wake.
8. Add PM suspend/resume cancel and immediate refresh.
9. Add the charger `power_supply` read/notifier when the charger driver lands.
10. Run the trace, suspend/wake, stage-transition and failure tests.

## 9. Non-goals

- No vendor `fuelgauged`/`libfgauge.so` estimator.
- No change to the OCV tables, `CAR_TUNE`, sense resistor or capacity model.
- No charger state machine or charge-current policy.
- No SoC thermal-zone policy.
- No polling in suspend.
- No wake on every gauge IRQ; wake is a policy decision, not a default.

## 10. Open questions

- Are 3250 mV and 3100 mV the right stage thresholds for this pack at typical
  PDA load, or should the first stage be raised?
- Is 5 s the right stage-1 confirmation, or should it be shorter at high
  current?
- Should stage 1 also trigger on `capacity <= 2%`, or only on the voltage
  comparator?
- Should stage 2 force poweroff even when a charger is present, or cancel if
  charging has already started?
- Does the PMIC `BAT_L` status need an explicit acknowledge beyond the MFD
  bank read?
- Is `CHRDET` owned by the PMIC charger driver or by a separate BQ25896
  driver on this board?
- Does the BQ25896 INT pin exist on the Gemini, or is charger status only
  available by polling?
- Should `FG_CUR_L/H` wake at all, or only update the snapshot on the next
  resume?
