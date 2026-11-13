# Experiment: a more tickless kernel (lazy RCU, HZ 100)

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-13-gemini-tickless` |
| Status | `planned`: two named profiles prepared, config resolution checked; nothing built or run |
| Subsystem | Timer tick, RCU, scheduler tick rate |
| Device variant | Named Gemini PDA development unit, card root on the station kernel |
| Date(s) | 2026-11-13 |
| Investigator(s) | Julien Etienne; Claude (plan, configuration) |
| Tracking issue | none; follows the [cpuidle record](../2026-11-07-mt6797-cpuidle/README.md) |

## Question or hypothesis

The owner asked that the kernel and system be "tickless as much as
possible". The station kernel already has `NO_HZ_IDLE`, high-resolution
timers, `HZ_250`, `SCHED_HRTICK`, `WQ_POWER_EFFICIENT_DEFAULT` and
`CONTEXT_TRACKING_IDLE`, and no RCU offloading or lazy RCU. The custodian's
wakeup census on the card root (0767 image, screen blanked, CPU0 alone,
120 s) found:

| Event | Rate |
| --- | --- |
| `hrtimer_start` for `tick_nohz_handler` | about 53/s |
| `arch_timer` interrupts | about 48/s |
| `dl_task_timer` (schedutil's deadline task) | about 11/s |
| `hrtimer_wakeup` (userspace sleeps and poll timeouts) | about 13/s |

So the tick is mostly stopped already, and the ticks that remain follow
wakeups. Two kernel-side changes can still trim it:

1. **Lazy RCU with offloaded callbacks** (`RCU_NOCB_CPU`, all CPUs, and
   `RCU_LAZY`). RCU callbacks then run in `rcuo` threads and are batched for
   up to about 10 s, instead of keeping the tick on or waking an idle CPU
   to run them.
2. **HZ 100 instead of 250.** Each busy period that restarts the tick then
   takes fewer tick interrupts. The cost is coarser jiffies: `msleep(1)` and
   jiffy timeouts in drivers round to 10 ms instead of 4 ms, and the
   scheduler tick is slower.

`NO_HZ_FULL` is out by the owner's decision: it adds work on every
user-kernel transition and does not help a battery-bound system.

**Hypothesis.** Lazy RCU removes the RCU share of tick restarts and wakeups
at no cost to responsiveness. HZ 100 removes some more ticks, which may or
may not be visible in the current, and has to be checked against
responsiveness.

## Configuration

Two fragments, each added to a named profile cloned from
`mt6797-a53-station-dvfs` (same patch series and fragments otherwise):

| Profile | Adds |
| --- | --- |
| `mt6797-a53-station-dvfs-rcu-lazy` | [`gemini-a53-station-rcu-lazy.fragment`](../../configs/gemini-a53-station-rcu-lazy.fragment): `RCU_EXPERT`, `RCU_NOCB_CPU`, `RCU_NOCB_CPU_DEFAULT_ALL`, `RCU_LAZY`, lazy on by default |
| `mt6797-a53-station-dvfs-rcu-lazy-hz100` | the same plus [`gemini-a53-station-hz100.fragment`](../../configs/gemini-a53-station-hz100.fragment): `HZ_100` |

- `RCU_NOCB_CPU_DEFAULT_ALL` stands in for `rcu_nocbs=all`, so the
  `CONFIG_CMDLINE` that the station RAM root and the card share does not
  change.
- `RCU_NOCB_CPU` depends on `RCU_EXPERT` (or `NO_HZ_FULL`) in 7.1, so the
  fragment sets it; every other expert option keeps its default.
- Checked in the dev VM: a pristine 7.1.3 tree with the station
  configuration, each fragment merged and `olddefconfig` run, resolves to
  exactly these values (`HZ=100` only in the second). The patch series does
  not touch the RCU or HZ Kconfig. Nothing was built.

## Safety assessment

Configuration only: no new driver, register write or firmware call. Each
profile is a new image, so a boot2 write under the standing approval and
the owner's selection. Recovery is the earlier image. RCU stall warnings, a
slow boot or a hang would show at boot; lazy RCU only delays callbacks
(memory frees), not grace periods that code waits on.

## Procedure

Build all three images (the base profile and the two trial profiles) **from
one commit**, so the configuration is the only difference. Run each on the
card root with the same software, at a similar battery level (the G2 run
showed about 3.5 mA of baseline drift between 77 % and 72 %), with
`mt6797-gate-unused` in the same state in all three.

| Stage | Image | Measure |
| --- | --- | --- |
| T0 | `mt6797-a53-station-dvfs` | The custodian's wakeup census, 120 s, blanked, CPU0 alone; then the blanked current, CPU0 alone, 600 samples at 1 Hz (the G1/G2 method); battery level |
| T1 | `...-rcu-lazy` | The same, plus: `rcuo` threads present for every CPU; no RCU stall or warning at boot |
| T2 | `...-rcu-lazy-hz100` | The same, plus a responsiveness check: the owner types and scrolls in the desktop, plays music for 5 minutes (no PipeWire underrun in the journal), and a timed download over Wi-Fi compares with T1 |

In the census, count per window: tick restarts (`hrtimer_start` for
`tick_nohz_handler`), `arch_timer` interrupts, wakeups of `rcu_preempt`,
`rcuog`/`rcuop` and other RCU threads, and the top wakers by task.

**Stop:** an RCU stall or a `WARNING` at boot; a hang (the owner selects the
earlier image).

## Decision

| Result | Next |
| --- | --- |
| T1 no worse than T0 on every check | Fold the RCU fragment into the station's shared fragments (and `configs/gemini.fragment`), whether or not the current moves: it costs nothing and removes a class of wakeups, as the owner asked |
| T1 shows RCU warnings or a slower boot | Keep it out; look at which callbacks wait |
| T2 lowers ticks or current, and responsiveness, audio and Wi-Fi match T1 | Fold `HZ_100` in too |
| T2 changes nothing measurable | Keep `HZ_250`; the coarser jiffies are not worth it for nothing |
| T2 shows lag, underruns or slower Wi-Fi | Keep `HZ_250` |

## What the kernel cannot remove

Most of the remaining wakeups are not the tick's own: schedutil's deadline
task (about 11/s, the cpufreq session's rate limit), userspace sleeps and
poll timeouts (about 13/s, the Arch root session's), and the Wi-Fi driver's
polling (the Wi-Fi session's). The census's per-task counts in T0-T2 go to
those owners.

## Observations

None yet.

## Conclusion

Pending.
