# Power accounting design

Status: **proposal**. No implementation, build or device access. This document
is the design behind the [record](README.md); it carries no runtime claim.

Related: [Gemini fuel gauge](../../docs/hardware/gemini-fuel-gauge.md),
[Gemini charging](../../docs/hardware/gemini-charging.md),
[MT6351 PMIC ADC](../../docs/hardware/mt6351-pmic-adc.md),
[Mali-T880](../../docs/hardware/mali-t880.md), and the evidence records
[2026-10-31 fuel gauge](../2026-10-31-gemini-fuel-gauge/README.md),
[2026-10-31 power status](../2026-10-31-gemini-power-status/README.md) and
[2026-10-30 development station](../2026-10-30-mainline-dev-station/README.md).
The Wi-Fi plan already sets an exit criterion in these terms: idle connected
draw "measured at the battery with charge-guard holding the charger off"
([daily-use plan](../../docs/WIFI_DAILY_USE_PLAN.md#5-battery)).

## 1. Scope and claim levels

| Level | Claim | Method | Confidence |
| --- | --- | --- | --- |
| L0 | total device power, unplugged | gauge, direct | measurement |
| L1 | total device power, plugged | regulated-input window or model | measurement or estimate |
| L2 | per-domain split (floor, features, user state) | fitted model | estimate |
| L3 | per-application power | accounted time times fitted coefficients | estimate, ranking-grade |

Every report must name its level. Presenting L3 as L0 is the failure mode this
design exists to prevent.

## 2. The power path and the observability problem

The BQ25896 is an NVDC (power-path) charger: the system rail is fed from VBUS
through the input FET, and the battery carries the difference between charge
current and system load. The MT6351 gauge senses only the battery branch, on
the 10 mΩ resistor across `CS_P`/`CS_N`.

```
P_in * eta + P_bat = P_sys        P_in = V_bus * I_in,  P_bat = V_bat * I_b
I_sys = (V_bus * I_in * eta - V_bat * I_b) / V_sys
```

Every term is measurable except `I_in`. The BQ25896 has no input-current ADC:
`REG11` is VBUS, `REG12` is the *battery* current, which is the same node the
gauge already reads at roughly 140 times the resolution. This yields three
regimes:

| Regime | `I_in` | `I_sys` observable |
| --- | --- | --- |
| HiZ (`REG00` bit 7) | 0 | exactly, `P_sys = V_bat * \|I_b\|` |
| input-current regulation | `= IINLIM` | yes, up to one constant `eta` |
| charging, or charger off with VBUS present | unknown | no; only net battery current |

Measured support for the third row: with `CHG_CONFIG` clear the gauge read
about 0 mA while the system ran from USB, and with charging enabled above the
charger's 4.208 V default the gauge read -190 to -210 mA
([charge limit](../2026-10-31-gemini-fuel-gauge/README.md#charge-limit-2026-10-31-owner-request)).

Two tempting shortcuts are dead ends and are recorded as such:

- the charger's `ICHG` ADC adds no information about the system branch;
- thermal zones are a lagged, uncalibrated proxy at 1-2 °C resolution, usable
  only as a sanity check.

### 2.1 The input-current clamp

Write `REG00` `IINLIM` to its 100 mA floor and keep `WD_RST` kicked. The
charger then regulates input current, which turns an unmeasurable into a
regulated known:

```
I_sys = (V_bus * IINLIM * eta - V_bat * I_b) / V_sys
```

This is the preferred plugged method because USB stays enumerated, unlike
HiZ. A sample is valid only when all of the following hold:

- `I_b` is negative and stable across at least three consecutive samples;
- `REG00` reads back the value written, so the 40 s watchdog has not restored
  the 500 mA default;
- `V_bus` stays above 4.6 V, so VINDPM (absolute 4.5 V per the vendor
  configuration) is not the binding loop instead of IINLIM.

The clamp cannot work when load is below 100 mA. That case is idle by
definition, which is exactly where a measured idle baseline is most accurate,
so the two methods fail in complementary regimes.

HiZ is reserved for scheduled ground truth: exact, but VBUS disappears, so it
requires local logging and a restore guarantee.

## 3. Domain partition and the ownership rule

A cost belongs to whoever decides the state that causes it.

| Domain | Decided by | Examples | Measured how |
| --- | --- | --- | --- |
| D0 kernel floor | always on | SoC quiescent and leakage, DRAM refresh, tick, idle, kernel threads | direct, nothing running |
| D1 enabled feature | configuration or rfkill | Wi-Fi, Bluetooth, GNSS, modem, storage controller, USB gadget | toggle the feature, everything else fixed |
| D2 user-driven | a human action | lid, backlight level, keyboard use, audio volume | toggle the control, everything else fixed |
| D3 application | scheduling | any cgroup workload, GPU dynamic cost | cgroup time and job accounting |

Consequences of the rule:

- kernel work caused by a feature belongs to the feature. The Wi-Fi receive
  engine is a poll, so "Wi-Fi up" burns CPU with zero traffic; charging that
  to D0 would make enabling Wi-Fi look like a heavier kernel;
- kernel work caused by an application's syscalls belongs to the application
  as `system` time, but interrupt and softirq work lands on whichever task was
  interrupted. D3 must therefore never absorb it; the report carries an
  explicit kernel/softirq bucket;
- display splits by owner: panel and backlight power is D2, a DSI/DRM pipeline
  would be D1. There is no DRM today, so the display is measurable only as
  backlight.

Attribution is conditional. A feature's cost is only meaningful with its
precondition stated (SoC awake, battery carrying the load), and must be
reported with that condition set.

## 4. Domains are curves, not booleans

Each domain has at least three states, and the middle one is not free: off,
enabled-idle, and under load. The same holds for the backlight (off, dim,
bright) and for an application (idle, partial, saturated). A single number per
feature is where such budgets usually fail.

```
P_total = P0(T)
        + sum f_k(state_k)      D1, gated: zero when off
        + sum u_j(level_j)      D2, curve in level
        + sum a_i(marginal)     D3, marginal only
        + interaction terms     only where physically expected
        + epsilon
```

## 5. Measurement design

A single global least-squares fit is fragile here, because D0 drifts with
junction temperature and leakage. The primary method is **interleaved A/B/A
toggling**, which yields marginal costs directly and cancels first-order
drift: baseline 30 s, toggle 30 s, restore 30 s, at 1 Hz, randomised order,
accepting the pair only when the pre- and post-baselines agree within gauge
noise.

| Step | Condition | Yields |
| --- | --- | --- |
| B0 | lid closed, backlight off, no radios, no USB, idle | D0 floor, `T_ref` |
| B1 | backlight at three levels | D2 display curve |
| B2 | Wi-Fi up, no traffic | D1 static plus poll cost |
| B3 | Wi-Fi at a fixed 5 Mbit/s | D1 marginal per Mbit/s |
| B4 | one application cgroup at fixed CPU share | D3 CPU coefficient |
| B5 | keyboard scanning active | D2 sub-term |
| G1 | Panfrost probed, rail on, no jobs | GPU static cost |
| G2-G4 | offscreen GPU workload at about 25/50/100 % duty | GPU slope |
| C-G | the same workload forced to CPU | GPU CPU-side control |
| A1-A4 | ablations in reverse order | drift and hysteresis check |
| C1 | held-out combination | closure test |

The additive model is then only a runtime estimator for conditions that were
not toggled, and it is gated by the closure test: predict C1 from the fitted
set and require the prediction within the stated tolerance. A model that fails
its own held-out case is not reportable.

Two protocol details matter more than they appear:

- **Low currents need the coulomb counter, not instantaneous current.** At
  about 30 mA, 1 Hz instantaneous samples are offset-dominated. The counter
  steps 103.4 µAh, so a 10-minute window at 30 mA is about 29 counts, 3 %
  resolution. Short high-current toggles may use instantaneous medians.
- **Temperature is a regressor, not a nuisance.** Carry `T - T_ref` globally,
  so that a long Wi-Fi run does not quietly inflate D0 for the screen test
  that follows.

## 6. Model, attribution and reporting

Regressors, all available from the current station configuration except where
noted:

`{ 1, A53 busy time, idle time, backlight level, lid, Wi-Fi up, Wi-Fi bytes,
eMMC bytes, USB gadget up, T - T_ref }`

Fit `P_sys = sum theta_i * x_i` by non-negative least squares: power adds, and
a negative coefficient means a confounded design, not a result. With no
`cpufreq` in the composed configurations there is no frequency regressor, but
MT6797 DVFSP is firmware-owned and unobservable, so coefficients are valid
only for the workload mix they were fitted on. That is a scoping limit of the
model, not a defect.

Identifiability needs at least as many independent conditions as parameters;
the table in section 5 provides them.

Reporting is marginal, never proportional, because the denominator shrinks as
the device idles:

- **marginal cost**: `dP` from enabling the domain, which answers what it
  costs;
- **attributed share**: the domain's fraction of the variable part only, with
  D0 excluded from the denominator;
- **closure residual**: measured total minus the sum of domains, always
  printed.

The identity `P0 + sum dD1 + sum dD2 + sum dD3 + epsilon = P_measured` is the
tool's most useful diagnostic. A large residual means the partition is wrong
somewhere.

## 7. GPU allocation

The GPU is the only domain with a static and a dynamic part, and they have
different owners.

| Part | Owner | Rule |
| --- | --- | --- |
| static: MFG rail, MFGPLL, power domains, SRAM, leakage | the client that keeps it powered | an application that opened the render node pays the idle-keepalive; only a system component holding the device open with no driver moves this to D1 |
| dynamic: job execution | clients, split by GPU-busy time | proportional to each client's busy time within the sampling interval |
| driver CPU cost (submission, MMU, cache maintenance) | the client, as CPU | charged to its cgroup as `system` time, never counted again in the GPU bucket |

GPU power is never a hardware reading. There is no telemetry on the RT5735
vGPU rail, and the MT6351 senses only the battery branch, so the GPU cost is a
coefficient times a busy fraction, calibrated by whole-device differential
measurement. That coefficient inherits the gauge scale error, which cancels in
shares.

Current boundary: the GPU node is disabled, there is no OPP, devfreq or
cooling, and the first runtime point is planned as a fixed 520 MHz / 1.0 V
([bring-up](../2026-10-31-mali-t880-offline-bringup/README.md)). A fixed point
removes the DVFS confound but also means no frequency curve. With no DRM
display, the first GPU measurements must be offscreen, which isolates GPU cost
before display cost exists to contaminate it.

Runtime attribution needs per-client accounting, which Panfrost's fdinfo does
not provide for engine time (it reports memory). The preferred addition is a
per-`drm_file` job counter with on-slot intervals, mapped to the opener's
cgroup through `/proc/<pid>/cgroup`. Client deltas are taken per sample, so a
client that closes its file descriptor mid-interval is still charged for what
it used, and no bucket silently disappears.

The GPU workload also burns CPU in the driver, so the C-G control state is
required; without it the GPU coefficient absorbs CPU cost and every
GPU-using application is overcharged.

## 8. Error budget

| Term | Effect |
| --- | --- |
| gauge quantization, 0.364 mA per count | averaged out over a window |
| gauge scale: `CAR_TUNE` 115 against LK's 86, per-chip trim unapplied | up to about 25 %, multiplicative |
| model residual | 10-20 % on dynamic terms |
| baseline term | measured directly, small error |
| GPU coefficient | two-parameter fit from three duty points, inherits the gauge scale |

The multiplicative error is the useful property: it scales every coefficient
equally, so the partition and the ranking are trustworthy before the absolute
watts are. That is the correct order to build in.

## 9. Tooling

- `power-sampler`: static userspace binary, 1 Hz, fixed-field records carrying
  both the electricals and the domain state that they were taken under: gauge
  voltage, current and counter; `/proc/stat`; per-cgroup `cpu.stat`; backlight
  and lid; charger `REG0E`, `REG11` and `REG12`; feature state from rfkill and
  operstate; GPU power and busy state when it exists.
- `power-clamp`: optional bounded clamp window with readback guard and
  restore-on-exit; one reviewed `REG00` write.
- `power-report`: applies the coefficient set and prints the stacked
  breakdown, the per-application marginal costs and the closure residual.

No kernel change is needed for D0, D1 or D2, and none for D3 beyond cgroup
accounting, which is already enabled. `CPU_IDLE` residency and `PSI` would
mainly tighten D0 and idle attribution later; this design does not require
them.

## 10. Deferred measurements and open questions

1. Does `IINLIM` at 100 mA hold on the station's host port? One USB-meter
   cross-check settles it.
2. Is `eta` one constant across 4.5-5.2 V in and 3.6-4.3 V out, or does it
   need two coefficients?
3. Does the gauge hold scale below 5 mA, or does offset force counter-only
   integration there?
4. Is additivity (screen plus CPU) good enough at these power levels?
5. Which Panfrost revision, if any, exposes per-client engine time, and what
   does the first 520 MHz point cost in static power?

## 11. Non-goals

- No per-rail measurement is proposed: the hardware has no current sense on
  the MT6351 bucks or the RT5735 rail.
- No upstream interface is proposed. Linux has no per-application energy
  interface, and this model is a userspace convention.
- No claim of calibrated capacity or state of charge; the OCV lookup needs a
  full discharge that this design does not schedule.
