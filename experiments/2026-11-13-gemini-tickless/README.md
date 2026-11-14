# Experiment: a more tickless kernel (lazy RCU, HZ 100)

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-13-gemini-tickless` |
| Status | `complete`: T0-T2 measured; lazy RCU and HZ 100 folded into the station fragments |
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

### T0: the base image (2026-11-13)

Run by the custodian on station-work-120 (boot2 `ff5fb22a…`, package
`57181f2d…` from `64c1f85e`, `mt6797-a53-station-dvfs`: HZ 250, no lazy
RCU), boot `3f3e037b…`, card root with gemini-base 63. `mt6797-gate-unused`
loaded by hand (26 gates), no `rcuo` threads. On battery at 99-98 %, screen
blanked by the idle timer, CPU0 alone, 30 s settle. The census recorded 120 s
into the ring buffer with no SSH traffic in the window. Raw files stay
private with the custodian.

| Count, 120 s | Total | Per second |
| --- | --- | --- |
| tick restarts (`hrtimer_start` of `tick_nohz_handler`) | 5,922 | 49.4 |
| `arch_timer` interrupts | 5,173 | 43.1 |
| schedutil's `dl_task_timer` | 1,269 | 10.6 |
| `hrtimer_wakeup` (sleeps and poll timeouts) | 1,378 | 11.5 |
| `rcu_preempt` wakeups | 314 | 2.6 |

- **Other interrupts:** I2C `1100e000` 543, IPIs 154, I2C `11007000` 154,
  `11240000.mmc` 144.
- **Top wakers:** `kworker/0:0` 1,314; `sugov:0` 927; `gdbus` 697; `upowerd`
  514; `dbus-broker` 497; unbound kworkers 721; `rcu_preempt` 314;
  `kcompactd0` 235; `cat` 192; `noctalia` 191; `battery-guard` 170.
- **Timers started:** `delayed_work_timer_fn` 1,867; `tcp_orphan_update`
  1,148 (9.6/s); `process_timeout` 974; `mix_interrupt_randomness` 117.
- **Work items:** `mt6797_mac_join_work` 1,318 (11/s);
  `thermal_zone_device_check` 141; `vmstat_shepherd` 120.
- **Current:** 600 samples at 1 Hz, mean 143.6 mA (sd 1.7) at 4.135 V.

**Reading.** RCU's own share is small: `rcu_preempt` wakes about 2.6 times a
second, so T1 can at most remove that and the tick restarts it causes. The
larger wakers belong to other owners, and the custodian passes them on:
the Wi-Fi driver's join work at 11/s and TCP's orphan-count timer at
9.6/s (wifi-daily), schedutil at about 8-11/s (cpufreq), and `upowerd`,
`gdbus` and `dbus-broker` at about 14/s together (Arch root).

### T1: lazy RCU (2026-11-14)

Run by the custodian on station-work-121 (`mt6797-a53-station-dvfs-rcu-lazy`,
boot2 `4dfa17e2…`), boot `9a7d0389…`, same method as T0: 11 `rcuo` threads,
26 gates, no RCU stall or warning, the A72s offline, battery at 86-85 %.

| | T0 | T1 |
| --- | --- | --- |
| tick restarts, 120 s | 5,922 (49.4/s) | 5,536 (46.1/s) |
| `arch_timer` interrupts | 5,173 | 4,863 |
| RCU thread wakeups | `rcu_preempt` 314 | `rcuog/0` 237, `rcu_preempt` 149, `rcuop/0` 131: 520 |
| current | 143.6 mA (sd 1.7) at 4.135 V | 145.2 mA (sd 2.0) at 4.106 V |

Power is 594.0 against 596.4 mW, a 0.4 % difference inside run-to-run
noise. **Confound:** the run started 11 minutes after boot, so
`systemd-tmpfiles-clean` (15 minutes after boot) fired inside T1's window
(`systemd` 283, `systemd-userwork` 300, `systemd-tmpfiles` 74 wakeups,
`process_srcu` 310 work items). That inflates T1's wakeups, not T0's.

**Reading.**
- Tick restarts, the proxy for idle exits, fell by about 7 % despite the
  extra systemd work in T1's window.
- More RCU thread wakeups, not fewer: the callbacks now run in the `rcuog`
  and `rcuop` kthreads. A wakeup of a kthread is not by itself an idle exit,
  and the tick restarts went down, so the expected removal of RCU's own
  wakeups did not show as fewer wakeups, only as fewer tick restarts.
- The current is unchanged within noise.

**Decision, by the rule:** T1 is no worse than T0, so **lazy RCU is
folded in**: the same five options are now in `gemini-a53-station.fragment`
(every station profile and the release) and `configs/gemini.fragment`. The
`-rcu-lazy` profile stays for the record and for T2.

**One correction for the other owners.** `tcp_orphan_update` is not a
waker: in 7.1 its timer is `TIMER_DEFERRABLE` (`net/ipv4/tcp.c`) and re-arms
every 100 ms, so it only runs when the CPU is awake anyway. The census counts
its re-arms, not wakeups, and the count stays near 10/s with no orphan
sockets at all. `mt6797_mac_join_work` (11/s), schedutil (about 7/s) and the
desktop's D-Bus services (about 14/s) remain real wakers for their owners.
`timerfd_tmrproc` rose from 19 to 143 between the runs, likely userspace on
the card.

### T2: lazy RCU and HZ 100 (2026-11-14)

Run by the custodian on station-work-122 (`mt6797-a53-station-dvfs-rcu-lazy-hz100`),
boot `4fb1600d…`, same method as T1: blanked, CPU0 alone, census 120 s, then
600 samples at 1 Hz. The window started after 960 s of uptime, so
`systemd-tmpfiles-clean` fell outside it (no `systemd-userwork` or `systemd`
wakers this time). Raw files stay private with the custodian.

| | T0 (HZ 250) | T1 (HZ 250, lazy RCU) | T2 (HZ 100, lazy RCU) |
| --- | --- | --- | --- |
| tick restarts, 120 s | 5,922 | 5,536 | 4,710 (39.3/s) |
| `arch_timer` interrupts | 5,173 | 4,863 | 4,264 (35.5/s) |
| current | 143.6 mA at 4.135 V | 145.2 mA at 4.106 V | 147.0 mA at 4.044 V |
| power | 593.8 mW | 596.2 mW | 594.5 mW |
| battery | 99-98 % | 86-85 % | 84 % |

- **Top wakers, 120 s:** `kworker/0:1` 1,198; `sugov:0` 800; `gdbus` 619;
  `upowerd` 545; unbound kworkers 499; `dbus-broker` 468; `rcuog/0` 323;
  `kcompactd0` 235; `rcu_preempt` 190; `rcuop/0` 184; `noctalia` 183;
  `battery-guard` 157.
- **Timers started:** `delayed_work_timer_fn` 1,700; `tcp_orphan_update`
  1,090 (deferrable, not a waker); `process_timeout` 892.
- **Work items:** `mt6797_mac_join_work` 1,155 (9.6/s, still the largest
  single source); `thermal_zone_device_check` 137; `vmstat_shepherd` 120.

**Reading.**
- Against T1, tick restarts fell 15 % and `arch_timer` interrupts 12 %. Part
  of that is T1's tmpfiles confound (about 580 systemd wakeups in T1's
  window), so the HZ share alone is not separable from these runs. Against
  T0, which had no confound, the two changes together cut tick restarts by
  20 % and `arch_timer` interrupts by 18 %.
- Power is unchanged: 594.5 mW against 596.2 mW in T1 and 593.8 mW in T0,
  all within run-to-run noise. The CPU still leaves idle about
  35 times a second for the Wi-Fi join work, schedutil and the desktop's
  D-Bus and UPower polling; the tick only follows those wakeups.
- So HZ 100 meets the tick criterion of the decision rule, but not a power
  one. Its only argument is the owner's "tickless as much as possible".

**Decision, by the rule:** T2 lowers ticks, so `HZ_100` is folded in **only
if** the owner's three checks match T1: typing and scrolling in the desktop,
5 minutes of music with no PipeWire underrun in the journal, and a timed
Wi-Fi download within T1's time. Any lag, underrun or slower download keeps
`HZ_250`. Until then the fragment stays in the `-hz100` profile only. The
download is the check most likely to differ: driver timeouts and `msleep()`
polling round up to 10 ms jiffies instead of 4 ms.

**Owner checks (2026-11-14),** run by the custodian on the same image, boot
`ca480729…`:

- Typing and scrolling in the desktop: fine, in the owner's words "the audio
  is fine, scrolling works too".
- Music: played by the owner; no underrun or xrun line in the system or user
  journal for the boot.
- Wi-Fi download: 3 × 64 MiB over HTTP from a LAN host, 12.98, 13.53 and
  12.92 s (41.4, 39.7 and 41.6 Mbit/s) at -52 dBm on a 5.8 GHz, 40 MHz
  channel. T1 had no timed download, so there is no same-configuration
  baseline; the result sits inside the Wi-Fi records' 37-47 Mbit/s iperf
  receive band.
- A fullscreen browser column showed beside the terminal in the compositor's
  scrolling layout and went away when fullscreen was turned off. That is a
  compositor layout issue, unrelated to HZ.

**Decision, by the rule:** the three checks match, so **`HZ_100` is folded
in**: `gemini-a53-station.fragment` and `configs/gemini.fragment` now set it.
The `-hz100` profile stays for the record. The download check is the weakest
of the three (no same-configuration baseline); a regression in a later Wi-Fi
record that tracks jiffy timeouts would reopen it.

## Conclusion

- Lazy RCU with offloaded callbacks and HZ 100 together cut tick restarts by
  about 20 % and `arch_timer` interrupts by about 18 % with CPU0 alone and the
  screen blanked. Both are now in the station fragments.
- Neither change moved the blanked current measurably (about 594 mW in all
  three runs). The CPU still wakes about 35 times a second, and the tick only
  follows those wakeups. Their sources belong to other owners: the Wi-Fi
  driver's `mt6797_mac_join_work` (about 10/s), schedutil, and the desktop's
  D-Bus and UPower polling.
