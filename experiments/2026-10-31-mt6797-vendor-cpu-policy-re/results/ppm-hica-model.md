# PPM v1 and HICA policy model

Source: Gemian `59e00a91`; files and hashes in the
[experiment README](../README.md). This is a static reconstruction of the
vendor policy, checked against the retained live `/proc/ppm` dump. It is not a
runtime trace.

## 1. Policy order

PPM keeps a policy list sorted by descending priority (higher number first).
The live order is:

| Priority | Policy | Role |
| --- | --- | --- |
| 192 (`0xC0`) | HICA | Base per-state cluster/OPP limits |
| 128 (`0x80`) | SYS_BOOST | Performance-service boost |
| 128 | PERF_SERV | Performance-service request |
| 64 (`0x40`) | LCM_OFF | Screen-off limits |
| 64 | USER_LIMIT | User min/max frequency/core limits |
| 1 | DLPT | Dynamic low-power thermal budget |
| 1 | THERMAL | Thermal power budget |
| 1 | PWR_THRO | Battery/OC power budget |
| 0 | FORCE_LIMIT | Forced min/max |
| 0 | UT | Unit-test override |
| 0 | PTPOD | PTP one-point override |

HICA is always applied as the base. The other active policies tighten or
replace its limits. Power-budget policies (priority 1) set a budget rather than
a direct frequency, and PPM converts the budget to a state/limit.

## 2. HICA state limits

`LIMIT(fmin_idx, fmax_idx, min_core, max_core)`. Index 0 is the highest
frequency and index 15 the lowest, so a smaller `fmin_idx` means a higher
minimum frequency.

| State | LL (cluster 0) | L (cluster 1) | B (cluster 2) |
| --- | --- | --- | --- |
| `LL_ONLY` | freq 15..0, cores 1..4 | freq 15..0, cores 0..0 | freq 15..0, cores 0..0 |
| `L_ONLY` | cores 0..0 | freq 8..0, cores 1..4 | cores 0..0 |
| `4LL_L` | freq 15..0, cores 1..4 | freq 15..0, cores 0..4 | freq 15..0, cores 0..2 |
| `4L_LL` | freq 15..0, cores 0..4 | freq 15..0, cores 1..4 | freq 15..0, cores 0..2 |

In `4LL_L` and `4L_LL`, HICA also limits the B cluster to 1.5 GHz when
`PPM_DEFAULT_LIMIT_B_FREQ` is enabled. The live dump reports
`hica_is_limit_big_freq = 1 (idx = 9)`, which is the 1.495 GHz B entry in the
selected SB/0119 table.

`L_ONLY` is the only state with a non-minimum L frequency floor: index 8 is
1.352 GHz in the live L table. The other states allow the full L range.

## 3. Transition rules

Constants from `mt_ppm_platform.h`:

| Constant | Value |
| --- | --- |
| `PPM_DEFAULT_DELTA` | 20 |
| `PPM_DEFAULT_HOLD_TIME` | 4 |
| `PPM_DEFAULT_FREQ_HOLD_TIME` | 4 |
| `PPM_LOADING_UPPER` | 400 |
| `PPM_TLP_CRITERIA` | 400 |
| `PPM_HICA_BIG_LIMIT_FREQ` | 1,500,000 kHz |

The rules are evaluated in two ordered lists per state: performance-transfer
first, then power-transfer. A rule returns true when its hold count reaches the
configured threshold.

| From → to | Condition |
| --- | --- |
| `LL_ONLY → L_ONLY` | Root not fixed to LL and LCM-off not active, and either an LL heavy task with TLP ≤ 400, or load > 380 with TLP ≤ 400 for 4 samples, or LL frequency at its maximum for 8 samples |
| `LL_ONLY → 4LL_L` | LL heavy task with TLP > 400, or load > 380 with TLP > 400 for 4 samples |
| `L_ONLY → LL_ONLY` | Root not fixed to L, no L heavy task, and L frequency below LL maximum for 4 samples |
| `L_ONLY → 4L_LL` | L heavy task, or load > 380 for 4 samples |
| `4LL_L → LL_ONLY` | No heavy task in any cluster and load ≤ 380 for 4 samples |
| `4L_LL → L_ONLY` | No heavy task in any cluster and load ≤ 380 for 4 samples |

There is no direct `L_ONLY → 4LL_L` or `4LL_L → L_ONLY` transition. The state
machine must pass through `LL_ONLY` or `4L_LL` as appropriate.

`hps_get_hvytsk()` is the heavy-task input. `ppm_hica_state_decision()` may
override the state with a power-budget-derived state, and may use a
`fix_state_by_segment` override. The live unit is in `Performance` mode, where
the performance rules are the relevant ones.

## 4. Limit aggregation

`ppm_main_calc_new_limit()` walks the sorted policy list:

- HICA replaces the working limit with its state limit and clears any
  outstanding advise values.
- A normal policy whose range is disjoint from the working range replaces the
  out-of-range side.
- An overlapping policy tightens the range:
  - `min_cpufreq_idx = MIN(current, policy)` (raises the minimum frequency),
  - `max_cpufreq_idx = MAX(current, policy)` (lowers the maximum frequency),
  - `min_cpu_core = MAX(current, policy)`,
  - `max_cpu_core = MIN(current, policy)`.
- Power-budget policies do not set the minimum frequency or core count.
- If a cluster has zero cores in the final request, its frequency limits are
  inherited from the previous request.
- The final request carries `min_cpufreq_idx`, `max_cpufreq_idx`,
  `min_cpu_core`, `max_cpu_core`, optional advise values, and the root cluster.

In index space, larger index means lower frequency. The code's naming is
counter-intuitive: `idx_opp_ppm_base` receives `min_cpufreq_idx` and
`idx_opp_ppm_limit` receives `max_cpufreq_idx`.

## 5. Client callbacks

PPM notifies two clients:

| Client | Callback | Effect |
| --- | --- | --- |
| `PPM_CLIENT_DVFS` | `ppm_limit_callback()` in `mt_cpufreq.c` | Sets each policy's min/max frequency from the request and calls `_mt_cpufreq_set()` when the current OPP is outside the range |
| `PPM_CLIENT_HOTPLUG` | `ppm_limit_callback()` in `mt_hotplug_strategy_core.c` | Writes `ref_base_value`/`ref_limit_value` per cluster and wakes HPS |

If only frequency limits changed, PPM notifies DVFS only. If only core limits
changed, it notifies HPS only. If both changed, both are notified; under a
power-budget policy PPM may notify HPS first when frequency falls and core
count falls in the same update. The HPS loop runs `mt_ppm_main()` before its
own hotplug action, so a frequency decision is available to the cpufreq path
before cores are added or removed.

## 6. Live cross-check

The retained `/proc/ppm` dump reports:

- `ppm is enabled`, mode `Performance`;
- current state `LL_ONLY`;
- cluster 0 `(15)(0)(1)(4)`, clusters 1 and 2 `(15)(0)(0)(0)`;
- HICA big-frequency limit index 9;
- policy list order and enabled states matching the table above.

That matches the `LL_ONLY` state limit exactly. It does not prove the
transition history; the hold counters and the actual sequence remain
runtime-only.

## 7. Boundary

Proved statically:

- policy order and aggregation rules;
- state limits, including the B 1.5 GHz cap;
- transition thresholds and hold counts;
- how limits reach cpufreq and HPS.

Not proved:

- which policy was active at each historical instant;
- the exact load/TLP values that produced a transition;
- whether the live unit followed the performance or power branch in a
  specific cycle;
- any policy change caused by a write to `/proc/ppm`.

Those require a bounded read-only trace with load/TLP/state sampling.
