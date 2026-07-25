# Experiment: Gemian CPU and scheduler policy

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-21-gemian-cpu-scheduler-policy` |
| Status | `completed; all-ten interpretation corrected` |
| Subsystem | CPU topology, hotplug, PPM/DVFS, scheduler and cpusets |
| Device variant | Current named Gemini PDA unit |
| Date(s) | 2026-07-21; corrected 2026-07-23 |
| Investigator(s) | Project maintainers |
| Tracking issue | Not yet assigned |

## Question or hypothesis

How does the working Gemian 3.18 kernel configure and dynamically select the
MT6797's eight Cortex-A53 and two Cortex-A72 CPUs, and does it carry scheduler,
hotplug, cpuset, or cluster policy that must be understood before mainline
Linux attempts to online both Cortex-A72 CPUs?

The observation is intentionally separate from Candidate AD. AD proved one
normal boot with CPUs 0--7 online under a static `maxcpus=8` policy; it did not
exercise CPU8/9, DVFS, thermal management, or vendor scheduling policy.

## Provenance and environment

- Kernel: working Gemian vendor Linux `3.18.41+ #7`, built 2019-03-29 with
  GCC 6.3.0-18. The active Android boot image has SHA-256
  `1fa78de9f8744a6818bcef2f6773737939f84364de982413910d4958d6d21513`;
  its kernel field has SHA-256
  `b53d191dc41d3f7364b0fa62b4bc920b1d013a1942b2e6b06727263fc56fcf4d`.
- Root: `/dev/mmcblk0p29` after a changed-ID return from Candidate AD.
- Boot path: retained Planet LK to the known-good primary Gemian system.
- Device access: read-only SSH using the repository's private device key and
  passwordless device sudo.
- Private raw evidence belongs below Git-ignored, mode-0700 `artifacts/`;
  serial-bearing boot tokens are redacted by the probe before output.
- A prior mode-0600 `/proc/config.gz` extraction from that active kernel is
  retained as
  `artifacts/device-inventory/20260712-live/vendor-kernel.config` (SHA-256
  `231d8a2ffe7afac3a4cc62c27d0eb6fe8bd9165ebd096e3e3346dd6df35c18f4`)
  and supplies the focused MediaTek scheduler flags omitted by the first
  capture's narrower filter.
- The initial scheduler and HPS log decoding used Gemian GPL source commit
  [`d388d350`](https://github.com/gemian/gemini-linux-kernel-3.18/tree/d388d350cb2dda8f23b99be6fa5db9628896e87f),
  specifically the `mt_hotplug_strategy_{cpu,algo,core}.c` files below
  `drivers/misc/mediatek/base/power/mt6797/`. No vendor source is copied into
  this repository. That source revision has the matching `action-end` printk
  block commented out, while the exact running binary emits its format. The
  tuple interpretation was therefore a combined pinned-source and
  active-binary decode. Later reconciliation corrected a provenance error:
  the May 24 `gbp59e00a` package installed in the filesystem does not match the
  active March 29 boot image. The exact public commit for the active private
  build remains unresolved. Public commit `59e00a` is the chosen equivalent
  because its HPS and other observer-hook blobs match the active lineage and
  its HPS printk matches the active binary; it is not the exact active source.
  The equivalent source shows HPS changing its local count without checking
  `cpu_up()`/`cpu_down()` results, invalidating the original claim that a
  leading tuple alone proves online completion. The HPS algorithm file is
  `drivers/misc/mediatek/base/power/mt6797/mt_hotplug_strategy_algo.c`; there is
  no `hps_v3` component in this source path.

## Safety assessment

The live probe is read-only. It reads CPU masks, configuration, procfs/sysfs
policy, scheduler domains and logs. It performs no CPU online/offline write,
frequency or voltage change, scheduler-tunable write, workload, partition
access, reboot, suspend, or watchdog operation. Twenty one-second samples
observe natural HPS behavior without stimulating it. Stop on loss of SSH,
power anomaly, unexpected heat, or any read that fails the bounded script.

Enabling CPU8/9 is a later, separate mainline experiment. Prior evidence says a
boot-time CPU8 PSCI call may not return, so observation alone does not authorize
an uncapped boot. A recovery-backed hotplug boundary must precede any normal
all-ten boot policy.

## Associated code

- `scripts/collect-live.sh`: host-side safe SSH wrapper.
- `scripts/remote-probe.sh`: POSIX, read-only Gemian probe executed through
  `sudo -n sh -s` without creating remote files.
- [`results/live-policy-summary-20260721.txt`](results/live-policy-summary-20260721.txt):
  concise, non-identifying observations and the historical HPS decode. Its
  all-ten interpretation is superseded by
  [`results/hps-online-count-adjudication-20260723.txt`](results/hps-online-count-adjudication-20260723.txt).

## Procedure

1. Confirm Gemian `3.18.41+`, changed boot ID, `/dev/mmcblk0p29` root, healthy
   full battery, and external power.
2. Run `collect-live.sh` to a new private mode-0600 output path.
3. Record static topology, boot cap, kernel configuration, HPS/PPM/DVFS/EEM
   policy, scheduler tunables/domains, cpusets, and filtered kernel messages.
4. Observe twenty idle one-second mask samples without changing device state.
5. Sanitize and summarize only decision-relevant, non-identifying evidence in
   `results/`; keep the complete raw capture private.

## Observations

The complete redacted capture is retained privately at
`artifacts/runtime-captures/gemian-cpu-scheduler-20260721/live-boot-385cc5d1.txt`
(169,990 bytes, mode 0600, SHA-256
`aeabdc0d62aaca0520ff9f8a849870f5f2b1b7d5aeaea3e5494ea3c4a2020ba4`).
The probe reported no writes. At capture time the unit was USB-powered, full,
and healthy.

The boot command line contains `maxcpus=5`; dmesg says five processors were
activated during SMP boot. Nevertheless, `possible` and `present` are both
`0-9`. The vendor topology is three clusters: HMP domain 0 is CPUs 8--9,
domain 1 is CPUs 4--7, and domain 2 is CPUs 0--3. PPM independently reports
four cores rooted at CPU0, four at CPU4, and two at CPU8.

CPU masks changed naturally while the read-only probe ran. The identity
snapshot found CPUs 4--5 online; the later scheduler/cpuset snapshot found
CPUs 0--1; the first one-second sample retained 0--1, and samples 2--20 had
only CPU0 online. This is policy-driven hotplug, not a fixed five- or ten-core
online state.

The private HPS log format needed source decoding. The HPS CPU source obtains
each cluster mask through `arch_get_cluster_cpus()` rather than hard-coding
logical CPU ranges; the live HMP-domain and PPM-root lines above establish the
`0--3`, `4--7`, and `8--9` mapping. The leading angle-bracket tuple is HPS's
algorithm-local per-cluster count before the action; it is not secondary
completion evidence. The trailing tuple is the requested target. The middle
six-value tuple is the per-cluster maximum followed by minimum policy limits.
At 9.344392 seconds HPS reported a local `<4>(3)(2)` and target
`<4>(4)(2)`. The next action record at 9.469180 seconds began with the local
tuple `<4>(4)(2)`, and another record at 9.905154 seconds began with the same
local tuple. The later active-binary/public-equivalent reconciliation shows
that this local count is advanced even when a hotplug call fails. These records therefore prove the
vendor policy's four/four/two model and attempted transitions, not that all ten
secondaries completed or were simultaneously present in sysfs.

The active policy surfaces were:

- HPS enabled with 95%/three-sample up and 85%/one-sample down thresholds,
  heavy-task and rush boost enabled, two-CPU input boost, and suspend handling;
- PPM enabled in `Performance` mode with three clusters, HICA states
  `LL_ONLY`, `L_ONLY`, `4LL_L`, and `4L_LL`, plus thermal, DLPT, user-limit,
  force-limit, performance-service, and system-boost policies;
- private LL/L/B/CCI DVFS controls, active CPUHVFS/iDVFS, and live EEM tables
  for 2L, L, BIG, and CCI. The PPM big-cluster table tops out at 2.522 GHz,
  while the private cpufreq table reports 2.587 GHz; this capture does not
  resolve that calibrated-view difference.

The scheduler is downstream HMP/HMP+, not EAS. The running configuration has
`CONFIG_SCHED_HMP=y`, `CONFIG_SCHED_HMP_PLUS=y`, HMP priority filtering at 5,
MediaTek CPU topology, `SCHED_MC`, CPU hotplug, cpusets, and fair cgroup
scheduling. `sched_features` contains `ARCH_CAPACITY` and `SCHED_HMP`; no EAS
feature was observed. The same-image config also selects MediaTek runqueue
averaging, load-balance enhancement, scheduler interoperability, CMP/TGS wakeup
extensions, and scheduler tracers, while
`CONFIG_HMP_FREQUENCY_INVARIANT_SCALE` is disabled. Default IRQ affinity is
`0x3ff`, covering all ten CPUs.

The root, LXC, and Android-container cpusets explicitly contain `0-9`. The
foreground, background, boost, system-background, and top-app child masks were
empty and inherited the then-online `0-1` effective mask. A retained historical
log from the same kernel build records Android init receiving `Permission
denied` when it tried to populate those `/dev/cpuset` files. Cpuset groups
therefore exist, but this evidence does not establish successful Android
foreground/background CPU partitioning.

## Analysis

Gemian boots only five CPUs and then uses its private HPS/PPM stack to move work
across clusters and collapse to CPU0 at idle. The HPS `<4>(4)(2)` records do
not prove all-ten completion because the active implementation updates its
algorithm-local counts without checking the hotplug return. A later bounded
capture directly observed CPU8 stably online and then offline again. CPU9 and
an all-ten simultaneous mask remain unconfirmed.

That result does not show that generic mainline PSCI alone is sufficient. The
vendor log initializes the big-cluster SRAM/iDVFS path before the all-cluster
HPS activity, and the pinned source couples HPS to MediaTek PPM and platform
CPU hotplug hooks. This is an ordering correlation and source contract, not
proof that any one private operation is the missing mainline prerequisite.
CPU8 and CPU9 still need separate recovery-backed mainline `CPU_ON` tests.

Gemian's scheduling policy should not be transplanted. HMP, HPS, PPM, private
DVFS, and EEM predate mainline EAS and combine mechanism with Android-era
policy. The useful transferable fact is the topology: CPUs 0--3, 4--7, and
8--9 are three performance clusters in one SoC package. The vendor topology
source combines A53/A72 efficiency constants with the DT's 1.391, 1.950, and
2.288 GHz hints, yielding normalized HMP capacities 304, 426, and 1024 by its
integer formula. Those are source-derived policy inputs, not measurements, and
must not be copied as mainline `capacity-dmips-mhz` data.

Exact Candidate AI has no `cpu-map` or `capacity-dmips-mhz` property, so Linux
7.1 sees one flat, equal-capacity topology under its forced `maxcpus=8`
baseline. Its exact configuration has `CONFIG_ENERGY_MODEL=y` while CPUfreq
and CPU idle are disabled; that option alone registers no useful energy model.
A generic three-cluster `cpu-map` is therefore a justified later scheduler
change, but it should remain separate from the CPU8/9 power-on experiments.
Capacity, OPP, cpufreq, energy-model, idle, and thermal policy require their
own measured contracts and must not be inferred from Gemian.

## Conclusion

`confirmed` for the three-cluster HMP/HPS/PPM policy and dynamic hotplug down
to one CPU. `confirmed` separately for one direct vendor CPU8 online/offline
cycle. `unconfirmed` for CPU9 and for all ten CPUs being simultaneously
online. Gemian uses HMP/HMP+ with MediaTek HPS, PPM, DVFS, and EEM policy, not
EAS; none of that policy should be copied into mainline.

## Follow-up

Use the calibrated vendor CPU8 trigger only with the planned owner-local
in-kernel transaction observer. Keep CPU9 excluded. After separate mainline
CPU8 and CPU9 paths are proven, add a three-cluster `cpu-map` as an
independently attributable scheduler patch. Defer static capacity and all
DVFS/energy/thermal policy until measured mainline providers exist.
