# Sensor mapping and freshness audit

This offline follow-up interprets the [bounded attribution rejection](results/attribution-runtime-thermal-rejected.txt).
It preserves that rejection and admits no further reads or workload on the
consumed session. No kernel build, source copy or device access was performed.

## Exact source and method

The active managed Buildbox tree was checked against the deployed production
package, using the repository source-state hash recipe and full-tree integrity
verification. An older retained tree had a different state and was excluded.
The [audit receipt](results/sensor-freshness-source-audit.txt) pins the matching
source, supporting files and published capture. Inspection covered the bank
configuration, V4 conversion, bank scan, snapshot publication, bank setup and
first-sample checks. Source references below are relative to that verified tree.
No calibration values or raw ADC values were exported.

## Mapping supported by source

`drivers/thermal/mediatek/auxadc_thermal.c:331` defines zero-based sensor IDs;
its table at line 636 and measurement array at line 645 give this mapping.
Bank setup at line 1775 writes the sensor's mux value to each bank-local slot.

| Snapshot slot | Bank | Sensor ID / source name | Bank-local register | Mux | Temperatures °C, in stage order |
| --- | --- | --- | --- | --- | --- |
| 0 | 0 | 0 / MCU1 | TEMP_MSR0 (0x090) | 0 | 35.5 / 36.3 / 41.9 |
| 1 | 1 | 3 / MCU4 | TEMP_MSR0 (0x090) | 3 | 32.3 / 32.4 / 32.4 |
| 2 | 2 | 1 / MCU2 | TEMP_MSR0 (0x090) | 1 | 36.2 / 36.3 / 37.6 |
| 3 | 2 | 2 / MCU3 | TEMP_MSR1 (0x094) | 2 | 32.9 / 32.9 / 33.2 |
| 4 | 3 | 1 / MCU2 | TEMP_MSR0 (0x090) | 1 | 36.0 / 36.7 / 37.9 |
| 5 | 4 | 1 / MCU2 | TEMP_MSR0 (0x090) | 1 | 36.2 / 36.5 / 37.9 |
| 6 | 5 | 1 / MCU2 | TEMP_MSR0 (0x090) | 1 | 36.3 / 36.5 / 37.6 |

Stage order is post-lifecycle, writers-waiting, workers-complete. Sensor ID 1
uses the same mux and calibration index in banks 2--5, but each bank stores its
own measurement. Their observed spreads were 0.3/0.4/0.3 °C. These differences
are consistent with separately sampled/filtered registers; they neither prove
that explanation nor measure conversion age. Seven slots are not seven
independent physical sensors. Source names and bank numbers do not prove die
placement or identify a Big-cluster temperature.

Bank 0/sensor 0 rose 35.5 -> 36.3 -> 41.9 °C: +6.4 °C across the run and
+5.6 °C after the waiting boundary. It became the final maximum. The aggregate
change therefore includes a change within one recorded slot, not merely a
switch between unchanged readings. This is an observation of converted values,
not proof of physical heating, sensor correctness or causality.

## What validity and timestamps establish

The bank scan at line 959 reads each existing measurement once. V4 conversion
at line 886 rejects a zero low-12-bit sample and invalid conversion denominators,
then masks to the low 12 bits and converts using the sensor calibration index.
The snapshot's validity flag is `mtk_thermal_temp_is_valid()` at line 811: a
converted-temperature range test. It does not inspect a conversion-generation
counter or a fresh-data bit. The observer receives the already-converted value
and that validity result; it does not retain upper raw measurement bits.

The probe first-sample predicate in `auxadc_thermal_internal.h:84` requires a
nonzero low-12-bit sample and a converted value between -20000 and 150000 mC.
It is a bounded initialization plausibility check, not evidence that each later
read completes a new conversion. Bank setup programs periodic timing, filter
and ADC-valid-mask controls, but software configuration alone does not prove
live cadence, filter history or sample age. No hardware status-bit semantics
are inferred from register names or numeric masks here.

The observer timestamps bracket its software scan: 10.000/10.461/10.385 µs in
this run. They do not timestamp sensor conversion. Bank selection and capture
are serialized per bank, but the complete scan is sequential. The observed
all-valid mask thus establishes seven accepted converted values, not seven
fresh simultaneous physical temperatures.

## Decision boundary

Winner selection alone is insufficient to explain this run. Conversion
freshness, filtering, mux correctness and physical sensor placement remain
unresolved. The existing converted-only record cannot discriminate these
alternatives, and repeating the consumed program would not repair that gap.
The next offline design must first establish a source-backed register contract
for any proposed freshness evidence, including read side effects and ownership.
If no trustworthy freshness signal exists, explicitly retain unknown age;
do not turn a plausible raw value or a software timestamp into a freshness bit.
A changed observation path needs its own bounded fixtures and admission before
any new build or physical boot. Threshold relaxation and wider load remain closed.
Ordered actions are owned by the [roadmap](../../docs/ROADMAP.md).
